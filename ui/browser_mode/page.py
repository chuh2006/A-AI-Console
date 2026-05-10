from __future__ import annotations

import json
from pathlib import Path


class BrowserIndexPageMixin:
    def _browser_static_path(self, *parts: str) -> Path:
        return Path(__file__).resolve().parent.joinpath("static", *parts)

    def _build_index_html(self) -> str:
        bootstrap = {
            "defaultModel": self.default_model,
            "models": self.model_catalog,
            "theme": {
                "value": self.browser_theme,
                "options": self.THEME_OPTIONS,
                "accentValue": self.browser_accent,
                "accentOptions": self.ACCENT_OPTIONS,
            },
            "browserPreferences": self.browser_preferences,
            "enableSystemPrompt": self.enable_system_prompt,
        }
        bootstrap_json = json.dumps(bootstrap, ensure_ascii=False).replace("</", "<\\/")
        html_template = self._browser_static_path("index.html").read_text(encoding="utf-8")
        return html_template.replace("__BOOTSTRAP_JSON__", bootstrap_json)
