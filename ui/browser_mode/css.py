from __future__ import annotations


class BrowserCSSMixin:
    def _build_css(self) -> str:
        return self._browser_static_path("browser.css").read_text(encoding="utf-8")
