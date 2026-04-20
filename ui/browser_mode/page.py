from __future__ import annotations

import json


class BrowserIndexPageMixin:
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
        }
        bootstrap_json = json.dumps(bootstrap, ensure_ascii=False).replace("</", "<\\/")
        html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>NeoDS Browser Mode</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
    <style>__APP_CSS__</style>
</head>
<body>
    <aside class="records-panel history-sidebar" id="records-panel" aria-hidden="true"></aside>
    <main class="page browser-page">
        <header class="header browser-header">
            <div class="header-main">
                <button class="history-toggle-button" type="button" id="history-toggle-button" aria-label="切换历史记录" aria-controls="records-panel" aria-expanded="false">
                    <svg class="history-toggle-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                        <path d="M7 4.5L12.5 10L7 15.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path>
                    </svg>
                </button>
                <h1 class="title" id="chat-title">新对话</h1>
            </div>
            <div class="header-actions browser-header-actions">
                <div class="header-theme-field">
                    <div class="header-theme-group">
                        <span class="header-theme-label">主题色</span>
                        <div class="theme-option-grid" id="theme-selector"></div>
                    </div>
                    <div class="header-theme-group" id="accent-group" hidden>
                        <span class="header-theme-label">高亮色</span>
                        <div class="accent-option-grid" id="accent-selector"></div>
                    </div>
                </div>
                <button class="toggle-all-button" type="button" id="toggle-meta-button">全部展开</button>
                <button class="toggle-all-button" type="button" id="new-chat-button">新会话</button>
                <button class="toggle-all-button" type="button" id="save-chat-button">保存记录</button>
                <button class="toggle-all-button header-icon-button" type="button" id="settings-button" title="设置" aria-label="打开设置" aria-expanded="false">
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path d="M9.6 3.5h4.8l.52 2.16c.4.15.77.35 1.12.58l2.11-.79 2.4 4.15-1.59 1.58c.04.21.04.43.04.65s0 .44-.04.65l1.59 1.58-2.4 4.15-2.11-.79c-.35.23-.72.43-1.12.58l-.52 2.16H9.6l-.52-2.16a5.8 5.8 0 0 1-1.12-.58l-2.11.79-2.4-4.15 1.59-1.58A4.9 4.9 0 0 1 5 12c0-.22 0-.44.04-.65l-1.59-1.58 2.4-4.15 2.11.79c.35-.23.72-.43 1.12-.58L9.6 3.5Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"></path>
                        <circle cx="12" cy="12" r="2.85" stroke="currentColor" stroke-width="1.4"></circle>
                    </svg>
                </button>
            </div>
        </header>

        <section class="conversation-shell">
            <section class="conversation" id="conversation">
                <div class="empty-state" id="empty-state" hidden></div>
            </section>
        </section>

        <nav class="turn-map" id="turn-map" aria-label="对话轮次导航" hidden>
            <div class="turn-map-list" id="turn-map-list"></div>
        </nav>
        <button class="scroll-bottom-button" type="button" id="scroll-bottom-button" title="滚动到底部" aria-label="滚动到底部" hidden>
            <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M4.5 7.5L10 13L15.5 7.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            </svg>
        </button>

        <section class="composer-card" id="composer-card">
            <div class="textarea-wrap">
                <button class="icon-button" type="button" id="expand-button" title="放大输入框">⤢</button>
                <textarea id="chat-input" placeholder="输入消息，Shift+Enter 换行"></textarea>
            </div>

            <div class="attachment-strip" id="attachment-strip" hidden></div>

            <div class="composer-toolbar">
                <div class="toolbar-left">
                    <button class="toolbar-plus" type="button" id="attach-button">+</button>
                    <div class="toolbar-dropdown" id="model-slot">
                        <button class="toolbar-menu-button toolbar-pill-button" type="button" id="model-button"></button>
                        <div class="extra-menu dropdown-menu" id="model-menu" hidden></div>
                    </div>
                    <div class="thinking-slot toolbar-dropdown" id="thinking-slot" hidden>
                        <button class="toolbar-menu-button toolbar-pill-button" type="button" id="thinking-button" title="思考选项" aria-label="思考选项"></button>
                        <div class="extra-menu dropdown-menu" id="thinking-menu" hidden></div>
                    </div>
                    <div class="extra-slot toolbar-dropdown" id="extra-slot">
                        <button class="toolbar-menu-button toolbar-pill-button" type="button" id="extra-button">额外配置</button>
                        <div class="extra-menu" id="extra-menu" hidden></div>
                    </div>
                </div>
                <div class="toolbar-right">
                    <div class="context-meter-shell">
                        <button class="context-meter" type="button" id="context-meter" aria-label="上下文窗口用量估算">
                            <span class="context-meter-ring" id="context-meter-ring" aria-hidden="true">
                                <span class="context-meter-ring-core"></span>
                            </span>
                        </button>
                        <div class="context-meter-popover" aria-hidden="true">
                            <span class="context-meter-value" id="context-meter-value">0.0k / 100.0k</span>
                            <span class="context-meter-detail" id="context-meter-window">上下文窗口：0.0k / 100.0k</span>
                            <span class="context-meter-detail" id="context-meter-total">总对话 Token：0</span>
                            <button class="context-meter-detail-button" type="button" id="context-usage-detail-button">详细用量统计</button>
                            <span class="context-meter-status" id="context-meter-status" hidden>已超过上限</span>
                        </div>
                    </div>
                    <button class="send-button" type="button" id="send-button">发送</button>
                </div>
            </div>
        </section>

        <input id="file-input" type="file" multiple hidden>
    </main>

    <div class="confirm-dialog-overlay" id="confirm-dialog-overlay" aria-hidden="true" hidden>
        <div class="confirm-dialog-backdrop"></div>
        <div class="confirm-dialog" id="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title">
            <div class="confirm-dialog-header">
                <div class="confirm-dialog-kicker">Delete</div>
                <h2 class="confirm-dialog-title" id="confirm-dialog-title">确认删除</h2>
            </div>
            <p class="confirm-dialog-body" id="confirm-dialog-body">删除后将无法恢复。</p>
            <div class="confirm-dialog-actions">
                <button class="confirm-dialog-button" type="button" id="confirm-dialog-cancel">取消</button>
                <button class="confirm-dialog-button is-danger" type="button" id="confirm-dialog-confirm">删除</button>
            </div>
        </div>
    </div>

    <div class="settings-overlay" id="settings-overlay" aria-hidden="true" inert>
        <div class="settings-backdrop"></div>
        <aside class="settings-sidebar" id="settings-sidebar" role="dialog" aria-modal="true" aria-labelledby="settings-title">
            <div class="settings-sidebar-header">
                <div class="settings-sidebar-intro">
                    <p class="settings-kicker">Preferences</p>
                    <h2 class="settings-sidebar-title" id="settings-title">设置</h2>
                </div>
                <button class="settings-close-button" type="button" id="settings-close-button" aria-label="关闭设置">&times;</button>
            </div>
            <div class="settings-sidebar-body">
                <section class="settings-section">
                    <h3 class="settings-section-title">外观</h3>
                    <div class="settings-theme-host" id="settings-theme-slot"></div>
                </section>
                <section class="settings-section">
                    <h3 class="settings-section-title">输出设置</h3>
                    <label class="settings-toggle">
                        <span class="settings-toggle-copy">
                            <span class="settings-toggle-label">输出内容时默认折叠思考内容</span>
                        </span>
                        <span class="settings-switch">
                            <input class="settings-switch-input" type="checkbox" id="pref-collapse-thinking" data-preference-key="collapse_thinking_by_default">
                            <span class="settings-switch-ui" aria-hidden="true"></span>
                        </span>
                    </label>
                    <label class="settings-toggle">
                        <span class="settings-toggle-copy">
                            <span class="settings-toggle-label">输出内容时默认折叠过程元数据</span>
                        </span>
                        <span class="settings-switch">
                            <input class="settings-switch-input" type="checkbox" id="pref-collapse-process" data-preference-key="collapse_process_meta_by_default">
                            <span class="settings-switch-ui" aria-hidden="true"></span>
                        </span>
                    </label>
                    <label class="settings-toggle">
                        <span class="settings-toggle-copy">
                            <span class="settings-toggle-label">输出结束后自动折叠思考内容和元数据</span>
                        </span>
                        <span class="settings-switch">
                            <input class="settings-switch-input" type="checkbox" id="pref-auto-collapse-output" data-preference-key="auto_collapse_output_meta">
                            <span class="settings-switch-ui" aria-hidden="true"></span>
                        </span>
                    </label>
                </section>
                <section class="settings-section">
                    <h3 class="settings-section-title">存储设置</h3>
                    <label class="settings-toggle">
                        <span class="settings-toggle-copy">
                            <span class="settings-toggle-label">本地化保存</span>
                            <span class="settings-toggle-note">关闭后只保存 JSON 文件，不额外生成 HTML 文件。</span>
                        </span>
                        <span class="settings-switch">
                            <input class="settings-switch-input" type="checkbox" id="pref-localized-save" data-preference-key="localized_save">
                            <span class="settings-switch-ui" aria-hidden="true"></span>
                        </span>
                    </label>
                </section>
            </div>
        </aside>
    </div>

    <div class="usage-detail-overlay" id="usage-detail-overlay" aria-hidden="true" hidden>
        <div class="usage-detail-backdrop"></div>
        <div class="usage-detail-dialog" id="usage-detail-dialog" role="dialog" aria-modal="true" aria-labelledby="usage-detail-title">
            <div class="usage-detail-header">
                <div class="usage-detail-kicker">Token Usage</div>
                <h2 class="usage-detail-title" id="usage-detail-title">详细用量统计</h2>
                <button class="usage-detail-close" type="button" id="usage-detail-close" aria-label="关闭统计弹窗">&times;</button>
            </div>
            <div class="usage-detail-summary" id="usage-detail-summary"></div>
            <div class="usage-detail-body" id="usage-detail-body"></div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
    <script>
        window.__NEODS_BROWSER_BOOTSTRAP__ = __BOOTSTRAP_JSON__;
    </script>
    <script>__APP_JS__</script>
</body>
</html>
"""
        return (
            html_template
            .replace("__BOOTSTRAP_JSON__", bootstrap_json)
            .replace("__APP_CSS__", self._build_css())
            .replace("__APP_JS__", self._build_js())
        )

