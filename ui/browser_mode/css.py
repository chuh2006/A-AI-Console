from __future__ import annotations


class BrowserCSSMixin:
    def _build_css(self) -> str:
        return """
:root {
    --page-gutter: 24px;
    --content-max-width: 980px;
    --composer-gap: 16px;
    --composer-reserve: 188px;
    --assistant-meta-open-width: 760px;
    --history-sidebar-width: 304px;
    --history-sidebar-visible-width: min(var(--history-sidebar-width), calc(100vw - 32px));
    --history-sidebar-shift-open: calc(var(--history-sidebar-visible-width) / 2);
    --history-header-shift-open: var(--history-sidebar-visible-width);
    --history-sidebar-shift: 0px;
    --history-header-shift: 0px;
    --bg: #ffffff;
    --text: #222222;
    --muted: #7d7166;
    --muted-strong: #665648;
    --muted-soft: #a89b8e;
    --line: #e8ddd1;
    --line-strong: #d7c6b6;
    --line-soft: rgba(230, 224, 214, 0.72);
    --theme-accent: #d97757;
    --theme-accent-border: rgba(217, 119, 87, 0.22);
    --theme-accent-shadow: rgba(217, 119, 87, 0.24);
    --theme-accent-glow: rgba(217, 119, 87, 0.14);
    --accent: #d97757;
    --accent-start: #d97757;
    --accent-end: #d97757;
    --accent-surface: #faece6;
    --accent-border: rgba(217, 119, 87, 0.2);
    --accent-shadow: rgba(217, 119, 87, 0.12);
    --accent-tint: rgba(217, 119, 87, 0.18);
    --accent-glow: rgba(217, 119, 87, 0.12);
    --surface-hover: rgba(241, 231, 221, 0.84);
    --surface-card: rgba(255, 255, 255, 0.9);
    --surface-card-strong: rgba(255, 255, 255, 0.96);
    --surface-panel: rgba(255, 255, 255, 0.98);
    --surface-elevated: rgba(255, 255, 255, 0.92);
    --user: #f6e6de;
    --user-border: rgba(217, 119, 87, 0.18);
    --code-bg: #1f1f1f;
    --code-text: #f3f3f3;
    --shadow: 0 10px 30px rgba(51, 41, 28, 0.08);
    --paper: #fdf5ef;
    --inline-code-bg: #f4e3d6;
    --inline-code-text: #6b523c;
    --quote-border: #d8bea8;
    --quote-text: #6d5d4d;
    --quote-bg: rgba(255, 249, 244, 0.86);
    --meta-summary: #8a7463;
    --meta-text: #725f51;
    --overlay: rgba(10, 14, 22, 0.52);
    --sidebar-bg: rgba(255, 248, 241, 0.98);
    --sidebar-section-bg: rgba(255, 255, 255, 0.76);
}
:root[data-theme="green"] {
    --muted: #61776c;
    --muted-strong: #476154;
    --muted-soft: #91a79b;
    --line: #d6e5dd;
    --line-strong: #b9d2c6;
    --line-soft: rgba(214, 229, 221, 0.82);
    --theme-accent: #2d8a63;
    --theme-accent-border: rgba(45, 138, 99, 0.22);
    --theme-accent-shadow: rgba(45, 138, 99, 0.24);
    --theme-accent-glow: rgba(45, 138, 99, 0.14);
    --accent: #2d8a63;
    --accent-start: #2d8a63;
    --accent-end: #2d8a63;
    --accent-surface: #e7f4ed;
    --accent-border: rgba(45, 138, 99, 0.22);
    --accent-shadow: rgba(45, 138, 99, 0.12);
    --accent-tint: rgba(45, 138, 99, 0.18);
    --accent-glow: rgba(45, 138, 99, 0.12);
    --surface-hover: rgba(223, 239, 231, 0.92);
    --user: #e1f0e7;
    --user-border: rgba(45, 138, 99, 0.22);
    --paper: #f1f8f3;
    --inline-code-bg: #dff0e7;
    --inline-code-text: #2e5d47;
    --quote-border: #90c0a8;
    --quote-text: #4b6557;
    --quote-bg: rgba(242, 250, 245, 0.9);
    --meta-summary: #5d7568;
    --meta-text: #4f665b;
    --sidebar-bg: rgba(239, 248, 242, 0.98);
    --sidebar-section-bg: rgba(255, 255, 255, 0.72);
}
:root[data-theme="blue"] {
    --muted: #66758a;
    --muted-strong: #4b5d73;
    --muted-soft: #97a6bc;
    --line: #d8e2f1;
    --line-strong: #bdcde4;
    --line-soft: rgba(216, 226, 241, 0.84);
    --theme-accent: #2f6fca;
    --theme-accent-border: rgba(47, 111, 202, 0.22);
    --theme-accent-shadow: rgba(47, 111, 202, 0.24);
    --theme-accent-glow: rgba(47, 111, 202, 0.14);
    --accent: #2f6fca;
    --accent-start: #2f6fca;
    --accent-end: #2f6fca;
    --accent-surface: #e3efff;
    --accent-border: rgba(47, 111, 202, 0.22);
    --accent-shadow: rgba(47, 111, 202, 0.12);
    --accent-tint: rgba(47, 111, 202, 0.18);
    --accent-glow: rgba(47, 111, 202, 0.12);
    --surface-hover: rgba(226, 235, 248, 0.92);
    --user: #e5eefb;
    --user-border: rgba(47, 111, 202, 0.2);
    --paper: #f2f7ff;
    --inline-code-bg: #e1ebfa;
    --inline-code-text: #35557d;
    --quote-border: #9bb7e1;
    --quote-text: #52657d;
    --quote-bg: rgba(243, 248, 255, 0.92);
    --meta-summary: #62748d;
    --meta-text: #53657b;
    --sidebar-bg: rgba(240, 246, 255, 0.98);
    --sidebar-section-bg: rgba(255, 255, 255, 0.74);
}
:root[data-theme="black"] {
    --muted: #6f6f72;
    --muted-strong: #4d4d50;
    --muted-soft: #9a9a9d;
    --line: #dfdfdf;
    --line-strong: #c7c7c9;
    --line-soft: rgba(223, 223, 223, 0.86);
    --theme-accent: #3b3b3d;
    --theme-accent-border: rgba(59, 59, 61, 0.26);
    --theme-accent-shadow: rgba(59, 59, 61, 0.22);
    --theme-accent-glow: rgba(59, 59, 61, 0.14);
    --surface-hover: rgba(234, 234, 235, 0.92);
    --user: #ededee;
    --user-border: rgba(44, 44, 44, 0.14);
    --paper: #f5f5f6;
    --inline-code-bg: #ececed;
    --inline-code-text: #464649;
    --quote-border: #c3c3c6;
    --quote-text: #5f5f63;
    --quote-bg: rgba(248, 248, 248, 0.95);
    --meta-summary: #717176;
    --meta-text: #5f5f64;
    --sidebar-bg: rgba(244, 244, 246, 0.98);
    --sidebar-section-bg: rgba(255, 255, 255, 0.7);
}
:root[data-theme="black"]:not([data-accent]),
:root[data-theme="black"][data-accent="blue"] {
    --accent: #2f6fca;
    --accent-start: #2f6fca;
    --accent-end: #2f6fca;
    --accent-surface: #e3efff;
    --accent-border: rgba(47, 111, 202, 0.22);
    --accent-shadow: rgba(47, 111, 202, 0.12);
    --accent-tint: rgba(47, 111, 202, 0.18);
    --accent-glow: rgba(47, 111, 202, 0.12);
}
:root[data-theme="black"][data-accent="green"] {
    --accent: #2d8a63;
    --accent-start: #2d8a63;
    --accent-end: #2d8a63;
    --accent-surface: #e7f4ed;
    --accent-border: rgba(45, 138, 99, 0.22);
    --accent-shadow: rgba(45, 138, 99, 0.12);
    --accent-tint: rgba(45, 138, 99, 0.18);
    --accent-glow: rgba(45, 138, 99, 0.12);
}
:root[data-theme="black"][data-accent="orange"] {
    --accent: #d97757;
    --accent-start: #d97757;
    --accent-end: #d97757;
    --accent-surface: #faece6;
    --accent-border: rgba(217, 119, 87, 0.2);
    --accent-shadow: rgba(217, 119, 87, 0.12);
    --accent-tint: rgba(217, 119, 87, 0.18);
    --accent-glow: rgba(217, 119, 87, 0.08);
}
:root[data-theme="black"][data-accent="graphite"] {
    --accent: #3f3f41;
    --accent-start: #3f3f41;
    --accent-end: #3f3f41;
    --accent-surface: #ececee;
    --accent-border: rgba(63, 63, 65, 0.24);
    --accent-shadow: rgba(63, 63, 65, 0.12);
    --accent-tint: rgba(63, 63, 65, 0.16);
    --accent-glow: rgba(63, 63, 65, 0.12);
}
* {
    box-sizing: border-box;
}
html {
    min-height: 100%;
    scrollbar-gutter: stable both-edges;
    scroll-padding-bottom: calc(var(--composer-reserve) + var(--composer-gap) + 24px);
}
html, body {
    min-height: 100%;
}
body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
    line-height: 1.72;
    overflow-x: hidden;
}
body.settings-open {
    overflow: hidden;
}
body.records-open {
    --history-sidebar-shift: var(--history-sidebar-shift-open);
    --history-header-shift: var(--history-header-shift-open);
}
.page {
    width: 100%;
    max-width: none;
    margin: 0;
    padding: 0 var(--page-gutter) calc(var(--composer-reserve) + 40px);
}
.browser-page {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    gap: 0;
    position: relative;
}
.header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}
.browser-header {
    position: sticky;
    top: 0;
    z-index: 60;
    padding: 8px 0 4px;
    border: none;
    border-radius: 0;
    background: var(--bg);
    box-shadow: none;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
}
.header-main {
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    padding-right: 16px;
    transform: translateX(var(--history-header-shift));
    transition: transform 0.24s ease;
}
.history-toggle-button {
    width: 34px;
    height: 34px;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-card);
    color: var(--muted);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex: 0 0 auto;
    transition: border-color 0.18s ease, color 0.18s ease, background 0.18s ease, transform 0.22s ease;
}
.history-toggle-button:hover,
.history-toggle-button:focus-visible {
    color: var(--text);
    border-color: var(--line-strong);
    background: var(--surface-card-strong);
    outline: none;
}
.history-toggle-icon {
    width: 18px;
    height: 18px;
    transition: transform 0.24s ease;
}
body.records-open .history-toggle-icon {
    transform: rotate(180deg);
}
.title {
    margin: 0;
    font-size: 20px;
    line-height: 1.2;
    font-weight: 700;
    letter-spacing: 0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.browser-header-actions {
    display: flex;
    gap: 8px;
    flex-wrap: nowrap;
    justify-content: flex-end;
    position: relative;
    align-items: center;
    margin-left: auto;
    flex: 0 0 auto;
}
.header-theme-field {
    display: none;
}
.settings-section .header-theme-field {
    display: grid;
    gap: 14px;
    width: 100%;
}
.header-theme-group {
    display: grid;
    gap: 8px;
}
.header-theme-label {
    font-size: 13px;
    color: var(--muted);
    white-space: nowrap;
}
.theme-option-grid,
.accent-option-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}
.theme-option,
.accent-option {
    min-height: 44px;
    padding: 0 14px;
    border: 1px solid var(--line);
    border-radius: 16px;
    background-color: var(--surface-card-strong);
    color: var(--muted-strong);
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font: inherit;
    cursor: pointer;
    transition: border-color 0.18s ease, background-color 0.22s ease, color 0.18s ease, box-shadow 0.22s ease, transform 0.18s ease;
}
.theme-option:hover,
.theme-option:focus-visible,
.accent-option:hover,
.accent-option:focus-visible {
    border-color: var(--line-strong);
    background-color: var(--surface-hover);
    color: var(--text);
    outline: none;
    transform: translateY(-1px);
}
.theme-option.is-selected,
.accent-option.is-selected,
.dropdown-option.is-selected,
.extra-toggle.is-checked,
.extra-choice-button.is-selected {
    border-color: var(--accent-border);
    background-color: var(--accent-surface);
    color: var(--accent);
    box-shadow: 0 12px 22px var(--accent-shadow);
}
.theme-option-swatch,
.accent-option-swatch {
    display: inline-flex;
    flex: 0 0 auto;
    width: 14px;
    height: 14px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.32);
    box-shadow: inset 0 0 0 1px rgba(12, 16, 24, 0.08);
}
.theme-option-swatch {
    background: var(--theme-swatch, var(--accent));
}
.accent-option-swatch {
    background: var(--accent-option-swatch, var(--accent));
}
.theme-option-label,
.accent-option-label {
    white-space: nowrap;
}
@keyframes dropdown-reveal {
    from {
        opacity: 0;
        transform: translateY(8px) scale(0.97);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}
@keyframes selection-fadeout {
    0% {
        background-color: color-mix(in srgb, var(--accent) 9%, #ffffff 91%);
        border-color: color-mix(in srgb, var(--accent) 18%, #ffffff 82%);
        box-shadow: 0 0 0 0 color-mix(in srgb, var(--accent) 10%, transparent 90%);
    }
    100% {
        background-color: var(--accent-surface);
        border-color: var(--accent-border);
        box-shadow: 0 12px 22px var(--accent-shadow);
    }
}
@keyframes details-enter {
    0% {
        opacity: 0;
        transform: translateY(10px) scale(0.985);
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}
.header-dropdown {
    position: relative;
}
.header-icon-button {
    width: 36px;
    min-width: 36px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
.header-icon-button svg {
    width: 18px;
    height: 18px;
}
.toggle-all-button {
    min-height: 36px;
    padding: 8px 12px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-card);
    color: var(--muted);
    font: inherit;
    font-size: 13px;
    cursor: pointer;
    box-shadow: none;
    transition: border-color 0.18s ease, color 0.18s ease, transform 0.18s ease;
}
.toggle-all-button:hover,
.toggle-all-button:focus-visible {
    color: var(--text);
    border-color: var(--line-strong);
    transform: translateY(-1px);
    outline: none;
}
.toggle-all-button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
    transform: none;
}
.settings-overlay {
    position: fixed;
    inset: 0;
    z-index: 140;
    display: flex;
    justify-content: flex-end;
    pointer-events: none;
}
.settings-overlay.is-open {
    pointer-events: auto;
}
.settings-backdrop {
    position: absolute;
    inset: 0;
    background: var(--overlay);
    opacity: 0;
    transition: opacity 0.2s ease;
}
.settings-sidebar {
    position: relative;
    z-index: 1;
    width: min(380px, calc(100vw - 18px));
    height: 100%;
    margin-left: auto;
    padding: 22px 20px 28px;
    border-left: 1px solid var(--line);
    background: var(--sidebar-bg);
    box-shadow: none;
    overflow-y: auto;
    opacity: 0;
    transform: translateX(calc(100% + 48px));
    transition: transform 0.22s ease, opacity 0.18s ease, box-shadow 0.18s ease;
}
.settings-overlay.is-open .settings-backdrop {
    opacity: 1;
}
.settings-overlay.is-open .settings-sidebar {
    opacity: 1;
    transform: translateX(0);
    box-shadow: -18px 0 44px rgba(15, 21, 31, 0.18);
}
.settings-sidebar-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 20px;
}
.settings-sidebar-intro {
    min-width: 0;
}
.settings-kicker {
    margin: 0 0 8px;
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--muted);
}
.settings-sidebar-title {
    margin: 0;
    font-size: 28px;
    line-height: 1.08;
}
.settings-close-button {
    width: 36px;
    height: 36px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-card-strong);
    color: var(--muted);
    font: inherit;
    font-size: 22px;
    line-height: 1;
    cursor: pointer;
    flex: 0 0 auto;
    transition: border-color 0.18s ease, color 0.18s ease, background 0.18s ease;
}
.settings-close-button:hover,
.settings-close-button:focus-visible {
    color: var(--text);
    border-color: var(--line-strong);
    background: var(--surface-hover);
    outline: none;
}
.settings-sidebar-body {
    display: grid;
    gap: 14px;
}
.settings-section {
    display: grid;
    gap: 12px;
    padding: 16px;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: var(--sidebar-section-bg);
    box-shadow: 0 10px 24px rgba(51, 41, 28, 0.06);
}
.settings-section-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--muted-strong);
}
.settings-theme-host {
    display: grid;
}
.settings-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 14px 0;
    border-top: 1px solid var(--line-soft);
}
.settings-toggle:first-of-type {
    border-top: none;
    padding-top: 4px;
}
.settings-toggle:last-of-type {
    padding-bottom: 0;
}
.settings-toggle-copy {
    min-width: 0;
    display: grid;
    gap: 4px;
}
.settings-toggle-label {
    font-size: 14px;
    color: var(--text);
    line-height: 1.5;
}
.settings-toggle-note {
    font-size: 12px;
    color: var(--muted);
    line-height: 1.45;
}
.settings-switch {
    position: relative;
    flex: 0 0 auto;
    width: 48px;
    height: 30px;
}
.settings-switch-input {
    position: absolute;
    inset: 0;
    opacity: 0;
    margin: 0;
    cursor: pointer;
}
.settings-switch-ui {
    position: absolute;
    inset: 0;
    border-radius: 999px;
    background: rgba(125, 113, 102, 0.22);
    transition: background 0.18s ease;
}
.settings-switch-ui::after {
    content: "";
    position: absolute;
    top: 4px;
    left: 4px;
    width: 22px;
    height: 22px;
    border-radius: 999px;
    background: #ffffff;
    box-shadow: 0 4px 10px rgba(51, 41, 28, 0.18);
    transition: transform 0.18s ease;
}
.settings-switch-input:checked + .settings-switch-ui {
    background: var(--accent);
}
.settings-switch-input:checked + .settings-switch-ui::after {
    transform: translateX(18px);
}
.settings-switch-input:focus-visible + .settings-switch-ui {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}
.records-panel {
    position: fixed;
    top: 0;
    left: 0;
    z-index: 90;
    width: min(var(--history-sidebar-width), calc(100vw - 32px));
    height: 100vh;
    padding: 14px 12px 18px;
    border-right: 1px solid var(--line);
    background: #ffffff;
    box-shadow: 18px 0 42px rgba(51, 41, 28, 0.12);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transform: translateX(calc(-100% - 18px));
    opacity: 0;
    pointer-events: none;
    transition: transform 0.24s ease, opacity 0.2s ease;
}
body.records-open .records-panel {
    transform: translateX(0);
    opacity: 1;
    pointer-events: auto;
}
.records-sidebar-header {
    display: grid;
    gap: 6px;
    padding: 8px 8px 14px;
}
.records-sidebar-kicker {
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--muted);
}
.records-sidebar-title {
    font-size: 24px;
    line-height: 1.08;
    font-weight: 700;
    color: var(--text);
}
.records-sidebar-note {
    font-size: 13px;
    line-height: 1.5;
    color: var(--muted);
}
.records-search {
    position: sticky;
    top: 0;
    z-index: 2;
    margin-bottom: 12px;
    padding: 0 8px 12px;
    background: #ffffff;
}
.records-search-input {
    width: 100%;
    min-height: 40px;
    padding: 0 14px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.96);
    color: var(--text);
    font: inherit;
}
.records-search-input::placeholder {
    color: var(--muted-soft);
}
.records-list-host {
    flex: 1 1 auto;
    overflow: auto;
    padding: 0 8px 4px;
}
.records-list {
    display: grid;
    gap: 10px;
}
.records-item {
    display: grid;
    gap: 10px;
    padding: 12px 14px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--surface-card);
    transition: border-color 0.18s ease, transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}
.records-item.is-current {
    border-color: var(--accent-border);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, var(--surface-card-strong) 100%);
    box-shadow: 0 12px 24px rgba(217, 119, 87, 0.08);
}
.records-item.is-clickable {
    cursor: pointer;
}
.records-item.is-clickable:hover,
.records-item.is-clickable:focus-visible {
    border-color: var(--line-strong);
    background: var(--surface-card-strong);
    transform: translateY(-1px);
    outline: none;
}
.records-item-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}
.records-item-header-main {
    min-width: 0;
    display: grid;
    gap: 4px;
}
.records-item-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
}
.records-item-title {
    display: block;
    font-weight: 600;
    color: var(--text);
    overflow-wrap: anywhere;
}
.records-item-badge {
    display: inline-flex;
    align-items: center;
    min-height: 22px;
    padding: 0 8px;
    border-radius: 999px;
    background: rgba(217, 119, 87, 0.12);
    color: var(--accent);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.02em;
    white-space: nowrap;
}
.records-item-meta {
    display: block;
    font-size: 12px;
    color: var(--muted);
}
.records-item-actions {
    position: relative;
    display: flex;
    align-items: flex-start;
    justify-content: flex-end;
    flex: 0 0 auto;
}
.records-item-menu-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    min-width: 34px;
    height: 34px;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-card-strong);
    color: var(--muted);
    cursor: pointer;
    transition: border-color 0.18s ease, color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}
.records-item-menu-toggle:hover,
.records-item-menu-toggle:focus-visible {
    color: var(--text);
    border-color: var(--line-strong);
    background: var(--paper);
    transform: translateY(-1px);
    outline: none;
}
.records-item-menu-toggle-dots {
    display: inline-flex;
    align-items: center;
    gap: 3px;
}
.records-item-menu-toggle-dots span {
    width: 4px;
    height: 4px;
    border-radius: 999px;
    background: currentColor;
}
.records-item-menu {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    z-index: 3;
    display: grid;
    gap: 8px;
    min-width: 116px;
    padding: 10px;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--surface-panel);
    box-shadow: 0 22px 40px rgba(51, 41, 28, 0.16);
}
.records-item-menu[hidden] {
    display: none;
}
.records-item-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 34px;
    padding: 0 12px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-card-strong);
    color: var(--muted);
    font: inherit;
    font-size: 13px;
    cursor: pointer;
    flex: 0 0 auto;
    transition: border-color 0.18s ease, color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}
.records-item-action:hover,
.records-item-action:focus-visible {
    color: var(--text);
    border-color: var(--line-strong);
    background: var(--paper);
    transform: translateY(-1px);
    outline: none;
}
.records-item-action.is-danger {
    border-color: rgba(191, 72, 54, 0.22);
    background: rgba(255, 240, 238, 0.92);
    color: #bf4836;
}
.records-item-action.is-danger:hover,
.records-item-action.is-danger:focus-visible {
    border-color: rgba(191, 72, 54, 0.36);
    background: rgba(255, 232, 229, 0.98);
    color: #a63526;
}
.records-item-files {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.records-file-link {
    display: inline-flex;
    align-items: center;
    min-height: 26px;
    padding: 0 8px;
    border-radius: 999px;
    background: rgba(125, 113, 102, 0.08);
    color: var(--muted);
    font-size: 12px;
}
.records-file-kind {
    font-weight: 700;
    letter-spacing: 0.03em;
}
.records-file-name {
    color: var(--muted);
    overflow-wrap: anywhere;
}
.records-empty {
    padding: 14px 12px;
    color: var(--muted);
    font-size: 14px;
}
.records-empty.is-search-empty {
    padding: 18px 12px 10px;
}
.system-panel {
    margin-bottom: 24px;
}
.conversation-shell {
    flex: 1 1 auto;
    width: min(100%, var(--content-max-width));
    margin: 0 auto;
    min-width: 0;
    background: transparent;
    border: none;
    border-radius: 0;
    box-shadow: none;
    backdrop-filter: none;
    overflow: visible;
    padding-top: 0;
    transform: translateX(var(--history-sidebar-shift));
    transition: transform 0.24s ease;
}
.conversation {
    min-height: 220px;
    overflow: visible;
    padding: 10px 22px 18px;
}
.turn-map {
    position: fixed;
    top: 50%;
    right: clamp(10px, 2.4vw, 24px);
    z-index: 74;
    width: 32px;
    max-height: min(70vh, 640px);
    transform: translateY(-50%);
    transition: width 0.24s ease;
}
.turn-map:hover,
.turn-map:focus-within {
    width: min(304px, calc(100vw - 24px));
}
.turn-map-list {
    max-height: inherit;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 3px;
    border: 1px solid transparent;
    border-radius: 24px;
    background: transparent;
    box-shadow: none;
    scrollbar-width: none;
    transition: padding 0.24s ease, border-color 0.2s ease, background 0.2s ease, box-shadow 0.24s ease;
}
.turn-map-list::-webkit-scrollbar {
    width: 0;
    height: 0;
}
.turn-map:hover .turn-map-list,
.turn-map:focus-within .turn-map-list {
    padding: 10px 8px 10px 10px;
    border-color: var(--line);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, var(--surface-panel) 100%);
    box-shadow: 0 24px 48px rgba(51, 41, 28, 0.14);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
}
.turn-map-item {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding: 6px 2px;
    border: 1px solid transparent;
    border-radius: 14px;
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}
.turn-map:hover .turn-map-item,
.turn-map:focus-within .turn-map-item {
    justify-content: flex-end;
    gap: 10px;
    padding: 7px 8px 7px 10px;
}
.turn-map-item:hover,
.turn-map-item:focus-visible {
    border-color: var(--accent-border);
    background: var(--surface-hover);
    box-shadow: 0 12px 24px var(--accent-glow);
    transform: translateX(-2px);
    outline: none;
}
.turn-map-item.is-active {
    color: var(--text);
}
.turn-map:hover .turn-map-item.is-active,
.turn-map:focus-within .turn-map-item.is-active {
    border-color: var(--accent-border);
    background: rgba(255, 255, 255, 0.82);
}
.turn-map-preview {
    flex: 1 1 auto;
    min-width: 0;
    max-width: 0;
    overflow: hidden;
    opacity: 0;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.45;
    text-align: left;
    white-space: nowrap;
    text-overflow: ellipsis;
    transform: translateX(12px);
    transition: max-width 0.24s ease, opacity 0.18s ease, transform 0.24s ease, color 0.18s ease;
}
.turn-map:hover .turn-map-preview,
.turn-map:focus-within .turn-map-preview {
    max-width: 220px;
    opacity: 1;
    transform: translateX(0);
}
.turn-map-item.is-active .turn-map-preview {
    color: var(--text);
}
.turn-map-dash {
    flex: 0 0 auto;
    width: 10px;
    height: 4px;
    border-radius: 999px;
    background: var(--line-strong);
    transition: width 0.18s ease, background 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
}
.turn-map-item:hover .turn-map-dash,
.turn-map-item:focus-visible .turn-map-dash {
    background: var(--accent);
}
.turn-map-item.is-active .turn-map-dash {
    width: 18px;
    background: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-glow);
}
.scroll-bottom-button {
    position: fixed;
    right: var(--scroll-bottom-right, clamp(10px, 2.4vw, 24px));
    bottom: var(--scroll-bottom-bottom, calc(var(--composer-reserve) + 18px));
    z-index: 79;
    width: 34px;
    height: 34px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-panel);
    color: var(--muted);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 10px 22px rgba(51, 41, 28, 0.14);
    cursor: pointer;
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transform: translateY(8px) scale(0.96);
    transition: opacity 0.18s ease, transform 0.2s ease, color 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}
.scroll-bottom-button svg {
    width: 16px;
    height: 16px;
}
.scroll-bottom-button.is-visible {
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    transform: translateY(0) scale(1);
}
.scroll-bottom-button:hover,
.scroll-bottom-button:focus-visible {
    color: var(--text);
    border-color: var(--line-strong);
    background: var(--surface-card-strong);
    outline: none;
}
.empty-state {
    display: none;
}
.empty-state h2 {
    margin: 0;
    font-size: 24px;
}
.empty-state p {
    margin: 0;
    color: var(--muted);
}
.empty-kicker {
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--accent);
}
.composer-card {
    position: fixed;
    left: 50%;
    bottom: calc(var(--composer-gap) + env(safe-area-inset-bottom, 0px));
    z-index: 80;
    width: min(var(--content-max-width), calc(100% - (var(--page-gutter) * 2)));
    max-width: calc(100% - (var(--page-gutter) * 2));
    margin: 0;
    background: var(--surface-elevated);
    border: 1px solid var(--line);
    border-radius: 28px;
    padding: 14px 16px 14px;
    box-shadow: 0 20px 50px rgba(51, 41, 28, 0.12);
    backdrop-filter: blur(14px);
    transform: translateX(calc(-50% + var(--history-sidebar-shift)));
    transition: transform 0.24s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}
.composer-card.expanded #chat-input {
    min-height: 170px;
    max-height: 320px;
}
.textarea-wrap {
    position: relative;
}
#chat-input {
    width: 100%;
    min-height: 72px;
    max-height: 180px;
    resize: none;
    overflow-y: auto;
    border: none;
    background: transparent;
    color: var(--text);
    font: inherit;
    font-size: 16px;
    line-height: 1.72;
    padding: 6px 44px 4px 2px;
    outline: none;
}
#chat-input::placeholder {
    color: var(--muted-soft);
}
.icon-button {
    position: absolute;
    top: 4px;
    right: 0;
    width: 34px;
    height: 34px;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--surface-card-strong);
    color: var(--muted);
    cursor: pointer;
    box-shadow: var(--shadow);
}
.icon-button:hover,
.icon-button:focus-visible {
    color: var(--text);
    border-color: var(--line-strong);
    outline: none;
}
.composer-card.is-drag-over {
    border-color: var(--accent-tint);
    background: var(--surface-panel);
    box-shadow: 0 0 0 4px var(--accent-glow), 0 20px 50px rgba(51, 41, 28, 0.12);
}
.attachment-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 4px 0 10px;
}
.attachment-card {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: min(240px, 100%);
    max-width: 100%;
    padding: 8px 10px;
    border-radius: 18px;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--muted-strong);
}
.attachment-thumb,
.attachment-thumb-placeholder {
    width: 54px;
    height: 54px;
    border-radius: 14px;
    flex: 0 0 auto;
}
.attachment-thumb {
    display: block;
    object-fit: cover;
    border: 1px solid var(--line-soft);
    background: var(--surface-card-strong);
}
.attachment-thumb-placeholder {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px dashed var(--accent-border);
    background: rgba(255, 255, 255, 0.88);
    color: var(--accent);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.attachment-text {
    min-width: 0;
    display: grid;
    gap: 4px;
}
.attachment-name {
    font-size: 13px;
    line-height: 1.45;
    overflow-wrap: anywhere;
}
.attachment-kind {
    font-size: 12px;
    color: var(--muted);
}
.attachment-remove {
    margin-left: auto;
    width: 28px;
    height: 28px;
    border: none;
    border-radius: 999px;
    background: var(--surface-card);
    color: inherit;
    cursor: pointer;
    font: inherit;
    font-size: 16px;
    line-height: 1;
}
.attachment-remove:hover,
.attachment-remove:focus-visible {
    background: var(--surface-card-strong);
    outline: none;
}
.composer-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: nowrap;
    gap: clamp(6px, 1vw, 12px);
    margin-top: 2px;
}
.toolbar-left,
.toolbar-right {
    display: flex;
    align-items: center;
    gap: clamp(6px, 0.9vw, 10px);
    flex-wrap: wrap;
}
.toolbar-left {
    flex: 1 1 auto;
    min-width: 0;
}
.toolbar-right {
    flex: 0 1 auto;
    margin-left: auto;
}
.context-meter-shell {
    position: relative;
    display: inline-flex;
    align-items: center;
    flex: 0 0 auto;
}
.context-meter {
    --context-progress: 0.0;
    --context-ring-color: var(--accent);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    padding: 0;
    border: none;
    border-radius: 999px;
    background: transparent;
    color: var(--muted);
    cursor: default;
    flex: 0 0 auto;
}
.context-meter:hover,
.context-meter:focus-visible {
    outline: none;
}
.context-meter.is-over-limit {
    --context-ring-color: #c74b3c;
    color: #b84334;
}
.context-meter-ring {
    position: relative;
    flex: 0 0 auto;
    width: 18px;
    height: 18px;
    border-radius: 999px;
    background: conic-gradient(var(--context-ring-color) calc(var(--context-progress) * 1turn), rgba(125, 113, 102, 0.18) 0);
}
.context-meter-ring-core {
    position: absolute;
    inset: 3px;
    border-radius: 999px;
    background: var(--surface-elevated);
}
.context-meter-popover {
    position: absolute;
    right: 0;
    bottom: calc(100% + 10px);
    display: grid;
    gap: 4px;
    min-width: 132px;
    max-width: min(220px, calc(100vw - 40px));
    padding: 10px 12px;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--surface-elevated);
    box-shadow: 0 18px 40px rgba(51, 41, 28, 0.12);
    backdrop-filter: blur(10px);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transform: translateY(6px) scale(0.98);
    transform-origin: bottom right;
    transition: opacity 0.16s ease, transform 0.18s ease, visibility 0s linear 0.18s;
}
.context-meter-popover::after {
    content: "";
    position: absolute;
    right: 12px;
    top: calc(100% - 1px);
    width: 10px;
    height: 10px;
    border-right: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    background: var(--surface-elevated);
    transform: rotate(45deg);
}
.context-meter-shell:hover .context-meter-popover,
.context-meter-shell:focus-within .context-meter-popover {
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    transform: translateY(0) scale(1);
    transition-delay: 0s;
}
.context-meter-value {
    font-size: 13px;
    line-height: 1.3;
    color: var(--text);
    white-space: nowrap;
}
.context-meter-detail {
    font-size: 12px;
    line-height: 1.35;
    color: var(--muted);
    white-space: nowrap;
}
.context-meter-detail-button {
    min-height: 28px;
    padding: 0 10px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-card);
    color: var(--muted-strong);
    font: inherit;
    font-size: 12px;
    cursor: pointer;
    transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease;
}
.context-meter-detail-button:hover,
.context-meter-detail-button:focus-visible {
    border-color: var(--line-strong);
    background: var(--surface-hover);
    color: var(--text);
    outline: none;
}
.context-meter-status {
    font-size: 12px;
    line-height: 1.3;
    color: #b84334;
}
.toolbar-dropdown {
    position: relative;
    flex: 0 0 auto;
}
.toolbar-plus,
.toolbar-menu-button,
.toolbar-select,
.send-button {
    min-height: 40px;
    border-radius: 16px;
    font: inherit;
}
.toolbar-plus,
.toolbar-menu-button,
.toolbar-select {
    border: 1px solid transparent;
    background: transparent;
    color: var(--muted);
    transition: border-color 0.18s ease, background-color 0.22s ease, color 0.18s ease, box-shadow 0.22s ease, transform 0.18s ease;
}
.toolbar-plus {
    width: 36px;
    font-size: 28px;
    line-height: 1;
    cursor: pointer;
}
.toolbar-menu-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: auto;
    white-space: nowrap;
}
.toolbar-select {
    max-width: 180px;
    padding: 0 10px;
    appearance: none;
    cursor: pointer;
}
.toolbar-select:hover,
.toolbar-select:focus-visible,
.toolbar-plus:hover,
.toolbar-plus:focus-visible,
.toolbar-menu-button:hover,
.toolbar-menu-button:focus-visible {
    background: var(--surface-hover);
    color: var(--text);
    outline: none;
}
.toolbar-menu-button {
    padding: 0 10px;
    cursor: pointer;
}
.toolbar-pill-button {
    position: relative;
    padding: 0 28px 0 12px;
}
.toolbar-pill-button::after {
    content: "";
    position: absolute;
    right: 11px;
    top: 50%;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid currentColor;
    transform: translateY(-35%);
    opacity: 0.78;
}
.extra-slot {
    position: relative;
}
.extra-menu {
    position: absolute;
    left: 0;
    top: auto;
    bottom: calc(100% + 10px);
    z-index: 30;
    min-width: 280px;
    padding: 14px;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: var(--surface-panel);
    box-shadow: 0 24px 48px rgba(51, 41, 28, 0.14);
    transform-origin: bottom left;
    will-change: transform, opacity;
}
.dropdown-menu {
    min-width: 180px;
    padding: 8px;
}
.extra-menu[data-open="true"],
.dropdown-menu[data-open="true"] {
    animation: dropdown-reveal 0.22s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.extra-menu-grid {
    display: grid;
    gap: 12px;
}
.dropdown-option {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid transparent;
    border-radius: 14px;
    background: transparent;
    color: var(--muted);
    font: inherit;
    text-align: left;
    cursor: pointer;
    transition: background-color 0.2s ease, color 0.18s ease, border-color 0.18s ease, box-shadow 0.22s ease, transform 0.18s ease;
}
.dropdown-option:hover,
.dropdown-option:focus-visible {
    background-color: var(--surface-hover);
    color: var(--text);
    outline: none;
}
.dropdown-option.is-selected {
    transform: translateY(-1px);
    animation: selection-fadeout 0.26s ease-out both;
}
.dropdown-option-meta {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: var(--muted);
}
.dropdown-option.is-selected .dropdown-option-meta {
    color: var(--accent);
    opacity: 0.72;
}
.extra-field {
    display: grid;
    gap: 6px;
}
.extra-field label {
    font-size: 13px;
    color: var(--muted);
}
.extra-field input[type="text"] {
    width: 100%;
    min-height: 40px;
    padding: 0 12px;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--surface-card-strong);
    font: inherit;
    color: var(--text);
}
.extra-field input[type="text"]:focus-visible {
    border-color: var(--accent-border);
    outline: none;
    box-shadow: 0 0 0 3px var(--accent-glow);
}
.extra-field--choices {
    gap: 10px;
}
.extra-choice-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}
.extra-choice-button {
    min-height: 38px;
    padding: 0 14px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background-color: var(--surface-card-strong);
    color: var(--muted-strong);
    font: inherit;
    cursor: pointer;
    transition: border-color 0.18s ease, background-color 0.22s ease, color 0.18s ease, box-shadow 0.22s ease, transform 0.18s ease;
}
.extra-choice-button:hover,
.extra-choice-button:focus-visible {
    border-color: var(--line-strong);
    background-color: var(--surface-hover);
    color: var(--text);
    outline: none;
    transform: translateY(-1px);
}
.extra-toggle {
    width: 100%;
    min-height: 58px;
    padding: 0 14px;
    border: 1px solid var(--line);
    border-radius: 18px;
    background-color: var(--surface-card-strong);
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 12px;
    font: inherit;
    cursor: pointer;
    transition: border-color 0.18s ease, background-color 0.22s ease, color 0.18s ease, box-shadow 0.22s ease, transform 0.18s ease;
}
.extra-toggle:hover,
.extra-toggle:focus-visible {
    border-color: var(--line-strong);
    background-color: var(--surface-hover);
    outline: none;
    transform: translateY(-1px);
}
.extra-toggle-indicator {
    position: relative;
    width: 20px;
    height: 20px;
    flex: 0 0 auto;
    border-radius: 999px;
    border: 1.5px solid var(--line-strong);
    background: var(--surface-panel);
    transition: border-color 0.18s ease, background-color 0.22s ease;
}
.extra-toggle-indicator::after {
    content: "";
    position: absolute;
    inset: 4px;
    border-radius: 999px;
    background: var(--accent);
    opacity: 0;
    transform: scale(0.45);
    transition: opacity 0.18s ease, transform 0.22s ease;
}
.extra-toggle.is-checked .extra-toggle-indicator {
    border-color: var(--accent);
    background: rgba(255, 255, 255, 0.72);
}
.extra-toggle.is-checked .extra-toggle-indicator::after {
    opacity: 1;
    transform: scale(1);
}
.extra-toggle-label {
    text-align: left;
    line-height: 1.45;
}
.theme-option.is-selected:hover,
.theme-option.is-selected:focus-visible,
.accent-option.is-selected:hover,
.accent-option.is-selected:focus-visible,
.dropdown-option.is-selected:hover,
.dropdown-option.is-selected:focus-visible,
.extra-choice-button.is-selected:hover,
.extra-choice-button.is-selected:focus-visible,
.extra-toggle.is-checked:hover,
.extra-toggle.is-checked:focus-visible {
    border-color: var(--accent-border);
    background-color: var(--accent-surface);
    color: var(--accent);
    box-shadow: 0 12px 22px var(--accent-shadow);
}
.extra-choice-button.is-selected,
.extra-toggle.is-checked {
    animation: selection-fadeout 0.26s ease-out both;
}
.extra-menu-grid > *.is-detail-enter {
    opacity: 0;
    transform-origin: top center;
    animation: details-enter 0.24s cubic-bezier(0.2, 0.9, 0.2, 1) forwards;
    animation-delay: var(--detail-enter-delay, 0ms);
}
.toolbar-menu-button.is-feature-pill,
.toolbar-menu-button.is-open {
    border-color: transparent;
    background-color: transparent;
    color: var(--muted);
    box-shadow: none;
}
.toolbar-menu-button.is-feature-pill:hover,
.toolbar-menu-button.is-feature-pill:focus-visible,
.toolbar-menu-button.is-open:hover,
.toolbar-menu-button.is-open:focus-visible {
    background: var(--surface-hover);
    color: var(--text);
    border-color: transparent;
    box-shadow: none;
    outline: none;
}
.send-button {
    padding: 0 16px;
    border: 1px solid var(--theme-accent-border);
    background-color: var(--theme-accent);
    color: #ffffff;
    cursor: pointer;
    box-shadow: 0 12px 22px var(--theme-accent-shadow);
    flex: 0 0 auto;
    transition: transform 0.18s ease, box-shadow 0.22s ease, background-color 0.22s ease, border-color 0.18s ease, opacity 0.18s ease;
}
.send-button:hover,
.send-button:focus-visible {
    transform: translateY(-1px);
    box-shadow: 0 16px 28px var(--theme-accent-shadow);
    outline: none;
}
.send-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
}
.turn {
    margin-bottom: 28px;
}
.user-row {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
}
.user-bubble {
    max-width: min(82%, 720px);
    background: var(--user);
    border: 1px solid var(--user-border);
    border-radius: 22px;
    padding: 16px 18px;
    box-shadow: var(--shadow);
}
.assistant-block {
    margin-top: 14px;
    padding-left: 6px;
}
.assistant-response-row {
    position: relative;
}
.assistant-response-main {
    width: 100%;
    min-width: 0;
}
.assistant-status-indicator {
    position: absolute;
    left: -34px;
    top: auto;
    bottom: 6px;
    width: 24px;
    height: 24px;
    border-radius: 999px;
    border: 1px solid var(--line-soft);
    background: var(--surface-elevated);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    pointer-events: none;
    box-shadow: 0 10px 22px rgba(51, 41, 28, 0.12);
    transition: opacity 0.6s ease, transform 0.28s ease;
}
.assistant-status-spinner {
    width: 13px;
    height: 13px;
    border: 2px solid var(--muted-soft);
    border-top-color: transparent;
    border-radius: 999px;
    animation: assistantSpin 0.82s linear infinite;
}
.assistant-status-check {
    display: none;
    width: 8px;
    height: 12px;
    border-right: 2px solid var(--accent);
    border-bottom: 2px solid var(--accent);
    transform: rotate(40deg) translate(-1px, -1px);
}
.assistant-status-indicator.is-done .assistant-status-spinner {
    display: none;
}
.assistant-status-indicator.is-done .assistant-status-check {
    display: block;
}
.assistant-status-indicator.is-fadeout {
    opacity: 0;
    transform: translateY(-2px);
}
@keyframes assistantSpin {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}
.message-content {
    font-size: 16px;
    overflow-wrap: anywhere;
}
.message-content > :first-child {
    margin-top: 0;
}
.message-content > :last-child {
    margin-bottom: 0;
}
.message-content h1,
.message-content h2,
.message-content h3,
.message-content h4 {
    margin: 1.1em 0 0.55em;
    line-height: 1.35;
}
.message-content p,
.message-content ul,
.message-content ol,
.message-content blockquote,
.message-content pre {
    margin: 0 0 0.9em;
}
.message-content ul,
.message-content ol {
    padding-left: 1.4em;
}
.message-content blockquote {
    margin-left: 0;
    padding: 0.1em 1em;
    border-left: 3px solid var(--quote-border);
    color: var(--quote-text);
    background: var(--quote-bg);
    border-radius: 0 12px 12px 0;
}
.message-content code {
    padding: 0.1em 0.36em;
    border-radius: 6px;
    background: var(--inline-code-bg);
    color: var(--inline-code-text);
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 0.92em;
}
.message-content pre {
    padding: 14px 16px;
    border-radius: 14px;
    background: var(--code-bg);
    color: var(--code-text);
    overflow-x: auto;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.05);
}
.message-content pre code {
    padding: 0;
    background: transparent;
    color: inherit;
}
.message-content table {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 0.95em;
    display: block;
    overflow-x: auto;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--surface-card);
}
.message-content th,
.message-content td {
    border: 1px solid var(--line);
    padding: 8px 10px;
    min-width: 88px;
    vertical-align: top;
}
.message-content th {
    background: var(--surface-hover);
    font-weight: 700;
}
.message-content tr:nth-child(even) td {
    background: rgba(255, 255, 255, 0.55);
}
        .message-content .katex-display {
            overflow-x: auto;
            overflow-y: hidden;
            padding: 0.15em 0;
        }
.message-content a {
    color: var(--accent);
    text-decoration: none;
}
.message-content a:hover {
    text-decoration: underline;
}
.message-content--live {
    white-space: pre-wrap;
}
.message-actions {
    display: flex;
    gap: 8px;
    width: 100%;
}
.bubble-actions-user {
    justify-content: flex-end;
    padding-right: 6px;
}
.bubble-actions-assistant {
    justify-content: flex-start;
    margin-top: 8px;
    margin-left: 2px;
}
.message-action-btn {
    width: 30px;
    height: 30px;
    border: none;
    border-radius: 999px;
    background: transparent;
    color: var(--meta-text);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 0.18s ease, color 0.18s ease, background 0.18s ease;
}
.message-action-btn svg {
    width: 15px;
    height: 15px;
}
.message-action-btn:hover,
.message-action-btn:focus-visible {
    color: var(--accent);
    background: var(--surface-hover);
    transform: translateY(-1px);
    outline: none;
}
.stream-render-surface {
    position: relative;
}
.stream-fade-burst {
    animation: streamFadeIn 220ms ease;
    will-change: opacity;
}
@keyframes streamFadeIn {
    from {
        opacity: 0.18;
    }
    to {
        opacity: 1;
    }
}
.image-grid {
    display: grid;
    gap: 12px;
    margin-top: 12px;
}
.image-card {
    background: var(--surface-card);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 10px;
}
.image-card img {
    display: block;
    width: 100%;
    border-radius: 10px;
    max-height: 420px;
    object-fit: contain;
    background: var(--surface-card-strong);
}
.image-card a {
    display: inline-block;
    margin-top: 8px;
    font-size: 13px;
    color: var(--muted);
    text-decoration: none;
}
.meta-section + .meta-section {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--line);
}
.meta-title {
    margin-bottom: 8px;
    font-size: 13px;
    font-weight: 700;
    color: var(--muted);
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.chip-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.chip {
    display: inline-flex;
    align-items: center;
    padding: 6px 10px;
    border-radius: 999px;
    background: var(--inline-code-bg);
    color: var(--muted-strong);
    font-size: 13px;
}
.tool-list {
    display: grid;
    gap: 10px;
}
.tool-item {
    padding: 12px 14px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--surface-card);
}
.tool-name {
    font-weight: 600;
}
.tool-status {
    margin-left: 8px;
    color: var(--accent);
    font-size: 13px;
}
.kv-list {
    display: grid;
    gap: 8px;
}
.kv-item {
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--surface-card);
    border: 1px solid var(--line);
}
.kv-key {
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}
.source-list {
    display: grid;
    gap: 10px;
}
.source-item {
    padding: 12px 14px;
    border-radius: 14px;
    background: var(--surface-card);
    border: 1px solid var(--line);
}
.source-title {
    color: var(--accent);
    font-weight: 600;
    text-decoration: none;
}
.source-url {
    margin-top: 4px;
    color: var(--muted);
    font-size: 12px;
    overflow-wrap: anywhere;
}
details.meta-box {
    background: var(--surface-card-strong);
    border: 1px solid var(--line);
    border-radius: 18px;
    box-shadow: var(--shadow);
    overflow: hidden;
}
details.meta-box summary {
    cursor: pointer;
    list-style: none;
    font-size: 14px;
    color: var(--muted);
    user-select: none;
    padding: 0;
}
details.meta-box summary::-webkit-details-marker {
    display: none;
}
details.meta-box[open] summary {
    border-bottom: 1px solid var(--line);
    color: var(--text);
}
.meta-content {
    padding: 16px 18px 18px;
    background: var(--surface-card-strong);
}
.summary-row {
    display: inline-flex;
    align-items: center;
    justify-content: flex-start;
    gap: 10px;
    max-width: 100%;
    padding: 12px 16px;
}
.summary-label {
    min-width: 0;
    overflow-wrap: anywhere;
}
.summary-caret {
    flex: 0 0 auto;
    width: 0;
    height: 0;
    border-top: 5px solid transparent;
    border-bottom: 5px solid transparent;
    border-left: 7px solid currentColor;
    color: var(--muted);
    transform-origin: 35% 50%;
    transition: transform 0.18s ease;
}
details.meta-box[open] .summary-caret {
    transform: rotate(90deg);
}
details.assistant-meta-box {
    display: inline-block;
    width: auto;
    max-width: 100%;
    vertical-align: top;
}
details.assistant-meta-box[open] {
    width: min(100%, var(--assistant-meta-open-width, 760px));
}
details.assistant-meta-box summary {
    color: var(--meta-summary);
}
details.assistant-meta-box[open] summary {
    color: var(--meta-summary);
}
details.assistant-meta-box .meta-content,
details.assistant-meta-box .message-content {
    color: var(--meta-text);
}
.browser-attachment-meta {
    margin-top: 12px;
}
.supplement-thread {
    display: grid;
    gap: 12px;
    margin-top: 14px;
}
.supplement-turn {
    display: grid;
    gap: 8px;
}
.supplement-assistant {
    padding: 12px 14px;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--surface-elevated);
}
.supplement-meta {
    margin-top: 8px;
    color: var(--muted);
    font-size: 13px;
}
.supplement-user-row {
    display: flex;
    justify-content: flex-end;
}
.supplement-user {
    max-width: min(88%, 480px);
    padding: 12px 14px;
    border-radius: 16px;
    background: var(--user);
    border: 1px solid var(--user-border);
}
.live-activity-host {
    margin-bottom: 12px;
}
.live-log {
    margin-bottom: 12px;
}
.warning-banner {
    margin-bottom: 12px;
    padding: 10px 12px;
    border: 1px solid #ebcf9d;
    border-radius: 12px;
    background: #fff6df;
    color: #7a5a19;
    font-size: 14px;
}
.confirm-dialog-overlay {
    position: fixed;
    inset: 0;
    z-index: 150;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
.confirm-dialog-overlay[hidden] {
    display: none;
}
.confirm-dialog-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(10, 14, 22, 0.44);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}
.confirm-dialog {
    position: relative;
    z-index: 1;
    width: min(420px, calc(100vw - 32px));
    padding: 22px 22px 20px;
    border: 1px solid var(--line);
    border-radius: 24px;
    background: var(--surface-panel);
    box-shadow: 0 30px 60px rgba(15, 21, 31, 0.2);
}
.confirm-dialog-header {
    display: grid;
    gap: 6px;
    margin-bottom: 14px;
}
.confirm-dialog-kicker {
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #b84334;
}
.confirm-dialog-title {
    margin: 0;
    font-size: 26px;
    line-height: 1.06;
}
.confirm-dialog-body {
    margin: 0;
    color: var(--muted);
    line-height: 1.6;
}
.confirm-dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
}
.confirm-dialog-button {
    min-height: 40px;
    padding: 0 16px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-card-strong);
    color: var(--muted);
    font: inherit;
    cursor: pointer;
    transition: border-color 0.18s ease, color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}
.confirm-dialog-button:hover,
.confirm-dialog-button:focus-visible {
    color: var(--text);
    border-color: var(--line-strong);
    background: var(--paper);
    transform: translateY(-1px);
    outline: none;
}
.confirm-dialog-button.is-danger {
    border-color: rgba(191, 72, 54, 0.24);
    background: linear-gradient(135deg, #d86352 0%, #bf4836 100%);
    color: #ffffff;
}
.confirm-dialog-button.is-danger:hover,
.confirm-dialog-button.is-danger:focus-visible {
    border-color: rgba(191, 72, 54, 0.4);
    background: linear-gradient(135deg, #cf5442 0%, #b33d2d 100%);
    color: #ffffff;
}
.usage-detail-overlay {
    position: fixed;
    inset: 0;
    z-index: 145;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
.usage-detail-overlay[hidden] {
    display: none;
}
.usage-detail-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(10, 14, 22, 0.44);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}
.usage-detail-dialog {
    position: relative;
    z-index: 1;
    width: min(760px, calc(100vw - 32px));
    max-height: min(80vh, 760px);
    overflow: auto;
    padding: 22px;
    border: 1px solid var(--line);
    border-radius: 24px;
    background: var(--surface-panel);
    box-shadow: 0 30px 60px rgba(15, 21, 31, 0.2);
}
.usage-detail-header {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 4px 16px;
    align-items: start;
    margin-bottom: 14px;
}
.usage-detail-kicker {
    grid-column: 1;
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--muted);
}
.usage-detail-title {
    grid-column: 1;
    margin: 0;
    font-size: 24px;
    line-height: 1.1;
}
.usage-detail-close {
    grid-column: 2;
    grid-row: 1 / span 2;
    width: 34px;
    height: 34px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-card-strong);
    color: var(--muted);
    font: inherit;
    font-size: 22px;
    line-height: 1;
    cursor: pointer;
}
.usage-detail-close:hover,
.usage-detail-close:focus-visible {
    border-color: var(--line-strong);
    color: var(--text);
    outline: none;
}
.usage-detail-summary {
    font-size: 13px;
    color: var(--muted);
    margin-bottom: 12px;
}
.usage-token-meta {
    position: relative;
    display: inline-flex;
    align-items: center;
    color: var(--text);
    cursor: help;
}
.usage-token-meta-value {
    text-decoration: underline dotted;
    text-underline-offset: 2px;
}
.usage-token-meta-tooltip {
    position: absolute;
    left: 50%;
    bottom: calc(100% + 8px);
    transform: translateX(-50%);
    padding: 6px 8px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface-card-strong);
    color: var(--text);
    font-size: 12px;
    line-height: 1.3;
    white-space: nowrap;
    box-shadow: 0 8px 20px rgba(15, 21, 31, 0.16);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transition: opacity 0.14s ease, transform 0.14s ease, visibility 0s linear 0.14s;
}
.usage-token-meta:hover .usage-token-meta-tooltip,
.usage-token-meta:focus-visible .usage-token-meta-tooltip {
    opacity: 1;
    visibility: visible;
    transform: translateX(-50%) translateY(-1px);
    transition-delay: 0s;
}
.usage-detail-body {
    display: grid;
    gap: 10px;
}
.usage-detail-table {
    width: 100%;
    border-collapse: collapse;
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
    background: var(--surface-card-strong);
}
.usage-detail-table th,
.usage-detail-table td {
    border-bottom: 1px solid var(--line-soft);
    padding: 10px 12px;
    text-align: left;
    font-size: 13px;
}
.usage-detail-table th {
    background: var(--surface-hover);
    color: var(--muted-strong);
}
.usage-detail-table tr:last-child td {
    border-bottom: none;
}
.usage-detail-empty {
    padding: 14px;
    border: 1px dashed var(--line);
    border-radius: 14px;
    color: var(--muted);
}
@media (max-width: 900px) {
    .turn-map {
        display: none !important;
    }
}
@media (max-width: 720px) {
    :root {
        --page-gutter: 14px;
        --history-sidebar-width: 248px;
        --history-sidebar-visible-width: min(var(--history-sidebar-width), calc(100vw - 28px));
        --history-sidebar-shift-open: calc(var(--history-sidebar-visible-width) / 2);
        --history-header-shift-open: var(--history-sidebar-visible-width);
    }
    .page {
        padding-bottom: calc(var(--composer-reserve) + 26px);
    }
    .header {
        flex-direction: column;
        align-items: stretch;
    }
    .browser-header {
        top: 0;
        padding: 8px 0 4px;
    }
    .browser-header-actions {
        width: 100%;
        justify-content: flex-end;
        flex-wrap: wrap;
    }
    .header-theme-field {
        width: 100%;
    }
    .records-panel {
        width: min(var(--history-sidebar-width), calc(100vw - 28px));
        padding: 12px 10px 16px;
    }
    .settings-sidebar {
        width: min(100%, 360px);
        padding: 20px 16px 24px;
    }
    .settings-section {
        padding: 14px;
    }
    .conversation {
        min-height: 220px;
        padding: 8px 14px 14px;
    }
    .assistant-status-indicator {
        left: -28px;
    }
    .user-bubble {
        max-width: 100%;
    }
    .composer-toolbar {
        flex-direction: column;
        align-items: stretch;
        flex-wrap: wrap;
    }
    .toolbar-left,
    .toolbar-right {
        width: 100%;
        justify-content: flex-start;
    }
    .toolbar-right {
        margin-left: 0;
    }
    .extra-menu {
        left: auto;
        right: 0;
        top: auto;
        bottom: calc(100% + 8px);
        width: min(320px, calc(100vw - 48px));
    }
    .context-meter-popover {
        left: 0;
        right: auto;
        transform-origin: bottom left;
    }
    .context-meter-popover::after {
        left: 12px;
        right: auto;
    }
    .scroll-bottom-button {
        right: var(--scroll-bottom-right, 14px);
        bottom: var(--scroll-bottom-bottom, calc(var(--composer-reserve) + 12px));
    }
}
"""

