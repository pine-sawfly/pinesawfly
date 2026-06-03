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
        for rule in self.rules[language]:
            try:
                results.extend(self._match_rule(content, rule, file_path))
            except Exception as exc:
                logger.error("应用规则 %s 时出错: %s", rule["id"], exc)

        logger.info("通用规则引擎在文件 %s 中发现 %s 个问题", file_path, len(results))
        return results

    def _match_rule(self, content: str, rule: dict[str, Any], file_path: str) -> list[dict[str, Any]]:
        if rule.get("type", "REGEX") != "REGEX":
            return []

        try:
            regex = re.compile(rule.get("pattern", ""), self._regex_flags(rule.get("flags", [])))
        except re.error as exc:
            logger.error("规则 %s 的正则表达式错误: %s", rule["id"], exc)
            return []

        results = []
        for match in regex.finditer(content):
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
