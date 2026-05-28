from __future__ import annotations

import json
import re
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot


class RuleManager(QObject):
    rulesChanged = Signal()
    statusChanged = Signal()

    def __init__(self, rules_dir: str | Path) -> None:
        super().__init__()
        self._rules_dir = Path(rules_dir)
        self._rules: list[dict[str, object]] = []
        self._status = "规则已加载"
        self.reload()

    @Slot()
    def reload(self) -> None:
        self._rules = []
        self._rules_dir.mkdir(parents=True, exist_ok=True)
        for file_path in sorted(self._rules_dir.glob("*_rules.json")):
            language = file_path.name.replace("_rules.json", "")
            for rule in self._read_rule_file(file_path):
                self._rules.append(self._normalize_rule(language, rule))
        self.rulesChanged.emit()

    @Slot(str, str, str, str, str, str, result=bool)
    def addRule(self, language: str, rule_id: str, name: str, pattern: str, severity: str, description: str) -> bool:
        language = self._normalize_language(language)
        if not language or not rule_id.strip() or not name.strip() or not pattern.strip():
            self._set_status("语言、规则ID、名称和正则不能为空")
            return False

        try:
            re.compile(pattern)
        except re.error as exc:
            self._set_status(f"正则无效: {exc}")
            return False

        file_path = self._file_for_language(language)
        rules = self._read_rule_file(file_path)
        if any(rule.get("id") == rule_id for rule in rules):
            self._set_status(f"规则ID已存在: {rule_id}")
            return False

        rules.append(
            {
                "id": rule_id.strip(),
                "name": name.strip(),
                "type": "REGEX",
                "pattern": pattern,
                "severity": severity.strip() or "Medium",
                "description": description.strip(),
                "enabled": True,
            }
        )
        self._write_rule_file(file_path, rules)
        self._set_status(f"已新增规则 {rule_id}")
        self.reload()
        return True

    @Slot(str, result=bool)
    def deleteRule(self, key: str) -> bool:
        language, rule_id = self._split_key(key)
        if not language or not rule_id:
            return False
        file_path = self._file_for_language(language)
        rules = self._read_rule_file(file_path)
        next_rules = [rule for rule in rules if rule.get("id") != rule_id]
        if len(next_rules) == len(rules):
            self._set_status(f"未找到规则 {rule_id}")
            return False
        self._write_rule_file(file_path, next_rules)
        self._set_status(f"已删除规则 {rule_id}")
        self.reload()
        return True

    @Slot(str, str, str, str, str, str, str, result=bool)
    def updateRule(
        self,
        key: str,
        language: str,
        rule_id: str,
        name: str,
        pattern: str,
        severity: str,
        description: str,
    ) -> bool:
        old_language, old_rule_id = self._split_key(key)
        language = self._normalize_language(language)
        rule_id = rule_id.strip()
        if not old_language or not old_rule_id:
            self._set_status("未选择要编辑的规则")
            return False
        if not language or not rule_id or not name.strip() or not pattern.strip():
            self._set_status("语言、规则ID、名称和正则不能为空")
            return False
        try:
            re.compile(pattern)
        except re.error as exc:
            self._set_status(f"正则无效: {exc}")
            return False

        old_file = self._file_for_language(old_language)
        old_rules = self._read_rule_file(old_file)
        target_rule = None
        next_old_rules = []
        for rule in old_rules:
            if rule.get("id") == old_rule_id and target_rule is None:
                target_rule = dict(rule)
            else:
                next_old_rules.append(rule)
        if target_rule is None:
            self._set_status(f"未找到规则 {old_rule_id}")
            return False

        new_file = self._file_for_language(language)
        new_rules = next_old_rules if new_file == old_file else self._read_rule_file(new_file)
        if any(rule.get("id") == rule_id for rule in new_rules):
            self._set_status(f"规则ID已存在: {rule_id}")
            return False

        target_rule.update(
            {
                "id": rule_id,
                "name": name.strip(),
                "type": "REGEX",
                "pattern": pattern,
                "severity": severity.strip() or "Medium",
                "description": description.strip(),
                "enabled": bool(target_rule.get("enabled", True)),
                "flags": target_rule.get("flags", []),
            }
        )
        new_rules.append(target_rule)
        if new_file != old_file:
            self._write_rule_file(old_file, next_old_rules)
            self._write_rule_file(new_file, new_rules)
        else:
            self._write_rule_file(new_file, new_rules)
        self._set_status(f"已更新规则 {rule_id}")
        self.reload()
        return True

    @Slot(str, bool, result=bool)
    def setRuleEnabled(self, key: str, enabled: bool) -> bool:
        language, rule_id = self._split_key(key)
        if not language or not rule_id:
            return False
        file_path = self._file_for_language(language)
        rules = self._read_rule_file(file_path)
        changed = False
        for rule in rules:
            if rule.get("id") == rule_id:
                rule["enabled"] = enabled
                changed = True
                break
        if not changed:
            self._set_status(f"未找到规则 {rule_id}")
            return False
        self._write_rule_file(file_path, rules)
        self._set_status(f"已{'启用' if enabled else '禁用'}规则 {rule_id}")
        self.reload()
        return True

    def _read_rule_file(self, file_path: Path) -> list[dict[str, object]]:
        if not file_path.exists():
            return []
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, list):
                    return data
                return list(data.get("rules", []))
        except (OSError, json.JSONDecodeError) as exc:
            self._set_status(f"规则文件读取失败: {file_path.name}: {exc}")
            return []

    def _write_rule_file(self, file_path: Path, rules: list[dict[str, object]]) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        language = file_path.name.replace("_rules.json", "")
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "version": 1,
                    "language": language,
                    "rules": rules,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")

    def _normalize_rule(self, language: str, rule: dict[str, object]) -> dict[str, object]:
        rule_id = str(rule.get("id", ""))
        return {
            "key": f"{language}:{rule_id}",
            "language": language,
            "id": rule_id,
            "name": str(rule.get("name", "")),
            "type": str(rule.get("type", "REGEX")),
            "pattern": str(rule.get("pattern", "")),
            "severity": str(rule.get("severity", "Medium")),
            "description": str(rule.get("description", "")),
            "enabled": bool(rule.get("enabled", True)),
        }

    def _normalize_language(self, language: str) -> str:
        language = language.strip().lower()
        aliases = {"py": "python", "python": "python", "php": "php", "java": "java"}
        return aliases.get(language, language)

    def _file_for_language(self, language: str) -> Path:
        return self._rules_dir / f"{language}_rules.json"

    def _split_key(self, key: str) -> tuple[str, str]:
        if ":" not in key:
            return "", ""
        language, rule_id = key.split(":", 1)
        return self._normalize_language(language), rule_id

    def _set_status(self, status: str) -> None:
        self._status = status
        self.statusChanged.emit()

    def get_rules(self) -> list[dict[str, object]]:
        return self._rules

    def get_status(self) -> str:
        return self._status

    rules = Property("QVariantList", get_rules, notify=rulesChanged)
    status = Property(str, get_status, notify=statusChanged)
