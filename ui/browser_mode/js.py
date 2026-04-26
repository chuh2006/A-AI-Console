from __future__ import annotations


class BrowserJSMixin:
    def _build_js(self) -> str:
        return self._browser_static_path("browser.js").read_text(encoding="utf-8")
