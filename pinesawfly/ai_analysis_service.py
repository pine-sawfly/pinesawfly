from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import logging
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings
from openai import OpenAI

logger = logging.getLogger(__name__)

AI_ANALYSIS_TIMEOUT_SECONDS = 30
AI_ANALYSIS_MAX_WORKERS = 8
AI_ANALYSIS_CACHE_TTL_SECONDS = 24 * 60 * 60
AI_PROVIDER_PRESETS = [
    "DeepSeek 官方",
    "OpenAI 官方",
    "自定义 API",
]
KNOWN_AI_MODEL_NAMES = {
    "deepseek",
    "deepseek api",
    "deepseek-chat",
    "deepseek-reasoner",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-latest",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "qwen-plus",
    "qwen-max",
}


class AiAnalysisService:
    def __init__(
        self,
        settings: QSettings,
        app_root: Path,
        project_path: Callable[[], str],
        render_prompt: Callable[[str, int, dict[str, object]], str],
    ) -> None:
        self.settings = settings
        self.app_root = app_root
        self.project_path = project_path
        self.render_prompt = render_prompt
        self.configs = self.load_api_configs()
        self.analysis_by_finding: dict[int, str] = {}
        self.last_error = ""

    def add_api_config(self) -> None:
        self.configs.append({
            "apiName": "DeepSeek 官方",
            "apiUrl": "https://api.deepseek.com",
            "modelName": "deepseek-v4-flash",
            "keyName": "DEEPSEEK_API_KEY",
            "apiKey": "",
        })
        self.save_api_configs()

    def delete_api_config(self, index: int) -> None:
        if 0 <= index < len(self.configs):
            self.configs.pop(index)
            self.save_api_configs()

    def update_api_config(self, index: int, api_name: str, api_url: str, model_name: str, key_name: str, api_key: str) -> None:
        if not 0 <= index < len(self.configs):
            return
        current_key = self.configs[index].get("apiKey", "")
        api_key = api_key.strip()
        self.configs[index] = {
            "apiName": api_name.strip(),
            "apiUrl": api_url.strip(),
            "modelName": model_name.strip(),
            "keyName": key_name.strip(),
            "apiKey": api_key if api_key else current_key,
        }
        self.save_api_configs()

    def public_configs(self) -> list[dict[str, object]]:
        return [self._public_api_config(index, config) for index, config in enumerate(self.configs)]

    def usable_configs(self) -> list[dict[str, str]]:
        return [
            config
            for config in self.configs
            if config.get("apiUrl", "").strip() and config.get("apiKey", "").strip()
        ]

    def load_api_configs(self) -> list[dict[str, str]]:
        raw = self.settings.value("plugins/aiAnalysis/apis", "[]", str)
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        configs = []
        for item in data:
            if isinstance(item, dict):
                api_name = str(item.get("apiName", "")).strip()
                api_url = str(item.get("apiUrl", "")).strip()
                model_name = str(item.get("modelName", "")).strip()
                if not model_name and self._looks_like_model_name(api_name):
                    model_name = self._legacy_model_name(api_name, api_url)
                    api_name = self._provider_name_from_url(api_url)
                configs.append({
                    "apiName": api_name,
                    "apiUrl": api_url,
                    "modelName": model_name,
                    "keyName": str(item.get("keyName", "")),
                    "apiKey": self._decrypt_secret(str(item.get("apiKey", ""))),
                })
        return configs

    def save_api_configs(self) -> None:
        encrypted = []
        for config in self.configs:
            encrypted.append({
                "apiName": config.get("apiName", ""),
                "apiUrl": config.get("apiUrl", ""),
                "modelName": config.get("modelName", ""),
                "keyName": config.get("keyName", ""),
                "apiKey": self._encrypt_secret(config.get("apiKey", "")),
            })
        self.settings.setValue("plugins/aiAnalysis/apis", json.dumps(encrypted, ensure_ascii=False))

    def prepare_analysis(self, findings: list[dict[str, object]]) -> None:
        self.analysis_by_finding = {}
        self.last_error = ""
        configs = self.usable_configs()
        if not configs or not findings:
            return

        prompt_template = self.load_prompt_template()
        pending_findings = [
            (index, finding)
            for index, finding in enumerate(findings, 1)
            if isinstance(finding, dict) and not str(finding.get("aiAnalysis", "")).strip()
        ]
        if not pending_findings:
            return
        workers = min(AI_ANALYSIS_MAX_WORKERS, max(1, len(pending_findings)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._request_analysis, configs[(index - 1) % len(configs)], prompt_template, index, finding): index
                for index, finding in pending_findings
            }
            for future in as_completed(futures):
                finding_index = futures[future]
                try:
                    content = future.result().strip()
                except Exception:
                    logger.debug("AI analysis failed for finding %s", finding_index, exc_info=True)
                    content = ""
                if content:
                    self.analysis_by_finding[finding_index] = content

    def restore_cache(self, findings: list[dict[str, object]]) -> bool:
        project_cache = self.current_project_cache()
        items = project_cache.get("items", {})
        if not isinstance(items, dict) or not items:
            return False
        changed = False
        for finding in findings:
            if not isinstance(finding, dict) or str(finding.get("aiAnalysis", "")).strip():
                continue
            cached = items.get(self.analysis_cache_key(finding), {})
            content = cached.get("content", "") if isinstance(cached, dict) else str(cached)
            if content:
                finding["aiAnalysis"] = content
                changed = True
        return changed

    def save_cache(self, findings: list[dict[str, object]]) -> None:
        cache = self.load_cache()
        project_key = self.project_cache_key()
        now = datetime.now().timestamp()
        project_cache = cache.get(project_key, {})
        if not isinstance(project_cache, dict):
            project_cache = {}
        items = project_cache.get("items", {})
        if not isinstance(items, dict):
            items = {}
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            content = str(finding.get("aiAnalysis", "")).strip()
            if content:
                key = self.analysis_cache_key(finding)
                previous = items.get(key, {})
                created_at = previous.get("createdAt", now) if isinstance(previous, dict) else now
                items[key] = {"content": content, "createdAt": created_at, "updatedAt": now}
        cache[project_key] = {
            "projectPath": os.path.abspath(self.project_path()),
            "createdAt": project_cache.get("createdAt", now),
            "updatedAt": now,
            "items": items,
        }
        self.settings.setValue("plugins/aiAnalysis/cache", json.dumps(cache, ensure_ascii=False))

    def load_cache(self) -> dict[str, object]:
        raw = self.settings.value("plugins/aiAnalysis/cache", "{}", str)
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): value for key, value in data.items()}

    def current_project_cache(self) -> dict[str, object]:
        cache = self.load_cache()
        project_cache = cache.get(self.project_cache_key(), {})
        return project_cache if isinstance(project_cache, dict) else {}

    def cleanup_cache(self) -> None:
        cache = self.load_cache()
        if not cache:
            return
        now = datetime.now().timestamp()
        changed = False
        cleaned: dict[str, object] = {}
        for project_key, project_cache in cache.items():
            if not isinstance(project_cache, dict):
                changed = True
                continue
            project_updated = float(project_cache.get("updatedAt") or project_cache.get("createdAt") or 0)
            if project_updated and now - project_updated > AI_ANALYSIS_CACHE_TTL_SECONDS:
                changed = True
                continue
            items = project_cache.get("items", {})
            if not isinstance(items, dict):
                changed = True
                continue
            cleaned_items = {}
            for item_key, item in items.items():
                if not isinstance(item, dict):
                    changed = True
                    continue
                item_updated = float(item.get("updatedAt") or item.get("createdAt") or 0)
                if item_updated and now - item_updated <= AI_ANALYSIS_CACHE_TTL_SECONDS:
                    cleaned_items[str(item_key)] = item
                else:
                    changed = True
            if cleaned_items:
                project_cache["items"] = cleaned_items
                project_cache["updatedAt"] = max(
                    float(item.get("updatedAt") or item.get("createdAt") or 0)
                    for item in cleaned_items.values()
                    if isinstance(item, dict)
                )
                cleaned[str(project_key)] = project_cache
            else:
                changed = True
        if changed:
            self.settings.setValue("plugins/aiAnalysis/cache", json.dumps(cleaned, ensure_ascii=False))

    def project_cache_key(self) -> str:
        return hashlib.sha256(os.path.abspath(self.project_path()).encode("utf-8", "replace")).hexdigest()

    def analysis_cache_key(self, finding: dict[str, object]) -> str:
        payload = "|".join(
            [
                str(finding.get("absolutePath") or finding.get("file") or ""),
                str(finding.get("line") or ""),
                str(finding.get("ruleId") or ""),
                str(finding.get("description") or ""),
                str(finding.get("dataFlow") or ""),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8", "replace")).hexdigest()

    def load_prompt_template(self) -> str:
        path = self.app_root / "templates" / "ai" / "analysis_prompt.md"
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                logger.debug("unable to read AI prompt template %s", path, exc_info=True)
        return self.default_prompt_template()

    def default_prompt_template(self) -> str:
        return (
            "你是资深应用安全专家。请根据以下漏洞信息，严格按格式输出，总字数不超过300字。\n"
            "判断规则：\n"
            "若存在漏洞，按格式输出：\n"
            "确认存在安全漏洞，修复建议：...\n"
            "修复代码：（仅展示修复核心代码）\n"
            "若不存在漏洞，按格式输出：\n"
            "该项漏洞为误报，理由：...（只说明理由，不要输出任何建议或代码）\n"
            "漏洞信息如下：\n"
            "漏洞位置：{{ vulnerability_location }}\n"
            "传递链路：{{ data_flow }}\n"
            "问题概述：{{ issue_summary }}\n"
            "代码证据片段：{{ evidence_code }}\n"
        )

    def _request_analysis(self, config: dict[str, str], prompt_template: str, index: int, finding: dict[str, object]) -> str:
        prompt = self.render_prompt(prompt_template, index, finding)
        api_url = config.get("apiUrl", "").strip()
        if self._uses_bearer_auth(config):
            return self._request_openai_compatible_analysis(config, prompt, api_url)
        return self._request_raw_chat_completions(config, prompt, api_url)

    def _request_openai_compatible_analysis(self, config: dict[str, str], prompt: str, api_url: str) -> str:
        api_key = config.get("apiKey", "").strip()
        base_url = self._ai_base_url(api_url)
        try:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=AI_ANALYSIS_TIMEOUT_SECONDS)
            kwargs: dict[str, object] = {
                "model": self._ai_model_name(config),
                "messages": [
                    {"role": "system", "content": "你是严谨的应用安全审计助手。"},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            }
            if "deepseek" in base_url.lower() and self._ai_model_name(config) == "deepseek-v4-pro":
                kwargs["reasoning_effort"] = "high"
                kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            self.last_error = self._format_exception(exc)
            logger.debug("OpenAI-compatible AI API request failed: %s", base_url, exc_info=True)
            return ""

    def _request_raw_chat_completions(self, config: dict[str, str], prompt: str, api_url: str) -> str:
        chat_url = self._ai_chat_completions_url(api_url)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self._ai_auth_headers(config))
        payload = {
            "model": self._ai_model_name(config),
            "messages": [
                {"role": "system", "content": "你是严谨的应用安全审计助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 600,
        }
        request = urllib.request.Request(
            chat_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=AI_ANALYSIS_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            self.last_error = f"HTTP {exc.code} {body}".strip()
            logger.debug("AI API request failed: %s", chat_url, exc_info=True)
            return ""
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            self.last_error = str(exc)
            logger.debug("AI API request failed: %s", chat_url, exc_info=True)
            return ""
        return self._extract_response_text(data)

    def _public_api_config(self, index: int, config: dict[str, str]) -> dict[str, object]:
        api_key = config.get("apiKey", "")
        return {
            "index": index,
            "apiName": config.get("apiName", ""),
            "apiUrl": config.get("apiUrl", ""),
            "modelName": config.get("modelName", ""),
            "keyName": config.get("keyName", ""),
            "apiKey": "",
            "maskedKey": self._mask_secret(api_key),
            "keyFingerprint": self._key_fingerprint(api_key),
        }

    def _looks_like_model_name(self, value: str) -> bool:
        normalized = value.strip().lower()
        return normalized in KNOWN_AI_MODEL_NAMES or normalized.startswith(("gpt-", "claude-", "gemini-", "qwen-", "deepseek-"))

    def _legacy_model_name(self, api_name: str, api_url: str) -> str:
        normalized = api_name.strip().lower()
        if normalized in {"deepseek", "deepseek api", "deepseek-chat"}:
            return "deepseek-v4-flash"
        if normalized == "deepseek-reasoner":
            return "deepseek-v4-pro"
        return api_name.strip() or self._default_model_for_url(api_url)

    def _provider_name_from_url(self, api_url: str) -> str:
        lowered = api_url.lower()
        if "deepseek" in lowered:
            return "DeepSeek 官方"
        if "openai" in lowered:
            return "OpenAI 官方"
        return "自定义 API"

    def _default_model_for_url(self, api_url: str) -> str:
        lowered = api_url.lower()
        if "deepseek" in lowered:
            return "deepseek-v4-flash"
        if "openai" in lowered:
            return "gpt-5-mini"
        return "gpt-5-mini"

    def _mask_secret(self, value: str) -> str:
        if not value:
            return ""
        if len(value) <= 11:
            return "*" * len(value)
        return f"{value[:7]}{'*' * max(4, len(value) - 11)}{value[-4:]}"

    def _key_fingerprint(self, value: str) -> str:
        if not value:
            return ""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]

    def _encrypt_secret(self, value: str) -> str:
        if not value:
            return ""
        if os.name != "nt":
            return value
        protected = self._dpapi_protect(value.encode("utf-8"))
        return "dpapi:" + base64.b64encode(protected).decode("ascii")

    def _decrypt_secret(self, value: str) -> str:
        if not value:
            return ""
        if not value.startswith("dpapi:"):
            return value
        if os.name != "nt":
            return ""
        try:
            data = base64.b64decode(value.removeprefix("dpapi:"))
            return self._dpapi_unprotect(data).decode("utf-8")
        except Exception:
            logger.debug("unable to decrypt AI API key", exc_info=True)
            return ""

    def _dpapi_protect(self, data: bytes) -> bytes:
        return self._dpapi_crypt(data, protect=True)

    def _dpapi_unprotect(self, data: bytes) -> bytes:
        return self._dpapi_crypt(data, protect=False)

    def _dpapi_crypt(self, data: bytes, protect: bool) -> bytes:
        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", ctypes.c_uint), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

        in_buffer = ctypes.create_string_buffer(data)
        in_blob = DATA_BLOB(len(data), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_ubyte)))
        out_blob = DATA_BLOB()
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        if protect:
            ok = crypt32.CryptProtectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob))
        else:
            ok = crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob))
        if not ok:
            raise OSError(ctypes.get_last_error())
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)

    def _ai_auth_headers(self, config: dict[str, str]) -> dict[str, str]:
        api_key = config.get("apiKey", "").strip()
        key_name = config.get("keyName", "").strip()
        if self._uses_bearer_auth(config):
            return {"Authorization": api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}"}
        return {key_name: api_key}

    def _uses_bearer_auth(self, config: dict[str, str]) -> bool:
        key_name = config.get("keyName", "").strip()
        api_url = config.get("apiUrl", "").lower()
        if any(provider in api_url for provider in ("deepseek", "openai")):
            return True
        normalized = key_name.lower().replace("-", "_")
        return (
            not key_name
            or normalized == "authorization"
            or normalized.endswith("_api_key")
            or normalized in {"api_key", "openai_api_key", "deepseek_api_key"}
        )

    def _ai_model_name(self, config: dict[str, str]) -> str:
        model_name = config.get("modelName", "").strip()
        api_url = config.get("apiUrl", "").lower()
        if not model_name:
            return self._default_model_for_url(api_url)
        if model_name.lower() == "deepseek-chat":
            return "deepseek-v4-flash"
        if model_name.lower() == "deepseek-reasoner":
            return "deepseek-v4-pro"
        return model_name

    def _ai_chat_completions_url(self, api_url: str) -> str:
        value = api_url.strip().rstrip("/")
        if not value:
            return value
        lowered = value.lower()
        if lowered.endswith("/chat/completions") or lowered.endswith("/v1/chat/completions"):
            return value
        if lowered.endswith("/v1"):
            return f"{value}/chat/completions"
        return f"{value}/chat/completions"

    def _ai_base_url(self, api_url: str) -> str:
        value = api_url.strip().rstrip("/")
        lowered = value.lower()
        if lowered.endswith("/chat/completions"):
            return value[: -len("/chat/completions")]
        return value

    def _format_exception(self, exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None)
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                body = response.text[:300]
            except Exception:
                body = ""
        else:
            body = str(exc)
        if status_code:
            return f"HTTP {status_code} {body}".strip()
        return body[:300]

    def _extract_response_text(self, data: object) -> str:
        if not isinstance(data, dict):
            return ""
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                text = first.get("text")
                if isinstance(text, str):
                    return text
        content = data.get("content")
        return content if isinstance(content, str) else ""
