from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from core.exception_handler import safe_operation
from modules.file_module import FileModule

logger = logging.getLogger(__name__)


class GenericRuleEngine:
    def __init__(self, rules_dir: str | None = None):
        self.rules_dir = Path(rules_dir) if rules_dir else Path(__file__).resolve().parent.parent / "rules"
        self.rules: dict[str, list[dict[str, Any]]] = {}
        self._load_all_rules()

    def _load_all_rules(self) -> None:
        if not self.rules_dir.exists():
            logger.warning("规则目录 %s 不存在", self.rules_dir)
            return

        for file_path in self.rules_dir.glob("*_rules.json"):
            language = file_path.name.replace("_rules.json", "")
            self.rules[language] = self._load_rules_from_file(file_path)

    def _load_rules_from_file(self, rules_file: Path) -> list[dict[str, Any]]:
        try:
            data = json.loads(rules_file.read_text(encoding="utf-8"))
            rules = [self._normalize_rule(rule) for rule in data.get("rules", []) if rule.get("enabled", True)]
            logger.info("从 %s 加载了 %s 条规则", rules_file, len(rules))
            return rules
        except OSError as exc:
            logger.error("读取规则文件 %s 失败: %s", rules_file, exc)
        except json.JSONDecodeError as exc:
            logger.error("解析规则文件 %s 失败: %s", rules_file, exc)
        return []

    def _normalize_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": rule.get("id", "UNKNOWN"),
            "name": rule.get("name", rule.get("id", "未知规则")),
            "type": rule.get("type", "REGEX"),
            "pattern": rule.get("pattern", ""),
            "severity": rule.get("severity", "Medium"),
            "description": rule.get("description", ""),
            "flags": rule.get("flags", []),
            "skipContexts": rule.get("skipContexts", []),
            "scanFullFile": bool(rule.get("scanFullFile", False)),
        }

    def get_rules_by_language(self, language: str) -> list[dict[str, Any]]:
        return self.rules.get(language, [])

    def get_all_rules(self) -> dict[str, list[dict[str, Any]]]:
        return self.rules

    @safe_operation
    def scan_file(self, file_path: str) -> list[dict[str, Any]]:
        language = {
            ".php": "php",
            ".py": "python",
            ".java": "java",
        }.get(Path(file_path).suffix.lower())

        if not language or language not in self.rules:
            logger.info("不支持的语言或无对应规则: %s", Path(file_path).suffix.lower())
            return []

        content = FileModule.read_file_with_encoding(file_path)
        results: list[dict[str, Any]] = []
        ignored_spans = self._ignored_spans(content, language)
        for rule in self.rules[language]:
            try:
                results.extend(self._match_rule(content, rule, file_path, ignored_spans))
            except Exception as exc:
                logger.error("应用规则 %s 时出错: %s", rule["id"], exc)

        logger.info("通用规则引擎在文件 %s 中发现 %s 个问题", file_path, len(results))
        return results

    def _match_rule(
        self,
        content: str,
        rule: dict[str, Any],
        file_path: str,
        ignored_spans: list[tuple[int, int, str]],
    ) -> list[dict[str, Any]]:
        if rule.get("type", "REGEX") != "REGEX":
            return []

        try:
            regex = re.compile(rule.get("pattern", ""), self._regex_flags(rule.get("flags", [])))
        except re.error as exc:
            logger.error("规则 %s 的正则表达式错误: %s", rule["id"], exc)
            return []

        results = []
        for match in regex.finditer(content):
            if self._should_skip_match(match.start(), rule, ignored_spans):
                continue
            results.append({
                "rule_id": rule["id"],
                "rule_name": rule["name"],
                "severity": rule["severity"],
                "file": file_path,
                "line": content[:match.start()].count("\n") + 1,
                "description": rule["description"],
                "match": match.group(0),
            })
        return results

    def _ignored_spans(self, content: str, language: str) -> list[tuple[int, int, str]]:
        if language != "php":
            return []
        return self._php_ignored_spans(content)

    def _should_skip_match(self, start: int, rule: dict[str, Any], ignored_spans: list[tuple[int, int, str]]) -> bool:
        if rule.get("scanFullFile"):
            return False
        if any(span_start <= start < span_end and context == "outside_php" for span_start, span_end, context in ignored_spans):
            return True
        if not rule.get("skipContexts"):
            return False
        contexts = set(rule.get("skipContexts") or [])
        return any(span_start <= start < span_end and context in contexts for span_start, span_end, context in ignored_spans)

    def _php_ignored_spans(self, content: str) -> list[tuple[int, int, str]]:
        code_spans = self._php_code_spans(content)
        if not code_spans:
            return [(0, len(content), "outside_php")]

        ignored: list[tuple[int, int, str]] = []
        cursor = 0
        for start, end in code_spans:
            if cursor < start:
                ignored.append((cursor, start, "outside_php"))
            ignored.extend(self._php_string_comment_spans(content, start, end))
            cursor = end
        if cursor < len(content):
            ignored.append((cursor, len(content), "outside_php"))
        return ignored

    def _php_code_spans(self, content: str) -> list[tuple[int, int]]:
        tag_pattern = re.compile(r"<\?(?:php|=)?", re.IGNORECASE)
        spans: list[tuple[int, int]] = []
        for match in tag_pattern.finditer(content):
            start = match.end()
            close = content.find("?>", start)
            end = len(content) if close == -1 else close
            spans.append((start, end))
        return spans

    def _php_string_comment_spans(self, content: str, start: int, end: int) -> list[tuple[int, int, str]]:
        spans: list[tuple[int, int, str]] = []
        i = start
        while i < end:
            char = content[i]
            next_char = content[i + 1] if i + 1 < end else ""
            if char in {"'", '"', "`"}:
                span_start = i
                quote = char
                i += 1
                while i < end:
                    if content[i] == "\\":
                        i += 2
                        continue
                    if content[i] == quote:
                        i += 1
                        break
                    i += 1
                spans.append((span_start, min(i, end), "string"))
                continue
            if char == "/" and next_char == "/":
                span_start = i
                i = content.find("\n", i + 2)
                if i == -1 or i > end:
                    i = end
                spans.append((span_start, i, "comment"))
                continue
            if char == "#":
                span_start = i
                i = content.find("\n", i + 1)
                if i == -1 or i > end:
                    i = end
                spans.append((span_start, i, "comment"))
                continue
            if char == "/" and next_char == "*":
                span_start = i
                block_end = content.find("*/", i + 2)
                i = end if block_end == -1 or block_end > end else block_end + 2
                spans.append((span_start, i, "comment"))
                continue
            i += 1
        return spans

    def _regex_flags(self, flags: Any) -> int:
        if isinstance(flags, str):
            flags = [flags]
        value = 0
        mapping = {
            "IGNORECASE": re.IGNORECASE,
            "I": re.IGNORECASE,
            "MULTILINE": re.MULTILINE,
            "M": re.MULTILINE,
            "DOTALL": re.DOTALL,
            "S": re.DOTALL,
        }
        for flag in flags or []:
            value |= mapping.get(str(flag).upper(), 0)
        return value
