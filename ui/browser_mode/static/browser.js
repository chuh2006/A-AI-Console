(() => {
    const CONTEXT_TIER_WARNING_THRESHOLD = 32000;
    const COMPOSER_COLLAPSED_MIN_HEIGHT = 72;
    const COMPOSER_COLLAPSED_MAX_HEIGHT = 180;
    const COMPOSER_EXPANDED_MIN_HEIGHT = 170;
    const COMPOSER_EXPANDED_MAX_HEIGHT = 320;
    const bootstrap = window.__NEODS_BROWSER_BOOTSTRAP__ || {
        models: [],
        defaultModel: "deepseek-v4-flash",
        theme: {
            value: "orange",
            options: [{ id: "orange", label: "橙色", swatch: "#d97757" }],
            accentValue: "orange",
            accentOptions: [{ id: "orange", label: "橙色", swatch: "#d97757", start: "#e28f6d", end: "#d97757" }],
        },
        browserPreferences: {
            collapse_thinking_by_default: true,
            collapse_process_meta_by_default: true,
            auto_collapse_output_meta: false,
            localized_save: true,
        },
        enableSystemPrompt: true,
    };
    const state = {
        sessionId: null,
        isStreaming: false,
        streamAbortController: null,
        stopStreamRequested: false,
        streamStopBlocked: false,
        isExpanded: false,
        attachments: [],
        selectedReferenceImages: {},
        settingsByModel: {},
        followStreaming: true,
        dragDepth: 0,
        recordsCache: [],
        recordsSearchQuery: "",
        currentTitle: "新对话",
        currentSavedBasename: "",
        theme: "orange",
        accent: "orange",
        activeTurnEpoch: "",
        turnNavigatorSignature: "",
        turnNavigatorFrame: 0,
        contextMessages: [],
        contextLimitTokens: 100000,
        totalConversationTokens: 0,
        latestAssistantThinking: "",
        contextTierWarningDismissed: false,
        openRecordActionMenuKey: "",
        pendingDeleteRecord: null,
        browserPreferences: {
            collapse_thinking_by_default: true,
            collapse_process_meta_by_default: true,
            auto_collapse_output_meta: false,
            localized_save: true,
        },
        enableSystemPrompt: true,
    };
    const refs = {
        conversation: document.getElementById("conversation"),
        emptyState: document.getElementById("empty-state"),
        title: document.getElementById("chat-title"),
        turnMap: document.getElementById("turn-map"),
        turnMapList: document.getElementById("turn-map-list"),
        scrollBottomButton: document.getElementById("scroll-bottom-button"),
        historyToggleButton: document.getElementById("history-toggle-button"),
        themeField: document.querySelector(".header-theme-field"),
        themeSelector: document.getElementById("theme-selector"),
        accentGroup: document.getElementById("accent-group"),
        accentSelector: document.getElementById("accent-selector"),
        input: document.getElementById("chat-input"),
        contextMeter: document.getElementById("context-meter"),
        contextMeterRing: document.getElementById("context-meter-ring"),
        contextMeterShell: document.querySelector(".context-meter-shell"),
        contextMeterValue: document.getElementById("context-meter-value"),
        contextMeterWindow: document.getElementById("context-meter-window"),
        contextMeterTotal: document.getElementById("context-meter-total"),
        contextMeterToolShare: document.getElementById("context-meter-tool-share"),
        contextMeterChatShare: document.getElementById("context-meter-chat-share"),
        contextTierWarning: document.getElementById("context-tier-warning"),
        contextTierWarningText: document.getElementById("context-tier-warning-text"),
        contextTierWarningClose: document.getElementById("context-tier-warning-close"),
        contextUsageDetailButton: document.getElementById("context-usage-detail-button"),
        contextMeterStatus: document.getElementById("context-meter-status"),
        usageDetailOverlay: document.getElementById("usage-detail-overlay"),
        usageDetailSummary: document.getElementById("usage-detail-summary"),
        usageDetailBody: document.getElementById("usage-detail-body"),
        usageDetailClose: document.getElementById("usage-detail-close"),
        sendButton: document.getElementById("send-button"),
        attachButton: document.getElementById("attach-button"),
        fileInput: document.getElementById("file-input"),
        attachmentStrip: document.getElementById("attachment-strip"),
        modelSlot: document.getElementById("model-slot"),
        modelButton: document.getElementById("model-button"),
        modelMenu: document.getElementById("model-menu"),
        thinkingSlot: document.getElementById("thinking-slot"),
        thinkingButton: document.getElementById("thinking-button"),
        thinkingMenu: document.getElementById("thinking-menu"),
        extraButton: document.getElementById("extra-button"),
        extraMenu: document.getElementById("extra-menu"),
        extraSlot: document.getElementById("extra-slot"),
        expandButton: document.getElementById("expand-button"),
        composerCard: document.getElementById("composer-card"),
        toggleMetaButton: document.getElementById("toggle-meta-button"),
        newChatButton: document.getElementById("new-chat-button"),
        saveChatButton: document.getElementById("save-chat-button"),
        recordsPanel: document.getElementById("records-panel"),
        confirmDialogOverlay: document.getElementById("confirm-dialog-overlay"),
        confirmDialogBody: document.getElementById("confirm-dialog-body"),
        confirmDialogCancel: document.getElementById("confirm-dialog-cancel"),
        confirmDialogConfirm: document.getElementById("confirm-dialog-confirm"),
        settingsButton: document.getElementById("settings-button"),
        settingsOverlay: document.getElementById("settings-overlay"),
        settingsSidebar: document.getElementById("settings-sidebar"),
        settingsThemeSlot: document.getElementById("settings-theme-slot"),
        settingsCloseButton: document.getElementById("settings-close-button"),
        systemPromptToggle: document.getElementById("system-prompt-toggle"),
        imageLightboxOverlay: document.getElementById("image-lightbox-overlay"),
        imageLightboxImage: document.getElementById("image-lightbox-image"),
        imageLightboxCaption: document.getElementById("image-lightbox-caption"),
        imageLightboxClose: document.getElementById("image-lightbox-close"),
        browserPreferenceInputs: Array.from(document.querySelectorAll("[data-preference-key]")),
    };
    const modelMap = new Map(bootstrap.models.map((item) => [item.id, item]));
    let composerResizeObserver = null;
    let composerExpansionAnimationTimer = 0;

    init().catch((error) => showToast("初始化失败：" + error.message, "error"));

    async function init() {
        mountSettingsFields();
        initializeTheme();
        initializeBrowserPreferences();
        initializeSystemPromptSetting();
        initializeModelState();
        bindEvents();
        installComposerLayoutObserver();
        await createSession();
        renderControls();
        updateSendButtonState();
        syncTextareaHeight({ animate: true });
        renderContextUsage();
        refreshTurnNavigator();
        syncScrollBottomButtonVisibility();
        await refreshRecordsPanel({ silent: true });
        updateToggleMetaButtonState();
    }

    function bindEvents() {
        refs.attachButton.addEventListener("click", () => refs.fileInput.click());
        refs.fileInput.addEventListener("change", onFilesSelected);
        refs.sendButton.addEventListener("click", () => {
            if (state.isStreaming) {
                stopStreaming();
                return;
            }
            void sendMessage();
        });
        refs.modelButton.addEventListener("click", (event) => {
            event.stopPropagation();
            toggleMenu("model");
        });
        refs.thinkingButton.addEventListener("click", (event) => {
            event.stopPropagation();
            toggleMenu("thinking");
        });
        refs.extraButton.addEventListener("click", (event) => {
            event.stopPropagation();
            toggleMenu("extra");
        });
        refs.modelMenu.addEventListener("click", onModelMenuClick);
        refs.thinkingMenu.addEventListener("click", onThinkingMenuClick);
        refs.extraMenu.addEventListener("click", onExtraMenuClick);
        refs.extraMenu.addEventListener("change", onExtraFieldChange);
        refs.expandButton.addEventListener("click", toggleExpanded);
        if (refs.toggleMetaButton) refs.toggleMetaButton.addEventListener("click", () => void toggleAllAssistantMetaDetails());
        refs.newChatButton.addEventListener("click", () => void resetConversation());
        refs.saveChatButton.addEventListener("click", () => void saveConversation());
        refs.historyToggleButton.addEventListener("click", (event) => {
            event.stopPropagation();
            void toggleRecordsPanel();
        });
        refs.settingsButton.addEventListener("click", (event) => {
            event.stopPropagation();
            toggleSettingsSidebar();
        });
        if (refs.confirmDialogCancel) refs.confirmDialogCancel.addEventListener("click", closeDeleteConfirmDialog);
        if (refs.confirmDialogConfirm) refs.confirmDialogConfirm.addEventListener("click", () => void confirmDeleteRecord());
        if (refs.confirmDialogOverlay) {
            refs.confirmDialogOverlay.addEventListener("click", (event) => {
                if (event.target.closest(".confirm-dialog")) return;
                closeDeleteConfirmDialog();
            });
        }
        if (refs.imageLightboxClose) refs.imageLightboxClose.addEventListener("click", closeImageLightbox);
        if (refs.imageLightboxOverlay) {
            refs.imageLightboxOverlay.addEventListener("click", (event) => {
                if (event.target.closest(".image-lightbox-dialog")) return;
                closeImageLightbox();
            });
        }
        refs.settingsCloseButton.addEventListener("click", () => closeSettingsSidebar());
        refs.settingsOverlay.addEventListener("click", (event) => {
            if (event.target.closest(".settings-sidebar")) return;
            closeSettingsSidebar();
        });
        if (refs.themeSelector) refs.themeSelector.addEventListener("click", onThemeOptionClick);
        if (refs.accentSelector) refs.accentSelector.addEventListener("click", onAccentOptionClick);
        refs.browserPreferenceInputs.forEach((input) => {
            input.addEventListener("change", onBrowserPreferenceInputChange);
        });
        if (refs.systemPromptToggle) {
            refs.systemPromptToggle.addEventListener("change", onSystemPromptToggleChange);
        }
        if (refs.contextUsageDetailButton) {
            refs.contextUsageDetailButton.addEventListener("click", (event) => {
                event.stopPropagation();
                void openUsageDetailDialog();
            });
        }
        if (refs.contextTierWarningClose) {
            refs.contextTierWarningClose.addEventListener("click", (event) => {
                event.stopPropagation();
                dismissContextTierWarning();
            });
        }
        if (refs.usageDetailClose) refs.usageDetailClose.addEventListener("click", closeUsageDetailDialog);
        if (refs.usageDetailOverlay) {
            refs.usageDetailOverlay.addEventListener("click", (event) => {
                if (event.target.closest(".usage-detail-dialog")) return;
                closeUsageDetailDialog();
            });
        }
        refs.input.addEventListener("input", () => {
            // Disable live height animation while typing to avoid a visible bounce on each keystroke.
            syncTextareaHeight({ animate: false });
            renderContextUsage();
        });
        refs.input.addEventListener("keydown", onInputKeyDown);
        refs.input.addEventListener("paste", onInputPaste);
        refs.composerCard.addEventListener("dragenter", onComposerDragEnter);
        refs.composerCard.addEventListener("dragover", onComposerDragOver);
        refs.composerCard.addEventListener("dragleave", onComposerDragLeave);
        refs.composerCard.addEventListener("drop", onComposerDrop);
        window.addEventListener("scroll", updateFollowStreamingState, { passive: true });
        window.addEventListener("scroll", scheduleTurnNavigatorSync, { passive: true });
        window.addEventListener("resize", onWindowResize);
        if (refs.turnMapList) refs.turnMapList.addEventListener("click", onTurnMapClick);
        if (refs.scrollBottomButton) refs.scrollBottomButton.addEventListener("click", onScrollBottomButtonClick);
        document.addEventListener("click", (event) => {
            if (!event.target.closest(".toolbar-dropdown")) closeAllMenus();
            if (!event.target.closest(".records-item-actions")) closeRecordActionMenu();
        });
        document.addEventListener("click", (event) => {
            const imageLink = event.target.closest(".image-card-link");
            if (!imageLink) return;
            event.preventDefault();
            openImageLightbox(
                imageLink.getAttribute("href") || imageLink.dataset.fullSrc || "",
                imageLink.querySelector("img")?.getAttribute("alt") || imageLink.dataset.caption || ""
            );
        });
        document.addEventListener("click", (event) => {
            const summary = event.target.closest("details.assistant-meta-box > summary");
            if (!summary) return;
            const detailsNode = summary.parentElement;
            if (!(detailsNode instanceof HTMLDetailsElement)) return;
            event.preventDefault();
            void setAssistantMetaDetailsOpen(detailsNode, !detailsNode.open, { animate: true });
        });
        document.addEventListener("keydown", (event) => {
            if (event.key !== "Escape") return;
            closeAllMenus();
            closeRecordsPanel();
            closeSettingsSidebar();
            closeUsageDetailDialog();
            closeDeleteConfirmDialog();
            closeRecordActionMenu();
            closeImageLightbox();
        });
    }

    function installComposerLayoutObserver() {
        syncComposerLayout();
        if (composerResizeObserver || typeof ResizeObserver !== "function" || !refs.composerCard) return;
        composerResizeObserver = new ResizeObserver(() => syncComposerLayout());
        composerResizeObserver.observe(refs.composerCard);
    }

    function syncComposerLayout() {
        if (!refs.composerCard) return;
        const composerRect = refs.composerCard.getBoundingClientRect();
        const composerHeight = Math.ceil(composerRect.height || refs.composerCard.offsetHeight || 0);
        if (!composerHeight) return;
        const gapValue = window.getComputedStyle(document.documentElement).getPropertyValue("--composer-gap");
        const composerGap = Number.parseFloat(gapValue) || 16;
        document.documentElement.style.setProperty("--composer-reserve", `${composerHeight + composerGap}px`);
        const composerWidth = Math.max(0, Math.round(composerRect.width || refs.composerCard.offsetWidth || 0));
        if (composerWidth) {
            const metaWidth = Math.max(320, composerWidth - 88);
            document.documentElement.style.setProperty("--assistant-meta-open-width", `${metaWidth}px`);
        }
        syncScrollBottomButtonLayout();
    }

    function onWindowResize() {
        syncComposerLayout();
        updateFollowStreamingState();
        scheduleTurnNavigatorSync();
        syncScrollBottomButtonVisibility();
        syncScrollBottomButtonLayout();
    }

    function setHistorySidebarOpen(isOpen) {
        document.body.classList.toggle("records-open", !!isOpen);
        refs.recordsPanel.setAttribute("aria-hidden", isOpen ? "false" : "true");
        refs.historyToggleButton.setAttribute("aria-expanded", isOpen ? "true" : "false");
        window.requestAnimationFrame(syncComposerLayout);
        window.setTimeout(syncComposerLayout, 260);
    }

    function setConversationTitle(nextTitle, options = {}) {
        const resolvedTitle = String(nextTitle || "").trim() || "新对话";
        state.currentTitle = resolvedTitle;
        refs.title.textContent = resolvedTitle;
        document.title = resolvedTitle;
        if (options.refreshRecords !== false) renderRecordsPanel();
    }

    function setCurrentSavedBasename(nextBasename, options = {}) {
        state.currentSavedBasename = String(nextBasename || "").trim();
        if (options.refreshRecords !== false) renderRecordsPanel();
    }

    function getCurrentConversationSidebarTitle() {
        if (state.currentSavedBasename) return state.currentSavedBasename;
        return state.currentTitle || "新对话";
    }

    function coerceTokenValue(value) {
        const numericValue = Number(value);
        if (!Number.isFinite(numericValue) || numericValue < 0) return 0;
        return numericValue;
    }

    function estimateTextTokens(text) {
        let total = 0;
        for (const char of String(text || "")) {
            total += char.charCodeAt(0) <= 127 ? 0.3 : 0.6;
        }
        return total;
    }

    function formatContextTokenLabel(value) {
        return `${(coerceTokenValue(value) / 1000).toFixed(1)}k`;
    }

    function normalizeContextMessages(messages) {
        if (!Array.isArray(messages)) return [];
        return messages.reduce((result, item) => {
            const role = String(item?.role || "").trim();
            const sourceRole = String(item?.source_role || item?.sourceRole || role).trim();
            if (role === "tool" || sourceRole === "tool") {
                result.push({
                    role: "assistant",
                    content: String(item?.content || ""),
                    sourceRole: "tool",
                });
                return result;
            }
            if (!["system", "assistant", "user"].includes(role)) return result;
            result.push({
                role,
                content: String(item?.content || ""),
                sourceRole,
            });
            return result;
        }, []);
    }

    function cloneContextMessages(messages = state.contextMessages) {
        return normalizeContextMessages(messages);
    }

    function estimateContextMessagesTokens(messages) {
        return cloneContextMessages(messages).reduce((total, message) => (
            total + estimateTextTokens(message.content || "")
        ), 0);
    }

    function estimateContextUsageBreakdown(messages = state.contextMessages, pendingInput = refs.input?.value || "") {
        const inputTokens = estimateTextTokens(pendingInput);
        return cloneContextMessages(messages).reduce((totals, message) => {
            const messageTokens = estimateTextTokens(message.content || "");
            const sourceRole = String(message.sourceRole || message.role || "").trim();
            if (sourceRole === "tool") {
                totals.toolTokens += messageTokens;
            } else {
                totals.chatTokens += messageTokens;
            }
            totals.totalTokens += messageTokens;
            return totals;
        }, {
            toolTokens: 0,
            chatTokens: inputTokens,
            totalTokens: inputTokens,
        });
    }

    function getCurrentEstimatedContextTokens() {
        return estimateContextUsageBreakdown(state.contextMessages, refs.input?.value || "").totalTokens;
    }

    function setContextMessages(messages) {
        state.contextMessages = cloneContextMessages(messages);
        renderContextUsage();
        syncSystemPromptToggle();
    }

    function setTotalConversationTokens(value) {
        state.totalConversationTokens = Math.ceil(coerceTokenValue(value));
        renderContextUsage();
    }

    function setLatestAssistantThinking(value) {
        state.latestAssistantThinking = String(value || "").trim();
        renderContextUsage();
    }

    function formatTokenDetailedLabel(value) {
        const numericValue = Math.ceil(coerceTokenValue(value));
        const compactKLabel = `${(numericValue / 1000).toFixed(1)}k`;
        const millionRoundedTo1k = Math.round(numericValue / 1000) / 1000;
        if (millionRoundedTo1k <= 0) {
            return `${compactKLabel} (${numericValue})`;
        }

        const millionLabel = `${millionRoundedTo1k.toFixed(3)}M`;
        const tooltipLabel = `详细值：${numericValue}`;
        return `${compactKLabel} (<span class="usage-token-meta" tabindex="0"><span class="usage-token-meta-value">${millionLabel}</span><span class="usage-token-meta-tooltip">${tooltipLabel}</span></span>)`;
    }

    function formatUsageShareLabel(value, total) {
        const denominator = coerceTokenValue(total);
        if (denominator <= 0) return "0.0%";
        return `${((coerceTokenValue(value) / denominator) * 100).toFixed(1)}%`;
    }

    function dismissContextTierWarning() {
        state.contextTierWarningDismissed = true;
        updateContextTierWarningVisibility(getCurrentEstimatedContextTokens());
    }

    function updateContextTierWarningVisibility(totalTokens) {
        if (!refs.contextTierWarning || !refs.contextMeterShell) return;
        const shouldWarn = coerceTokenValue(totalTokens) > CONTEXT_TIER_WARNING_THRESHOLD;
        if (!shouldWarn) state.contextTierWarningDismissed = false;
        const isVisible = shouldWarn && !state.contextTierWarningDismissed;
        refs.contextTierWarning.hidden = !isVisible;
        refs.contextTierWarning.setAttribute("aria-hidden", isVisible ? "false" : "true");
        refs.contextMeterShell.classList.toggle("has-tier-warning-visible", isVisible);
    }

    function renderContextUsage() {
        if (!refs.contextMeter || !refs.contextMeterValue || !refs.contextMeterStatus) return;
        const usageBreakdown = estimateContextUsageBreakdown(state.contextMessages, refs.input?.value || "");
        const totalTokens = usageBreakdown.totalTokens;
        const progress = Math.max(0, Math.min(1, totalTokens / state.contextLimitTokens));
        const isOverLimit = totalTokens > state.contextLimitTokens;
        const isTierWarning = totalTokens > CONTEXT_TIER_WARNING_THRESHOLD;
        const totalConversationTokens = coerceTokenValue(state.totalConversationTokens);
        const contextLabel = `${formatContextTokenLabel(totalTokens)} / ${formatContextTokenLabel(state.contextLimitTokens)}`;
        const totalConversationLabel = formatContextTokenLabel(totalConversationTokens);
        const toolShareLabel = formatUsageShareLabel(usageBreakdown.toolTokens, totalTokens);
        const chatShareLabel = formatUsageShareLabel(usageBreakdown.chatTokens, totalTokens);
        refs.contextMeter.style.setProperty("--context-progress", `${progress}`);
        refs.contextMeter.classList.toggle("is-tier-warning", isTierWarning);
        refs.contextMeter.classList.toggle("is-over-limit", isOverLimit);
        refs.contextMeterValue.textContent = contextLabel;
        if (refs.contextMeterWindow) refs.contextMeterWindow.textContent = `上下文窗口：${contextLabel}`;
        if (refs.contextMeterTotal) refs.contextMeterTotal.textContent = `总对话 Token：${totalConversationLabel}`;
        if (refs.contextMeterToolShare) refs.contextMeterToolShare.textContent = `工具占用：${toolShareLabel}`;
        if (refs.contextMeterChatShare) refs.contextMeterChatShare.textContent = `聊天占用：${chatShareLabel}`;
        if (refs.contextTierWarningText) refs.contextTierWarningText.textContent = `当前上下文窗口已达到 ${formatContextTokenLabel(totalTokens)}，超过 32k 后，部分模型可能进入更高档位收费。`;
        refs.contextMeterStatus.hidden = !isOverLimit;
        refs.contextMeterStatus.textContent = `已超过 ${formatContextTokenLabel(state.contextLimitTokens)}`;
        updateContextTierWarningVisibility(totalTokens);
        refs.contextMeter.setAttribute("aria-label", `上下文窗口用量估算 ${formatContextTokenLabel(totalTokens)} / ${formatContextTokenLabel(state.contextLimitTokens)}${isTierWarning ? "，已达到 32k 阶梯提醒" : ""}${isOverLimit ? "，已超过上限" : ""}`);
    }

    async function openUsageDetailDialog() {
        if (!refs.usageDetailOverlay || !refs.usageDetailBody || !refs.usageDetailSummary) return;
        if (!state.sessionId) return;

        refs.usageDetailOverlay.hidden = false;
        refs.usageDetailOverlay.setAttribute("aria-hidden", "false");
        refs.usageDetailSummary.textContent = "等待流结束后进行计算...";
        refs.usageDetailBody.innerHTML = '<div class="usage-detail-empty">等待中...</div>';

        try {
            const response = await fetch("/api/session/token-usage", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: state.sessionId }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "读取统计失败");
            renderUsageDetailPayload(payload);
        } catch (error) {
            refs.usageDetailSummary.textContent = "读取失败";
            refs.usageDetailBody.innerHTML = `<div class="usage-detail-empty">${escapeHtml(error.message || "读取统计失败")}</div>`;
        }
    }

    function closeUsageDetailDialog() {
        if (!refs.usageDetailOverlay) return;
        refs.usageDetailOverlay.hidden = true;
        refs.usageDetailOverlay.setAttribute("aria-hidden", "true");
    }

    function renderUsageDetailPayload(payload) {
        if (!refs.usageDetailBody || !refs.usageDetailSummary) return;
        const modelStats = Array.isArray(payload?.model_stats) ? payload.model_stats : [];
        const totalInput = coerceTokenValue(payload?.total_input_tokens);
        const totalOutput = coerceTokenValue(payload?.total_output_tokens);
        const totalTokens = coerceTokenValue(payload?.total_tokens);
        refs.usageDetailSummary.innerHTML = `总输入 ${formatTokenDetailedLabel(totalInput)} · 总输出 ${formatTokenDetailedLabel(totalOutput)} · 总计 ${formatTokenDetailedLabel(totalTokens)}`;

        if (!modelStats.length) {
            refs.usageDetailBody.innerHTML = '<div class="usage-detail-empty">当前会话暂无可统计的模型输出。</div>';
            return;
        }

        const rows = modelStats.map((item) => {
            const modelName = String(item?.model || "unknown");
            const inputTokens = coerceTokenValue(item?.input_tokens);
            const outputTokens = coerceTokenValue(item?.output_tokens);
            const combinedTokens = inputTokens + outputTokens;
            return `<tr><td>${escapeHtml(modelName)}</td><td>${formatTokenDetailedLabel(inputTokens)}</td><td>${formatTokenDetailedLabel(outputTokens)}</td><td>${formatTokenDetailedLabel(combinedTokens)}</td></tr>`;
        }).join("");

        refs.usageDetailBody.innerHTML = `
            <table class="usage-detail-table">
                <thead>
                    <tr>
                        <th>模型</th>
                        <th>输入 Token</th>
                        <th>输出 Token</th>
                        <th>总计</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    function closeRecordActionMenu() {
        if (!state.openRecordActionMenuKey) return;
        state.openRecordActionMenuKey = "";
        renderRecordsPanel();
    }

    function toggleRecordActionMenu(menuKey) {
        const normalizedKey = String(menuKey || "").trim();
        if (!normalizedKey) return;
        state.openRecordActionMenuKey = state.openRecordActionMenuKey === normalizedKey ? "" : normalizedKey;
        renderRecordsPanel();
    }

    function openDeleteConfirmDialog(record) {
        if (!refs.confirmDialogOverlay || !refs.confirmDialogBody) return;
        state.pendingDeleteRecord = record;
        refs.confirmDialogBody.textContent = `即将删除“${record.title || record.basename || "该记录"}”的所有记录文件。删除后无法恢复。`;
        refs.confirmDialogOverlay.hidden = false;
        refs.confirmDialogOverlay.setAttribute("aria-hidden", "false");
        if (refs.confirmDialogConfirm) refs.confirmDialogConfirm.focus();
    }

    function closeDeleteConfirmDialog() {
        if (!refs.confirmDialogOverlay) return;
        refs.confirmDialogOverlay.hidden = true;
        refs.confirmDialogOverlay.setAttribute("aria-hidden", "true");
        if (refs.confirmDialogConfirm) refs.confirmDialogConfirm.disabled = false;
        state.pendingDeleteRecord = null;
    }

    function initializeModelState() {
        refs.modelButton.dataset.value = bootstrap.defaultModel;
    }

    function mountSettingsFields() {
        if (!refs.themeField || !refs.settingsThemeSlot) return;
        refs.settingsThemeSlot.appendChild(refs.themeField);
    }

    function initializeTheme() {
        const themeMeta = bootstrap.theme || {};
        const themeOptions = Array.isArray(themeMeta.options) && themeMeta.options.length
            ? themeMeta.options
            : [{ id: "orange", label: "橙色", swatch: "#d97757" }];
        const accentOptions = Array.isArray(themeMeta.accentOptions) && themeMeta.accentOptions.length
            ? themeMeta.accentOptions
            : [{ id: "orange", label: "橙色", swatch: "#d97757", start: "#e28f6d", end: "#d97757" }];
        const fallbackTheme = String(themeOptions[0]?.id || "orange");
        const requestedTheme = String(themeMeta.value || fallbackTheme || "orange");
        state.theme = themeOptions.some((item) => String(item.id || "") === requestedTheme) ? requestedTheme : fallbackTheme;
        state.accent = resolveAccentValue(state.theme, themeMeta.accentValue, accentOptions);
        applyThemeDatasets();
        renderThemePickers(themeOptions, accentOptions);
    }

    function resolveAccentValue(themeValue, rawAccent, accentOptions) {
        const normalizedAccent = String(rawAccent || "").trim().toLowerCase();
        if (accentOptions.some((item) => String(item.id || "") === normalizedAccent)) return normalizedAccent;
        if (themeValue === "black") return "blue";
        return accentOptions.some((item) => String(item.id || "") === themeValue) ? themeValue : "orange";
    }

    function applyThemeDatasets() {
        document.documentElement.dataset.theme = state.theme;
        document.documentElement.dataset.accent = state.accent;
        if (refs.accentGroup) refs.accentGroup.hidden = state.theme !== "black";
    }

    function renderThemePickers(themeOptions, accentOptions) {
        if (refs.themeSelector) {
            refs.themeSelector.innerHTML = themeOptions.map((item) => {
                const id = String(item.id || "");
                const label = String(item.label || id || "theme");
                const selectedClass = id === state.theme ? " is-selected" : "";
                const swatch = String(item.swatch || "");
                const style = swatch ? ` style="--theme-swatch:${escapeAttr(swatch)}"` : "";
                return `<button class="theme-option${selectedClass}" type="button" data-theme-id="${escapeAttr(id)}"${style}><span class="theme-option-swatch" aria-hidden="true"></span><span class="theme-option-label">${escapeHtml(label)}</span></button>`;
            }).join("");
        }
        if (refs.accentSelector) {
            refs.accentSelector.innerHTML = accentOptions.map((item) => {
                const id = String(item.id || "");
                const label = String(item.label || id || "accent");
                const selectedClass = id === state.accent ? " is-selected" : "";
                const style = ` style="--accent-option-swatch:${escapeAttr(String(item.swatch || ""))};--accent-option-start:${escapeAttr(String(item.start || item.swatch || ""))};--accent-option-end:${escapeAttr(String(item.end || item.swatch || ""))}"`;
                return `<button class="accent-option${selectedClass}" type="button" data-accent-id="${escapeAttr(id)}"${style}><span class="accent-option-swatch" aria-hidden="true"></span><span class="accent-option-label">${escapeHtml(label)}</span></button>`;
            }).join("");
        }
    }

    function initializeBrowserPreferences() {
        const prefMeta = bootstrap.browserPreferences || {};
        state.browserPreferences = {
            collapse_thinking_by_default: prefMeta.collapse_thinking_by_default !== false,
            collapse_process_meta_by_default: prefMeta.collapse_process_meta_by_default !== false,
            auto_collapse_output_meta: !!prefMeta.auto_collapse_output_meta,
            localized_save: prefMeta.localized_save !== false,
        };
        refs.browserPreferenceInputs.forEach((input) => {
            const key = input.dataset.preferenceKey;
            if (!key) return;
            input.checked = !!state.browserPreferences[key];
        });
    }

    function initializeSystemPromptSetting() {
        state.enableSystemPrompt = bootstrap.enableSystemPrompt !== false;
        syncSystemPromptToggle();
    }

    function syncSystemPromptToggle() {
        if (!refs.systemPromptToggle) return;
        refs.systemPromptToggle.checked = !!state.enableSystemPrompt;
        refs.systemPromptToggle.disabled = !canChangeSystemPromptForCurrentSession();
    }

    function canChangeSystemPromptForCurrentSession() {
        return !state.isStreaming && state.contextMessages.every((message) => {
            const role = String(message?.role || "");
            return role !== "user" && role !== "assistant";
        });
    }

    function toggleSettingsSidebar() {
        if (refs.settingsOverlay.classList.contains("is-open")) {
            closeSettingsSidebar();
            return;
        }
        openSettingsSidebar();
    }

    function openSettingsSidebar() {
        closeAllMenus();
        closeRecordsPanel();
        refs.settingsOverlay.removeAttribute("inert");
        refs.settingsOverlay.classList.add("is-open");
        refs.settingsOverlay.setAttribute("aria-hidden", "false");
        refs.settingsButton.setAttribute("aria-expanded", "true");
        document.body.classList.add("settings-open");
        refs.settingsSidebar.querySelector(".theme-option.is-selected, .accent-option.is-selected, .settings-close-button")?.focus({ preventScroll: true });
    }

    function closeSettingsSidebar() {
        if (!refs.settingsOverlay.classList.contains("is-open")) return;
        refs.settingsOverlay.classList.remove("is-open");
        refs.settingsOverlay.setAttribute("aria-hidden", "true");
        refs.settingsOverlay.setAttribute("inert", "");
        refs.settingsButton.setAttribute("aria-expanded", "false");
        document.body.classList.remove("settings-open");
        refs.settingsButton.focus({ preventScroll: true });
    }

    async function onThemeOptionClick(event) {
        const selectedTheme = String(event.target?.closest("[data-theme-id]")?.dataset?.themeId || "").trim().toLowerCase();
        if (!selectedTheme) return;
        const previousTheme = state.theme;
        const previousAccent = state.accent;
        state.theme = selectedTheme;
        state.accent = resolveAccentValue(state.theme, state.accent, bootstrap.theme?.accentOptions || []);
        applyThemeDatasets();
        renderThemePickers(bootstrap.theme?.options || [], bootstrap.theme?.accentOptions || []);
        try {
            await persistThemeAppearance({ theme: selectedTheme, accent: state.accent });
            showToast("主题色已更新", "success");
        } catch (error) {
            state.theme = previousTheme;
            state.accent = previousAccent;
            applyThemeDatasets();
            renderThemePickers(bootstrap.theme?.options || [], bootstrap.theme?.accentOptions || []);
            showToast(error.message || "主题保存失败", "error");
        }
    }

    async function onAccentOptionClick(event) {
        const selectedAccent = String(event.target?.closest("[data-accent-id]")?.dataset?.accentId || "").trim().toLowerCase();
        if (!selectedAccent || selectedAccent === state.accent) return;
        const previousAccent = state.accent;
        state.accent = selectedAccent;
        applyThemeDatasets();
        renderThemePickers(bootstrap.theme?.options || [], bootstrap.theme?.accentOptions || []);
        try {
            await persistThemeAppearance({ theme: state.theme, accent: state.accent });
            showToast("高亮色已更新", "success");
        } catch (error) {
            state.accent = previousAccent;
            applyThemeDatasets();
            renderThemePickers(bootstrap.theme?.options || [], bootstrap.theme?.accentOptions || []);
            showToast(error.message || "高亮色保存失败", "error");
        }
    }

    async function persistThemeAppearance(nextAppearance) {
        const response = await fetch("/api/settings/theme", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(nextAppearance),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "主题保存失败");
        if (payload.theme) state.theme = String(payload.theme || state.theme);
        if (payload.accent) state.accent = String(payload.accent || state.accent);
        applyThemeDatasets();
        renderThemePickers(bootstrap.theme?.options || [], bootstrap.theme?.accentOptions || []);
    }

    async function onBrowserPreferenceInputChange(event) {
        const key = String(event.target?.dataset?.preferenceKey || "").trim();
        if (!key) return;
        const previousValue = !!state.browserPreferences[key];
        const nextValue = !!event.target.checked;
        state.browserPreferences[key] = nextValue;

        if (key === "collapse_thinking_by_default" || key === "collapse_process_meta_by_default") {
            applyOutputPreferenceState(refs.conversation, { animate: true });
        }

        try {
            const response = await fetch("/api/settings/browser", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ [key]: nextValue }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "设置保存失败");
            if (payload.preferences && typeof payload.preferences === "object") {
                state.browserPreferences = { ...state.browserPreferences, ...payload.preferences };
            }
        } catch (error) {
            state.browserPreferences[key] = previousValue;
            event.target.checked = previousValue;
            if (key === "collapse_thinking_by_default" || key === "collapse_process_meta_by_default") {
                applyOutputPreferenceState(refs.conversation, { animate: true });
            }
            showToast(error.message || "设置保存失败", "error");
        }
    }

    async function onSystemPromptToggleChange(event) {
        if (!refs.systemPromptToggle) return;
        if (!canChangeSystemPromptForCurrentSession()) {
            event.target.checked = !!state.enableSystemPrompt;
            syncSystemPromptToggle();
            showToast("系统提示词只能在发送第一条消息前调整", "info");
            return;
        }

        const previousValue = !!state.enableSystemPrompt;
        const nextValue = !!event.target.checked;
        state.enableSystemPrompt = nextValue;
        syncSystemPromptToggle();

        if (!state.sessionId) return;
        try {
            const response = await fetch("/api/session/system-prompt", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    enable_system_prompt: nextValue,
                }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "系统提示词设置失败");
            state.enableSystemPrompt = payload.enable_system_prompt !== false;
            if (Array.isArray(payload.context_messages)) {
                setContextMessages(payload.context_messages);
            }
            if (typeof payload.total_tokens === "number") {
                setTotalConversationTokens(payload.total_tokens);
            }
            renderContextUsage();
        } catch (error) {
            state.enableSystemPrompt = previousValue;
            syncSystemPromptToggle();
            showToast(error.message || "系统提示词设置失败", "error");
        }
    }

    function applyOutputPreferenceState(root, options = {}) {
        if (!root) return;
        const forceCollapse = !!options.forceCollapse;
        const animate = !!options.animate;
        root.querySelectorAll("details.assistant-thinking-box").forEach((node) => {
            void setAssistantMetaDetailsOpen(node, !forceCollapse && !state.browserPreferences.collapse_thinking_by_default, { animate });
        });
        root.querySelectorAll("details.assistant-process-box").forEach((node) => {
            void setAssistantMetaDetailsOpen(node, !forceCollapse && !state.browserPreferences.collapse_process_meta_by_default, { animate });
        });
        updateToggleMetaButtonState();
    }

    function getAssistantMetaDetails(root = refs.conversation) {
        if (!root) return [];
        return Array.from(root.querySelectorAll("details.assistant-thinking-box, details.assistant-process-box"));
    }

    function updateToggleMetaButtonState() {
        if (!refs.toggleMetaButton) return;
        const detailNodes = getAssistantMetaDetails();
        if (!detailNodes.length) {
            refs.toggleMetaButton.disabled = true;
            refs.toggleMetaButton.textContent = "全部展开";
            refs.toggleMetaButton.setAttribute("aria-pressed", "false");
            return;
        }
        refs.toggleMetaButton.disabled = false;
        const isAllOpen = detailNodes.every((node) => node.open);
        refs.toggleMetaButton.textContent = isAllOpen ? "全部折叠" : "全部展开";
        refs.toggleMetaButton.setAttribute("aria-pressed", isAllOpen ? "true" : "false");
    }

    function setAssistantMetaDetailsOpen(detailsNode, shouldOpen, options = {}) {
        if (!(detailsNode instanceof HTMLDetailsElement)) return Promise.resolve();
        const targetOpen = !!shouldOpen;
        const animate = !!options.animate;
        const content = detailsNode.querySelector(".meta-content");
        const summary = detailsNode.querySelector("summary");
        if (!content || !summary || !animate) {
            detailsNode.open = targetOpen;
            updateToggleMetaButtonState();
            return Promise.resolve();
        }
        if (detailsNode.dataset.animating === "1" || detailsNode.open === targetOpen) {
            updateToggleMetaButtonState();
            return Promise.resolve();
        }

        const durationMs = 220;
        const opacityDurationMs = 180;
        const easing = "cubic-bezier(0.22, 1, 0.36, 1)";

        const measureCollapsedWidth = () => {
            if (!detailsNode.open) {
                return Math.max(1, Math.ceil(detailsNode.getBoundingClientRect().width));
            }
            detailsNode.open = false;
            const width = Math.max(1, Math.ceil(detailsNode.getBoundingClientRect().width));
            detailsNode.open = true;
            return width;
        };

        const measureExpandedWidth = () => {
            if (detailsNode.open) {
                return Math.max(1, Math.ceil(detailsNode.getBoundingClientRect().width));
            }
            detailsNode.open = true;
            const width = Math.max(1, Math.ceil(detailsNode.getBoundingClientRect().width));
            detailsNode.open = false;
            return width;
        };

        const collapsedWidth = measureCollapsedWidth();
        const expandedWidth = Math.max(collapsedWidth, measureExpandedWidth());

        if (targetOpen) detailsNode.open = true;
        const contentHeight = Math.max(0, Math.ceil(content.scrollHeight));
        const computedStyle = window.getComputedStyle(content);
        const paddingTop = Math.max(0, Number.parseFloat(computedStyle.paddingTop) || 0);
        const paddingBottom = Math.max(0, Number.parseFloat(computedStyle.paddingBottom) || 0);
        const fromHeight = targetOpen ? 0 : contentHeight;
        const toHeight = targetOpen ? contentHeight : 0;
        const fromPaddingTop = targetOpen ? 0 : paddingTop;
        const toPaddingTop = targetOpen ? paddingTop : 0;
        const fromPaddingBottom = targetOpen ? 0 : paddingBottom;
        const toPaddingBottom = targetOpen ? paddingBottom : 0;
        if (!targetOpen) detailsNode.open = true;

        const fromWidth = targetOpen ? collapsedWidth : expandedWidth;
        const toWidth = targetOpen ? expandedWidth : collapsedWidth;

        detailsNode.dataset.animating = "1";
        detailsNode.style.overflow = "hidden";
        detailsNode.style.transition = "none";
        detailsNode.style.width = `${fromWidth}px`;
        summary.style.borderBottomWidth = targetOpen ? "" : "0px";

        content.style.overflow = "hidden";
        content.style.willChange = "max-height, opacity, transform, padding-top, padding-bottom";
        content.style.transition = "none";
        content.style.maxHeight = `${fromHeight}px`;
        content.style.paddingTop = `${fromPaddingTop}px`;
        content.style.paddingBottom = `${fromPaddingBottom}px`;
        content.style.opacity = targetOpen ? "0" : "1";
        content.style.transform = targetOpen ? "translateY(-4px)" : "translateY(0)";

        // Commit the start state so next-frame target values can animate reliably.
        void detailsNode.offsetHeight;

        const cleanup = () => {
            delete detailsNode.dataset.animating;
            detailsNode.style.removeProperty("overflow");
            detailsNode.style.removeProperty("transition");
            detailsNode.style.removeProperty("width");
            content.style.removeProperty("overflow");
            content.style.removeProperty("will-change");
            content.style.removeProperty("transition");
            content.style.removeProperty("max-height");
            content.style.removeProperty("padding-top");
            content.style.removeProperty("padding-bottom");
            content.style.removeProperty("opacity");
            content.style.removeProperty("transform");
            summary.style.removeProperty("border-bottom-width");
            updateToggleMetaButtonState();
        };

        return new Promise((resolve) => {
            let resolved = false;
            let timeoutId = 0;

            const finish = () => {
                if (resolved) return;
                resolved = true;
                content.removeEventListener("transitionend", onEnd);
                if (timeoutId) window.clearTimeout(timeoutId);
                detailsNode.open = targetOpen;
                cleanup();
                resolve();
            };

            const onEnd = (event) => {
                if (event.target !== content || event.propertyName !== "max-height") return;
                finish();
            };

            content.addEventListener("transitionend", onEnd);

            requestAnimationFrame(() => {
                detailsNode.style.transition = `width ${durationMs}ms ${easing}`;
                content.style.transition = `max-height ${durationMs}ms ${easing}, padding-top ${durationMs}ms ${easing}, padding-bottom ${durationMs}ms ${easing}, opacity ${opacityDurationMs}ms ease, transform ${opacityDurationMs}ms ease`;
                detailsNode.style.width = `${toWidth}px`;
                content.style.maxHeight = `${toHeight}px`;
                content.style.paddingTop = `${toPaddingTop}px`;
                content.style.paddingBottom = `${toPaddingBottom}px`;
                content.style.opacity = targetOpen ? "1" : "0";
                content.style.transform = targetOpen ? "translateY(0)" : "translateY(-4px)";
            });

            timeoutId = window.setTimeout(() => {
                if (detailsNode.dataset.animating === "1") {
                    finish();
                }
            }, durationMs + 140);
        });
    }

    async function toggleAllAssistantMetaDetails() {
        const detailNodes = getAssistantMetaDetails();
        if (!detailNodes.length) {
            updateToggleMetaButtonState();
            return;
        }
        const shouldOpen = !detailNodes.every((node) => node.open);
        await Promise.all(detailNodes.map((node) => setAssistantMetaDetailsOpen(node, shouldOpen, { animate: true })));
        updateToggleMetaButtonState();
    }

    async function createSession() {
        const response = await fetch("/api/session/new", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enable_system_prompt: !!state.enableSystemPrompt }),
        });
        if (!response.ok) throw new Error("无法创建浏览器会话");
        const payload = await response.json();
        state.sessionId = payload.session_id;
        state.enableSystemPrompt = payload.enable_system_prompt !== false;
        syncSystemPromptToggle();
        setContextMessages(payload.context_messages || []);
        setTotalConversationTokens(payload.total_tokens || 0);
        setLatestAssistantThinking(payload.latest_assistant_thinking || "");
        refreshTurnNavigator();
        refs.title.textContent = payload.title || "新对话";
        document.title = refs.title.textContent;
    }

    async function resetConversation() {
        if (state.isStreaming) return;
        refs.conversation.innerHTML = "";
        refreshTurnNavigator();
        refs.title.textContent = "新对话";
        document.title = "新对话";
        state.followStreaming = true;
        clearSelectedReferenceImages();
        clearPendingAttachments();
        refs.input.value = "";
        syncTextareaHeight();
        await createSession();
    }

    async function saveConversation() {
        if (!state.sessionId) return;
        const response = await fetch("/api/session/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: state.sessionId }),
        });
        const payload = await response.json();
        if (!response.ok) {
            showToast(payload.error || "保存失败", "error");
            return;
        }
        showToast("已保存到：" + payload.saved_path, "success");
    }

    async function toggleRecordsPanel() {
        const isOpen = refs.recordsPanel.dataset.open === "true";
        closeRecordsPanel();
        if (isOpen) return;

        refs.recordsPanel.dataset.open = "true";
        refs.recordsPanel.hidden = false;
        refs.recordsPanel.innerHTML = '<div class="records-empty">正在读取记录...</div>';

        try {
            const response = await fetch("/api/records");
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "读取记录失败");
            renderRecordsPanel(Array.isArray(payload.records) ? payload.records : []);
        } catch (error) {
            refs.recordsPanel.innerHTML = '<div class="records-empty">读取记录失败，请稍后再试。</div>';
            showToast(error.message || "读取记录失败", "error");
        }
    }

    function closeRecordsPanel() {
        delete refs.recordsPanel.dataset.open;
        refs.recordsPanel.hidden = true;
    }

    async function loadRecord(filename) {
        if (state.isStreaming) return;
        if (!state.sessionId) return;
        const targetFilename = String(filename || "").trim();
        if (!targetFilename) return;

        try {
            const response = await fetch("/api/session/load", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: state.sessionId, filename: targetFilename }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "导入记录失败");

            clearSelectedReferenceImages();
            refs.conversation.innerHTML = payload.conversation_html || "";
            renderMathInContent(refs.conversation);
            hydrateAssistantReferenceImages(refs.conversation);
            applyOutputPreferenceState(refs.conversation);
            refs.title.textContent = payload.title || "新对话";
            document.title = refs.title.textContent;
            state.followStreaming = true;
            if (payload.selected_model && modelMap.has(payload.selected_model)) {
                refs.modelButton.dataset.value = payload.selected_model;
                renderControls();
            }
            setContextMessages(payload.context_messages || []);
            setTotalConversationTokens(payload.total_tokens || 0);
            setLatestAssistantThinking(payload.latest_assistant_thinking || "");
            if (typeof payload.saved_basename === "string") {
                setCurrentSavedBasename(payload.saved_basename, { refreshRecords: false });
            }
            annotateTurnEpochs();
            enhanceConversationActions();
            closeRecordsPanel();
            window.scrollTo({ top: 0, behavior: "smooth" });
            showToast("已导入记录：" + (payload.loaded_filename || targetFilename), "success");
        } catch (error) {
            showToast(error.message || "导入记录失败", "error");
        }
    }

    async function forkConversationAtTurn(turnEl, prefillText) {
        if (state.isStreaming) return;
        if (!state.sessionId) return;
        const epoch = Number(turnEl?.dataset?.turnEpoch || 0);
        if (!epoch) {
            showToast("无法识别该轮次，暂时不能 fork", "error");
            return;
        }
        if (epoch <= 1) {
            showToast("第一轮之前没有可 fork 的历史", "error");
            return;
        }

        const forkEpoch = epoch - 1;
        try {
            const response = await fetch("/api/session/fork", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: state.sessionId, fork_epoch: forkEpoch }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "fork 失败");

            refs.conversation.innerHTML = payload.conversation_html || "";
            renderMathInContent(refs.conversation);
            refs.title.textContent = payload.title || refs.title.textContent || "新对话";
            document.title = refs.title.textContent;
            state.followStreaming = true;
            if (payload.selected_model && modelMap.has(payload.selected_model)) {
                refs.modelButton.dataset.value = payload.selected_model;
                renderControls();
            }
            setContextMessages(payload.context_messages || []);
            setTotalConversationTokens(payload.total_tokens || 0);
            setLatestAssistantThinking(payload.latest_assistant_thinking || "");
            if (typeof payload.saved_basename === "string") {
                setCurrentSavedBasename(payload.saved_basename, { refreshRecords: false });
            }
            annotateTurnEpochs();
            enhanceConversationActions();
            applyOutputPreferenceState(refs.conversation);

            refs.input.value = prefillText || "";
            syncTextareaHeight();
            renderContextUsage();
            focusComposerInput();
            showToast(`已 fork 到第 ${forkEpoch} 轮，并回填用户消息`, "success");
            window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" });
        } catch (error) {
            showToast(error.message || "fork 失败", "error");
        }
    }

    function annotateTurnEpochs() {
        refs.conversation.querySelectorAll(".turn").forEach((turn, index) => {
            const existingEpoch = Number(turn.dataset.turnEpoch || 0);
            if (existingEpoch > 0) return;
            const indexLabel = turn.querySelector(".turn-index");
            const labelText = (indexLabel?.textContent || "").trim();
            const matched = labelText.match(/(\d+)/);
            if (matched) {
                turn.dataset.turnEpoch = matched[1];
                return;
            }
            turn.dataset.turnEpoch = String(index + 1);
        });
    }

    function extractNodeText(node) {
        return String(node?.textContent || "").replace(/\u00a0/g, " ").trim();
    }

    function getTurnUserText(turnEl) {
        if (turnEl?.dataset?.userRaw) return turnEl.dataset.userRaw;
        return extractNodeText(turnEl?.querySelector(".user-row .user-bubble .message-content"));
    }

    function getTurnAssistantText(turnEl) {
        if (turnEl?.dataset?.assistantRaw) return turnEl.dataset.assistantRaw;
        return extractNodeText(turnEl?.querySelector(".assistant-answer .message-content"));
    }

    function getTurnNavigatorPreview(turnEl) {
        const normalizedText = String(getTurnUserText(turnEl) || "").replace(/\s+/g, " ").trim();
        if (normalizedText) return truncateTurnNavigatorText(normalizedText, 10);
        if (turnEl?.querySelector(".user-bubble .image-card img")) return "图片消息";
        if (turnEl?.querySelector(".user-bubble .chip")) return "附件消息";
        return "空白消息";
    }

    function truncateTurnNavigatorText(text, limit = 10) {
        const normalizedText = String(text || "").replace(/\s+/g, " ").trim();
        if (!normalizedText) return "";

        let weightedLength = 0;
        let result = "";
        let truncated = false;

        for (const char of normalizedText) {
            const nextLength = weightedLength + getTurnNavigatorCharWeight(char);
            if (nextLength > limit) {
                truncated = true;
                break;
            }
            result += char;
            weightedLength = nextLength;
        }

        const preview = result.trim();
        if (!truncated) return preview;
        return `${preview || normalizedText.slice(0, 1)}…`;
    }

    function getTurnNavigatorCharWeight(char) {
        if (/[\u3400-\u9fff\uf900-\ufaff]/u.test(char)) return 1;
        if (/[A-Za-z0-9]/.test(char)) return 0.56;
        if (/\s/.test(char)) return 0.32;
        return 0.68;
    }

    function refreshTurnNavigator() {
        if (!refs.turnMap || !refs.turnMapList) return;
        const turns = Array.from(refs.conversation.querySelectorAll(".turn"));
        if (!turns.length) {
            refs.turnMap.hidden = true;
            refs.turnMapList.innerHTML = "";
            state.activeTurnEpoch = "";
            state.turnNavigatorSignature = "";
            syncScrollBottomButtonVisibility();
            syncScrollBottomButtonLayout();
            return;
        }

        const items = turns.map((turnEl, index) => {
            const epoch = String(Number(turnEl.dataset.turnEpoch || index + 1) || index + 1);
            const preview = getTurnNavigatorPreview(turnEl);
            return {
                epoch,
                preview,
                ariaLabel: `跳转到第 ${epoch} 轮：${preview}`,
            };
        });
        const signature = items.map((item) => `${item.epoch}:${item.preview}`).join("\n");
        if (signature !== state.turnNavigatorSignature) {
            refs.turnMapList.innerHTML = items.map((item) => (
                `<button class="turn-map-item" type="button" data-turn-epoch="${escapeAttr(item.epoch)}" aria-label="${escapeAttr(item.ariaLabel)}">`
                + `<span class="turn-map-preview">${escapeHtml(item.preview)}</span>`
                + '<span class="turn-map-dash" aria-hidden="true"></span>'
                + "</button>"
            )).join("");
            state.turnNavigatorSignature = signature;
        }

        refs.turnMap.hidden = false;
        scheduleTurnNavigatorSync();
        syncScrollBottomButtonVisibility();
        syncScrollBottomButtonLayout();
    }

    function onScrollBottomButtonClick() {
        state.followStreaming = true;
        scrollPageToBottom({ behavior: "smooth" });
    }

    function onTurnMapClick(event) {
        const trigger = event.target.closest(".turn-map-item[data-turn-epoch]");
        if (!trigger) return;
        const targetEpoch = String(trigger.dataset.turnEpoch || "").trim();
        if (!targetEpoch) return;
        const targetTurn = Array.from(refs.conversation.querySelectorAll(".turn")).find((turnEl) => (
            String(turnEl.dataset.turnEpoch || "").trim() === targetEpoch
        ));
        if (!targetTurn) return;
        setActiveTurnNavigatorItem(targetEpoch, { scrollIntoView: true });
        jumpToConversationTurn(targetTurn);
    }

    function jumpToConversationTurn(turnEl) {
        if (!turnEl) return;
        const rect = turnEl.getBoundingClientRect();
        const targetTop = window.scrollY + rect.top - Math.max(20, window.innerHeight * 0.12);
        window.scrollTo({ top: Math.max(0, targetTop), behavior: "smooth" });
    }

    function scheduleTurnNavigatorSync() {
        if (state.turnNavigatorFrame) return;
        state.turnNavigatorFrame = window.requestAnimationFrame(() => {
            state.turnNavigatorFrame = 0;
            syncActiveTurnNavigatorItem();
        });
    }

    function syncActiveTurnNavigatorItem() {
        if (!refs.turnMapList || refs.turnMap.hidden) return;
        const turns = Array.from(refs.conversation.querySelectorAll(".turn"));
        if (!turns.length) {
            setActiveTurnNavigatorItem("");
            return;
        }

        const anchorY = window.innerHeight * 0.46;
        let visibleEpoch = "";
        let visibleDistance = Number.POSITIVE_INFINITY;
        let lastBeforeEpoch = "";
        let firstAfterEpoch = "";

        turns.forEach((turnEl, index) => {
            const epoch = String(Number(turnEl.dataset.turnEpoch || index + 1) || index + 1);
            const rect = turnEl.getBoundingClientRect();
            const centerY = rect.top + rect.height / 2;

            if (rect.top <= anchorY) lastBeforeEpoch = epoch;
            if (!firstAfterEpoch && rect.bottom >= anchorY) firstAfterEpoch = epoch;

            if (rect.bottom < 0 || rect.top > window.innerHeight) return;
            const distance = Math.abs(centerY - anchorY);
            if (distance < visibleDistance) {
                visibleDistance = distance;
                visibleEpoch = epoch;
            }
        });

        setActiveTurnNavigatorItem(visibleEpoch || firstAfterEpoch || lastBeforeEpoch || "1");
    }

    function setActiveTurnNavigatorItem(epoch, options = {}) {
        const targetEpoch = String(epoch || "").trim();
        if (targetEpoch === state.activeTurnEpoch && !options.force) return;
        state.activeTurnEpoch = targetEpoch;

        let activeButton = null;
        refs.turnMapList.querySelectorAll(".turn-map-item").forEach((button) => {
            const isActive = String(button.dataset.turnEpoch || "").trim() === targetEpoch;
            button.classList.toggle("is-active", isActive);
            if (isActive) {
                button.setAttribute("aria-current", "step");
                activeButton = button;
            } else {
                button.removeAttribute("aria-current");
            }
        });

        if (activeButton && options.scrollIntoView !== false) {
            activeButton.scrollIntoView({ block: "nearest", inline: "nearest" });
        }
    }

    async function copyToClipboard(text, successMessage = "已复制") {
        const content = String(text || "");
        if (!content.trim()) {
            showToast("没有可复制的内容", "error");
            return;
        }
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(content);
            } else {
                const textarea = document.createElement("textarea");
                textarea.value = content;
                textarea.setAttribute("readonly", "readonly");
                textarea.style.position = "fixed";
                textarea.style.top = "-9999px";
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand("copy");
                textarea.remove();
            }
            showToast(successMessage, "success");
        } catch (error) {
            showToast("复制失败，请检查浏览器权限", "error");
        }
    }

    function buildActionButton(action, title) {
        const icons = {
            copy: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.8"></rect><rect x="4" y="4" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.8"></rect></svg>',
            fork: '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 20h4l10-10a2 2 0 0 0 0-2.83l-1.17-1.17a2 2 0 0 0-2.83 0L4 16v4Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"></path><path d="m12.5 6.5 5 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path></svg>',
        };
        const button = document.createElement("button");
        button.type = "button";
        button.className = "message-action-btn";
        button.dataset.action = action;
        button.title = title;
        button.innerHTML = icons[action] || "";
        return button;
    }

    function ensureUserActions(turnEl) {
        const userRow = turnEl?.querySelector(".user-row");
        const userBubble = turnEl?.querySelector(".user-row .user-bubble");
        if (!userBubble || !userRow) return;
        if (userRow.querySelector(".message-actions[data-side='user']")) return;
        const actions = document.createElement("div");
        actions.className = "message-actions bubble-actions-user";
        actions.dataset.side = "user";
        const copyBtn = buildActionButton("copy", "复制用户消息");
        copyBtn.addEventListener("click", () => void copyToClipboard(getTurnUserText(turnEl), "已复制用户消息"));
        const forkBtn = buildActionButton("fork", "fork 到上一轮并回填此消息");
        forkBtn.addEventListener("click", () => void forkConversationAtTurn(turnEl, getTurnUserText(turnEl)));
        actions.appendChild(copyBtn);
        actions.appendChild(forkBtn);
        userRow.appendChild(actions);
    }

    function ensureAssistantActions(turnEl) {
        const assistantBlock = turnEl?.querySelector(".assistant-block");
        const assistantAnswer = turnEl?.querySelector(".assistant-answer");
        const assistantText = turnEl?.querySelector(".assistant-answer .message-content");
        if (!assistantBlock || !assistantAnswer || !assistantText) return;
        if (!getTurnAssistantText(turnEl)) return;
        if (assistantBlock.querySelector(".message-actions[data-side='assistant']")) return;
        const actions = document.createElement("div");
        actions.className = "message-actions bubble-actions-assistant";
        actions.dataset.side = "assistant";
        const copyBtn = buildActionButton("copy", "复制 AI 回复");
        copyBtn.addEventListener("click", () => void copyToClipboard(getTurnAssistantText(turnEl), "已复制 AI 回复"));
        actions.appendChild(copyBtn);
        assistantBlock.appendChild(actions);
    }

    function enhanceConversationActions() {
        annotateTurnEpochs();
        hydrateAssistantReferenceImages(refs.conversation);
        refs.conversation.querySelectorAll(".turn").forEach((turnEl) => {
            ensureUserActions(turnEl);
            ensureAssistantActions(turnEl);
        });
        refreshTurnNavigator();
        updateToggleMetaButtonState();
    }

    function getSelectedReferenceImageEntries() {
        return Object.values(state.selectedReferenceImages || {});
    }

    function clearSelectedReferenceImages() {
        state.selectedReferenceImages = {};
        syncAssistantReferenceImageToggles();
        refreshDynamicImageCountField();
    }

    function extractReferenceImagePath(source) {
        const value = String(source || "").trim();
        if (!value) return "";
        try {
            const resolved = new URL(value, window.location.origin);
            if (resolved.pathname !== "/api/file") return "";
            return String(resolved.searchParams.get("path") || "").trim();
        } catch {
            return "";
        }
    }

    function deriveReferenceImageName(path) {
        const normalized = String(path || "").trim().replace(/\\/g, "/");
        if (!normalized) return "reference-image";
        return normalized.split("/").pop() || "reference-image";
    }

    function isSeedreamModel(meta = getCurrentModelMeta()) {
        const modelId = String(meta?.id || "").trim();
        return modelId === "doubao-seedream-5-0-260128" || modelId === "doubao-seedream-4-5-251128";
    }

    function getPendingImageAttachmentCount() {
        const uploadedImages = state.attachments.filter((item) => item?.isImage).length;
        return uploadedImages + getSelectedReferenceImageEntries().length;
    }

    function getAvailableGeneratedImageCount() {
        return Math.max(0, 15 - getPendingImageAttachmentCount());
    }

    function normalizeGeneratedImageCount(value, fallback = 1) {
        const availableMax = getAvailableGeneratedImageCount();
        if (availableMax <= 0) return 0;
        let parsed = Number.parseInt(String(value ?? fallback).trim(), 10);
        if (!Number.isFinite(parsed)) parsed = fallback;
        parsed = Math.max(1, Math.min(parsed, availableMax));
        return parsed;
    }

    function syncDynamicImageCountSetting(meta = getCurrentModelMeta(), settings = getCurrentSettings()) {
        if (!isSeedreamModel(meta)) return;
        const field = (meta.extra_fields || []).find((item) => item?.type === "image_count");
        if (!field) return;
        const normalizedValue = normalizeGeneratedImageCount(settings.extras[field.key], Number.parseInt(String(field.default || "1"), 10) || 1);
        settings.extras[field.key] = String(normalizedValue || 0);
    }

    function refreshDynamicImageCountField() {
        const meta = getCurrentModelMeta();
        if (!isSeedreamModel(meta)) return;
        const settings = getCurrentSettings();
        syncDynamicImageCountSetting(meta, settings);
        if (refs.extraMenu.dataset.open === "true") {
            renderExtraMenuContent();
            reopenExtraMenu();
        }
        updateToolbarButtonStates(meta, settings);
    }

    function syncAssistantReferenceImageToggles(root = refs.conversation) {
        if (!root?.querySelectorAll) return;
        root.querySelectorAll(".assistant-reference-toggle-input[data-reference-image-path]").forEach((input) => {
            const path = String(input.dataset.referenceImagePath || "").trim();
            input.checked = !!state.selectedReferenceImages[path];
        });
    }

    function ensureAssistantReferenceToggle(card) {
        if (!card || card.dataset.referenceReady === "true") return;
        const figure = card.closest("figure");
        if (!figure) return;
        const link = card.querySelector(".image-card-link[href]");
        const referencePath = String(figure.dataset.localImagePath || "").trim() || extractReferenceImagePath(link?.getAttribute("href"));
        if (!referencePath) return;

        figure.dataset.referenceReady = "true";
        figure.dataset.localImagePath = referencePath;
        figure.classList.add("assistant-reference-card");

        const toggle = document.createElement("label");
        toggle.className = "assistant-reference-toggle";
        const input = document.createElement("input");
        input.className = "assistant-reference-toggle-input";
        input.type = "checkbox";
        input.dataset.referenceImagePath = referencePath;
        input.checked = !!state.selectedReferenceImages[referencePath];

        const text = document.createElement("span");
        text.className = "assistant-reference-toggle-text";
        text.textContent = "加入下一轮输入";

        toggle.append(input, text);
        input.addEventListener("change", () => {
            if (input.checked) {
                state.selectedReferenceImages[referencePath] = {
                    path: referencePath,
                    name: deriveReferenceImageName(referencePath),
                };
            } else {
                delete state.selectedReferenceImages[referencePath];
            }
            syncAssistantReferenceImageToggles();
            refreshDynamicImageCountField();
        });

        figure.appendChild(toggle);
    }

    function hydrateAssistantReferenceImages(root = refs.conversation) {
        if (!root?.querySelectorAll) return;
        root.querySelectorAll(".assistant-block .image-card, .assistant-live-image-host .image-card").forEach((card) => {
            if (card.closest(".user-bubble")) return;
            ensureAssistantReferenceToggle(card);
        });
        syncAssistantReferenceImageToggles(root);
    }

    function normalizeRecordSearchText(item) {
        const parts = [item?.title || "", item?.basename || "", item?.search_text || ""];
        const files = Array.isArray(item?.files) ? item.files : [];
        files.forEach((file) => {
            parts.push(file?.filename || "", file?.type || "", file?.label || "");
        });
        return parts.join(" ").toLocaleLowerCase();
    }

    function renderRecordList(records, query) {
        const normalizedQuery = String(query || "").trim().toLocaleLowerCase();
        const filteredRecords = normalizedQuery
            ? records.filter((item) => normalizeRecordSearchText(item).includes(normalizedQuery))
            : records;

        if (!filteredRecords.length) {
            return normalizedQuery
                ? '<div class="records-empty is-search-empty">没有匹配的记录。</div>'
                : '<div class="records-empty">暂时还没有可读取的记录。</div>';
        }

        return `<div class="records-list">${filteredRecords.map((item) => {
            const metaParts = [];
            if (item.modified_label) metaParts.push(escapeHtml(item.modified_label));
            if (Array.isArray(item.formats) && item.formats.length) metaParts.push(escapeHtml(item.formats.join(" / ")));
            const displayTitle = item.title || item.basename || "record";
            const fileLinks = (Array.isArray(item.files) ? item.files : []).map((file) => {
                const label = file.label || String(file.type || "").toUpperCase();
                const fileName = file.filename || "";
                return `<button class="records-file-link" type="button" data-record-filename="${escapeAttr(fileName)}"><span class="records-file-kind">${escapeHtml(label)}</span><span class="records-file-name">${escapeHtml(fileName)}</span></button>`;
            }).join("");
            return `<div class="records-item"><div class="records-item-header"><span class="records-item-title">${escapeHtml(displayTitle)}</span><span class="records-item-meta">${metaParts.join(" · ")}</span></div><div class="records-item-files">${fileLinks}</div></div>`;
        }).join("")}</div>`;
    }

    function renderRecordsPanel(records) {
        state.recordsCache = Array.isArray(records) ? records : [];
        refs.recordsPanel.innerHTML = `
            <div class="records-search">
                <input class="records-search-input" id="records-search-input" type="search" placeholder="搜索标题、文件名或格式">
            </div>
            <div class="records-list-host"></div>
        `;
        const searchInput = refs.recordsPanel.querySelector("#records-search-input");
        const listHost = refs.recordsPanel.querySelector(".records-list-host");
        const refreshList = () => {
            if (!listHost) return;
            listHost.innerHTML = renderRecordList(state.recordsCache, searchInput?.value || "");
            listHost.querySelectorAll("[data-record-filename]").forEach((button) => {
                button.addEventListener("click", () => void loadRecord(button.dataset.recordFilename || ""));
            });
        };
        if (searchInput) searchInput.addEventListener("input", refreshList);
        refreshList();
        if (searchInput) searchInput.focus();
    }

    function getCurrentSessionRecord(records) {
        const savedBasename = String(state.currentSavedBasename || "").trim();
        const diskRecords = Array.isArray(records) ? records : [];
        const matchedRecord = savedBasename
            ? diskRecords.find((item) => String(item?.basename || "").trim() === savedBasename)
            : null;
        const formats = Array.isArray(matchedRecord?.formats) ? matchedRecord.formats : (savedBasename ? ["JSON"] : []);
        const files = Array.isArray(matchedRecord?.files) ? matchedRecord.files : [];
        const metaParts = ["当前会话"];
        if (matchedRecord?.modified_label) {
            metaParts.push(matchedRecord.modified_label);
        } else if (!savedBasename) {
            metaParts.push("尚未保存");
        }
        if (formats.length) metaParts.push(formats.join(" / "));

        return {
            title: getCurrentConversationSidebarTitle(),
            basename: savedBasename,
            modified_label: matchedRecord?.modified_label || "",
            formats,
            files,
            load_filename: matchedRecord?.load_filename || "",
            search_text: [getCurrentConversationSidebarTitle(), savedBasename, state.currentTitle, metaParts.join(" ")].join(" ").trim(),
            isCurrentSession: true,
            meta_label: metaParts.join(" · "),
        };
    }

    function getMergedRecordEntries(records) {
        const diskRecords = Array.isArray(records) ? records : [];
        const currentRecord = getCurrentSessionRecord(diskRecords);
        const currentBasename = String(currentRecord?.basename || "").trim().toLocaleLowerCase();
        const otherRecords = diskRecords.filter((item) => {
            const basename = String(item?.basename || "").trim().toLocaleLowerCase();
            return !currentBasename || basename !== currentBasename;
        });
        return currentRecord ? [currentRecord, ...otherRecords] : otherRecords;
    }

    function ensureRecordsPanelShell() {
        if (!refs.recordsPanel) return null;
        let searchInput = refs.recordsPanel.querySelector("#records-search-input");
        let listHost = refs.recordsPanel.querySelector(".records-list-host");
        if (searchInput && listHost) return { searchInput, listHost };

        refs.recordsPanel.innerHTML = `
            <div class="records-sidebar-header">
                <div class="records-sidebar-kicker">History</div>
                <div class="records-sidebar-title">历史记录</div>
                <div class="records-sidebar-note">当前会话和已保存记录都会显示在这里。</div>
            </div>
            <div class="records-search">
                <input class="records-search-input" id="records-search-input" type="search" placeholder="搜索标题、文件名或格式">
            </div>
            <div class="records-list-host"></div>
        `;
        searchInput = refs.recordsPanel.querySelector("#records-search-input");
        listHost = refs.recordsPanel.querySelector(".records-list-host");
        if (searchInput) {
            searchInput.value = state.recordsSearchQuery || "";
            searchInput.addEventListener("input", () => {
                state.recordsSearchQuery = searchInput.value || "";
                renderRecordsPanel();
            });
        }
        return { searchInput, listHost };
    }

    function renderRecordList(records, query) {
        const normalizedQuery = String(query || "").trim().toLocaleLowerCase();
        const mergedRecords = getMergedRecordEntries(records);
        const filteredRecords = normalizedQuery
            ? mergedRecords.filter((item) => normalizeRecordSearchText(item).includes(normalizedQuery))
            : mergedRecords;

        if (!filteredRecords.length) {
            return normalizedQuery
                ? '<div class="records-empty is-search-empty">没有匹配的记录。</div>'
                : '<div class="records-empty">暂时还没有可读取的记录。</div>';
        }

        return `<div class="records-list">${filteredRecords.map((item) => {
            const displayTitle = item.title || item.basename || "record";
            const metaLabel = item.isCurrentSession
                ? (item.meta_label || "当前会话")
                : [item.modified_label || "", Array.isArray(item.formats) ? item.formats.join(" / ") : ""].filter(Boolean).join(" · ");
            const menuKey = String(item.basename || item.load_filename || "").trim();
            const isMenuOpen = !!menuKey && state.openRecordActionMenuKey === menuKey;
            const action = menuKey
                ? `<div class="records-item-actions"><button class="records-item-menu-toggle" type="button" data-record-menu-key="${escapeAttr(menuKey)}" aria-expanded="${isMenuOpen ? "true" : "false"}" aria-label="展开记录操作"><span class="records-item-menu-toggle-dots" aria-hidden="true"><span></span><span></span><span></span></span></button><div class="records-item-menu"${isMenuOpen ? "" : " hidden"}>${item.load_filename ? `<button class="records-item-action" type="button" data-record-action="load" data-record-filename="${escapeAttr(item.load_filename)}">读取</button>` : ""}${item.basename ? `<button class="records-item-action" type="button" data-record-action="archive" data-record-basename="${escapeAttr(item.basename)}" data-record-title="${escapeAttr(displayTitle)}">归档</button><button class="records-item-action is-danger" type="button" data-record-action="delete" data-record-basename="${escapeAttr(item.basename)}" data-record-title="${escapeAttr(displayTitle)}">删除</button>` : ""}</div></div>`
                : "";
            const badge = item.isCurrentSession ? '<span class="records-item-badge">当前</span>' : "";
            const fileTags = (Array.isArray(item.files) ? item.files : []).map((file) => {
                const label = file.label || String(file.type || "").toUpperCase();
                const fileName = file.filename || "";
                return `<span class="records-file-link"><span class="records-file-kind">${escapeHtml(label)}</span><span class="records-file-name">${escapeHtml(fileName)}</span></span>`;
            }).join("");
            const itemClassName = `records-item${item.isCurrentSession ? " is-current" : ""}`;
            return `<article class="${itemClassName}"><div class="records-item-header"><div class="records-item-header-main"><div class="records-item-title-row"><span class="records-item-title">${escapeHtml(displayTitle)}</span>${badge}</div><span class="records-item-meta">${escapeHtml(metaLabel || "")}</span></div>${action}</div>${fileTags ? `<div class="records-item-files">${fileTags}</div>` : ""}</article>`;
        }).join("")}</div>`;
    }

    function renderRecordsPanel(options = {}) {
        const shell = ensureRecordsPanelShell();
        if (!shell) return;
        const { searchInput, listHost } = shell;
        if (searchInput && searchInput.value !== (state.recordsSearchQuery || "")) {
            searchInput.value = state.recordsSearchQuery || "";
        }
        if (!listHost) return;
        listHost.innerHTML = renderRecordList(state.recordsCache, state.recordsSearchQuery || "");
        listHost.querySelectorAll("[data-record-menu-key]").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                toggleRecordActionMenu(button.dataset.recordMenuKey || "");
            });
        });
        listHost.querySelectorAll("[data-record-action='load']").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                closeRecordActionMenu();
                void loadRecord(button.dataset.recordFilename || "");
            });
        });
        listHost.querySelectorAll("[data-record-action='archive']").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                void archiveRecord({
                    basename: button.dataset.recordBasename || "",
                    title: button.dataset.recordTitle || "",
                });
            });
        });
        listHost.querySelectorAll("[data-record-action='delete']").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                closeRecordActionMenu();
                openDeleteConfirmDialog({
                    basename: button.dataset.recordBasename || "",
                    title: button.dataset.recordTitle || "",
                });
            });
        });
        if (options.focusSearch && searchInput) searchInput.focus();
    }

    async function refreshRecordsPanel(options = {}) {
        const focusSearch = !!options.focusSearch;
        const silent = !!options.silent;
        renderRecordsPanel({ focusSearch });
        try {
            const response = await fetch("/api/records");
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "读取记录失败");
            state.recordsCache = Array.isArray(payload.records) ? payload.records : [];
        } catch (error) {
            if (!silent) showToast(error.message || "读取记录失败", "error");
        }
        renderRecordsPanel({ focusSearch });
    }

    async function createSession() {
        const response = await fetch("/api/session/new", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enable_system_prompt: !!state.enableSystemPrompt }),
        });
        if (!response.ok) throw new Error("无法创建浏览器会话");
        const payload = await response.json();
        state.sessionId = payload.session_id;
        state.enableSystemPrompt = payload.enable_system_prompt !== false;
        syncSystemPromptToggle();
        setCurrentSavedBasename("", { refreshRecords: false });
        refreshTurnNavigator();
        setConversationTitle(payload.title || "新对话");
        setContextMessages(payload.context_messages || []);
        setTotalConversationTokens(payload.total_tokens || 0);
        setLatestAssistantThinking(payload.latest_assistant_thinking || "");
    }

    async function resetConversation() {
        if (state.isStreaming) return;
        refs.conversation.innerHTML = "";
        refreshTurnNavigator();
        setCurrentSavedBasename("", { refreshRecords: false });
        setConversationTitle("新对话");
        state.followStreaming = true;
        clearPendingAttachments();
        refs.input.value = "";
        syncTextareaHeight();
        await createSession();
        await refreshRecordsPanel({ silent: true });
    }

    async function saveConversation() {
        if (!state.sessionId) return;
        const response = await fetch("/api/session/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: state.sessionId }),
        });
        const payload = await response.json();
        if (!response.ok) {
            showToast(payload.error || "保存失败", "error");
            return;
        }
        setCurrentSavedBasename(payload.saved_basename || "", { refreshRecords: false });
        await refreshRecordsPanel({ silent: true });
        showToast("已保存到：" + payload.saved_path, "success");
    }

    async function toggleRecordsPanel() {
        const isOpen = document.body.classList.contains("records-open");
        if (isOpen) {
            closeRecordsPanel();
            return;
        }
        setHistorySidebarOpen(true);
        renderRecordsPanel({ focusSearch: true });
        await refreshRecordsPanel({ silent: true, focusSearch: true });
    }

    function closeRecordsPanel() {
        setHistorySidebarOpen(false);
    }

    async function archiveRecord(record) {
        if (state.isStreaming || !state.sessionId) return;
        const basename = String(record?.basename || "").trim();
        if (!basename) return;

        closeRecordActionMenu();
        try {
            const response = await fetch("/api/records/archive", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: state.sessionId, basename }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "归档失败");
            if (typeof payload.saved_basename === "string") {
                setCurrentSavedBasename(payload.saved_basename, { refreshRecords: false });
            }
            await refreshRecordsPanel({ silent: true });
            showToast(`已归档：${record?.title || basename}`, "success");
        } catch (error) {
            showToast(error.message || "归档失败", "error");
        }
    }

    async function confirmDeleteRecord() {
        if (state.isStreaming || !state.sessionId || !state.pendingDeleteRecord) return;
        const record = state.pendingDeleteRecord;
        const basename = String(record?.basename || "").trim();
        if (!basename) {
            closeDeleteConfirmDialog();
            return;
        }

        if (refs.confirmDialogConfirm) refs.confirmDialogConfirm.disabled = true;
        try {
            const response = await fetch("/api/records/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: state.sessionId, basename }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "删除失败");
            if (typeof payload.saved_basename === "string") {
                setCurrentSavedBasename(payload.saved_basename, { refreshRecords: false });
            }
            closeDeleteConfirmDialog();
            await refreshRecordsPanel({ silent: true });
            showToast(`已删除：${record?.title || basename}`, "success");
        } catch (error) {
            showToast(error.message || "删除失败", "error");
        } finally {
            if (refs.confirmDialogConfirm) refs.confirmDialogConfirm.disabled = false;
        }
    }

    async function loadRecord(filename) {
        if (state.isStreaming) return;
        if (!state.sessionId) return;
        const targetFilename = String(filename || "").trim();
        if (!targetFilename) return;

        try {
            const response = await fetch("/api/session/load", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: state.sessionId, filename: targetFilename }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "导入记录失败");

            clearSelectedReferenceImages();
            refs.conversation.innerHTML = payload.conversation_html || "";
            renderMathInContent(refs.conversation);
            hydrateAssistantReferenceImages(refs.conversation);
            applyOutputPreferenceState(refs.conversation);
            setConversationTitle(payload.title || "新对话", { refreshRecords: false });
            setCurrentSavedBasename(payload.saved_basename || "", { refreshRecords: false });
            setContextMessages(payload.context_messages || []);
            setTotalConversationTokens(payload.total_tokens || 0);
            setLatestAssistantThinking(payload.latest_assistant_thinking || "");
            if (typeof payload.saved_basename === "string") {
                setCurrentSavedBasename(payload.saved_basename, { refreshRecords: false });
            }
            state.followStreaming = true;
            if (payload.selected_model && modelMap.has(payload.selected_model)) {
                refs.modelButton.dataset.value = payload.selected_model;
                renderControls();
            }
            annotateTurnEpochs();
            enhanceConversationActions();
            renderRecordsPanel();
            window.scrollTo({ top: 0, behavior: "smooth" });
            showToast("已导入记录：" + (payload.loaded_filename || targetFilename), "success");
        } catch (error) {
            showToast(error.message || "导入记录失败", "error");
        }
    }

    async function forkConversationAtTurn(turnEl, prefillText) {
        if (state.isStreaming) return;
        if (!state.sessionId) return;
        const epoch = Number(turnEl?.dataset?.turnEpoch || 0);
        if (!epoch) {
            showToast("无法识别该轮次，暂时不能 fork", "error");
            return;
        }
        if (epoch <= 1) {
            showToast("第一轮之前没有可 fork 的历史", "error");
            return;
        }

        const forkEpoch = epoch - 1;
        try {
            const response = await fetch("/api/session/fork", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: state.sessionId, fork_epoch: forkEpoch }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "fork 失败");

            refs.conversation.innerHTML = payload.conversation_html || "";
            renderMathInContent(refs.conversation);
            setConversationTitle(payload.title || state.currentTitle || "新对话", { refreshRecords: false });
            setContextMessages(payload.context_messages || []);
            setTotalConversationTokens(payload.total_tokens || 0);
            setLatestAssistantThinking(payload.latest_assistant_thinking || "");
            if (typeof payload.saved_basename === "string") {
                setCurrentSavedBasename(payload.saved_basename, { refreshRecords: false });
            }
            state.followStreaming = true;
            if (payload.selected_model && modelMap.has(payload.selected_model)) {
                refs.modelButton.dataset.value = payload.selected_model;
                renderControls();
            }
            annotateTurnEpochs();
            enhanceConversationActions();
            applyOutputPreferenceState(refs.conversation);
            renderRecordsPanel();

            clearSelectedReferenceImages();
            refs.input.value = prefillText || "";
            syncTextareaHeight();
            renderContextUsage();
            focusComposerInput();
            showToast(`已 fork 到第 ${forkEpoch} 轮，并回填用户消息`, "success");
            window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" });
        } catch (error) {
            showToast(error.message || "fork 失败", "error");
        }
    }

    function getCurrentModelId() {
        return refs.modelButton.dataset.value || bootstrap.defaultModel;
    }

    function getCurrentModelMeta() {
        return modelMap.get(getCurrentModelId()) || bootstrap.models[0];
    }

    function ensureModelSettings(modelId) {
        if (state.settingsByModel[modelId]) return state.settingsByModel[modelId];
        const meta = modelMap.get(modelId);
        const settings = { thinking: meta && meta.thinking ? meta.thinking.default : null, extras: {} };
        for (const field of (meta?.extra_fields || [])) settings.extras[field.key] = cloneValue(field.default);
        state.settingsByModel[modelId] = settings;
        return settings;
    }

    function getCurrentSettings() {
        return ensureModelSettings(getCurrentModelId());
    }

    function flattenThinkingOptions(options) {
        return (options || []).reduce((result, item) => {
            if (Array.isArray(item?.children) && item.children.length) {
                item.children.forEach((child) => result.push(child));
                return result;
            }
            result.push(item);
            return result;
        }, []);
    }

    function getThinkingControlLabel(meta) {
        const configuredLabel = String(meta?.thinking?.label || "").trim();
        if (configuredLabel) return configuredLabel;
        return meta?.thinking?.kind === "resolution" ? "分辨率" : "思考";
    }

    function findThinkingOption(meta, value) {
        const flattened = flattenThinkingOptions(meta?.thinking?.options || []);
        return flattened.find((item) => String(item?.value || "") === String(value || "")) || flattened[0] || null;
    }

    function isThinkingFeatureActive(meta, settings) {
        if (!meta?.thinking) return false;
        if (meta.thinking.kind === "resolution") return false;
        const currentValue = String(settings?.thinking ?? meta.thinking.default ?? "").trim().toLowerCase();
        return !["", "disabled", "off", "none", "false"].includes(currentValue);
    }

    function hasActiveExtraSettings(meta, settings) {
        return (meta?.extra_fields || []).some((field) => {
            const currentValue = settings?.extras?.[field.key];
            if (field.type === "boolean") return currentValue === true;
            if (field.type === "image_count") return Number.parseInt(String(currentValue || "1"), 10) > 1;
            return currentValue !== undefined && String(currentValue) !== String(field.default ?? "");
        });
    }

    function updateToolbarButtonStates(meta, settings) {
        refs.modelButton.classList.remove("is-feature-pill");
        refs.modelButton.classList.toggle("is-open", refs.modelMenu?.dataset.open === "true");
        refs.thinkingButton.classList.toggle("is-feature-pill", isThinkingFeatureActive(meta, settings));
        refs.thinkingButton.classList.toggle("is-open", refs.thinkingMenu?.dataset.open === "true");
        refs.extraButton.classList.toggle("is-feature-pill", hasActiveExtraSettings(meta, settings));
        refs.extraButton.classList.toggle("is-open", refs.extraMenu?.dataset.open === "true");
    }

    function renderControls() {
        const meta = getCurrentModelMeta();
        const settings = ensureModelSettings(meta.id);
        syncDynamicImageCountSetting(meta, settings);
        refs.attachButton.disabled = !meta.supports_attachments;
        refs.attachButton.title = meta.supports_attachments ? "添加文件" : "当前模型不支持附件";
        refs.modelButton.innerHTML = escapeHtml(meta.label);
        refs.modelButton.title = `模型：${meta.label}`;
        renderModelMenu(meta.id);

        if (meta.thinking) {
            refs.thinkingSlot.hidden = false;
            settings.thinking = settings.thinking || meta.thinking.default;
            const currentThinking = findThinkingOption(meta, settings.thinking);
            const controlLabel = getThinkingControlLabel(meta);
            refs.thinkingButton.innerHTML = escapeHtml(currentThinking?.label || "");
            refs.thinkingButton.title = `${controlLabel}：${currentThinking?.label || ""}`;
            refs.thinkingButton.setAttribute("aria-label", `${controlLabel}：${currentThinking?.label || ""}`);
            refs.thinkingButton.title = `${controlLabel}: ${currentThinking?.label || ""}`;
            refs.thinkingButton.setAttribute("aria-label", `${controlLabel}: ${currentThinking?.label || ""}`);
            renderThinkingMenu(meta, settings.thinking);
        } else {
            refs.thinkingSlot.hidden = true;
            refs.thinkingButton.innerHTML = "";
            refs.thinkingButton.title = "";
            refs.thinkingButton.setAttribute("aria-label", "思考选项");
            refs.thinkingMenu.innerHTML = "";
        }
        refs.extraButton.title = "额外配置";
        renderExtraMenuContent();
        updateToolbarButtonStates(meta, settings);
    }

    function renderModelMenu(selectedId) {
        refs.modelMenu.innerHTML = bootstrap.models.map((item) => {
            const selectedClass = item.id === selectedId ? " is-selected" : "";
            return `<button class="dropdown-option${selectedClass}" type="button" data-model-id="${escapeAttr(item.id)}" title="${escapeAttr(item.label)}">${escapeHtml(item.label)}</button>`;
        }).join("");
    }

    function renderThinkingMenu(meta, currentValue) {
        refs.thinkingMenu.innerHTML = meta.thinking.options.map((item) => {
            if (Array.isArray(item?.children) && item.children.length) {
                const selectedChild = item.children.find((child) => String(child.value || "") === String(currentValue || ""));
                const selectedClass = selectedChild ? " is-selected" : "";
                return `
                    <div class="dropdown-option-group${selectedClass}">
                        <button class="dropdown-option dropdown-option--submenu${selectedClass}" type="button" tabindex="-1" aria-hidden="true">
                            <span>${escapeHtml(item.label || "更多")}</span>
                            <span class="dropdown-submenu-caret" aria-hidden="true"></span>
                        </button>
                        <div class="dropdown-submenu">
                            ${item.children.map((child) => {
                                const childSelectedClass = String(child.value || "") === String(currentValue || "") ? " is-selected" : "";
                                return `<button class="dropdown-option dropdown-option--child${childSelectedClass}" type="button" data-thinking-value="${escapeAttr(child.value)}" title="${escapeAttr(child.label)}" aria-label="${escapeAttr(child.label)}">${escapeHtml(child.label)}</button>`;
                            }).join("")}
                        </div>
                    </div>
                `;
            }
            const selectedClass = item.value === currentValue ? " is-selected" : "";
            return `<button class="dropdown-option${selectedClass}" type="button" data-thinking-value="${escapeAttr(item.value)}" title="${escapeAttr(item.label)}" aria-label="${escapeAttr(item.label)}">${escapeHtml(item.label)}</button>`;
        }).join("");
    }

    function renderExtraMenuContent() {
        const meta = getCurrentModelMeta();
        const settings = getCurrentSettings();
        const fields = getVisibleExtraFields(meta, settings);
        if (fields.length === 0) {
            refs.extraButton.hidden = true;
            refs.extraMenu.hidden = true;
            refs.extraMenu.innerHTML = "";
            refs.extraButton.classList.remove("is-feature-pill", "is-open");
            return;
        }
        refs.extraButton.hidden = false;
        refs.extraMenu.innerHTML = `<div class="extra-menu-grid">${fields.map((field) => renderExtraField(field, settings.extras[field.key])).join("")}</div>`;
        refs.extraMenu.hidden = refs.extraMenu.dataset.open !== "true";
        updateToolbarButtonStates(meta, settings);
    }

    function getVisibleExtraFields(meta, settings) {
        return (meta.extra_fields || []).filter((field) => shouldShowField(field, settings.extras));
    }

    function getVisibleExtraFieldKeys(meta, settings) {
        return getVisibleExtraFields(meta, settings).map((field) => String(field.key));
    }

    function didVisibleExtraFieldsChange(previousKeys, nextKeys) {
        if (previousKeys.length !== nextKeys.length) return true;
        for (let index = 0; index < previousKeys.length; index += 1) {
            if (previousKeys[index] !== nextKeys[index]) return true;
        }
        return false;
    }

    function syncExtraFieldStateInPlace(key, kind, value) {
        if (kind === "boolean") {
            const toggle = refs.extraMenu.querySelector(`[data-extra-kind="boolean"][data-extra-key="${escapeSelector(key)}"]`);
            if (!toggle) return;
            const isChecked = value === true;
            toggle.classList.toggle("is-checked", isChecked);
            toggle.setAttribute("aria-pressed", isChecked ? "true" : "false");
            return;
        }
        if (kind === "select") {
            const selectButtons = refs.extraMenu.querySelectorAll(`[data-extra-kind="select"][data-extra-key="${escapeSelector(key)}"]`);
            selectButtons.forEach((button) => {
                const isSelected = String(button.dataset.extraValue || "") === String(value ?? "");
                button.classList.toggle("is-selected", isSelected);
                button.setAttribute("aria-pressed", isSelected ? "true" : "false");
            });
            return;
        }
        if (kind === "image_count") {
            const normalizedValue = String(normalizeGeneratedImageCount(value, 1));
            const choiceButtons = refs.extraMenu.querySelectorAll(`[data-extra-kind="image_count"][data-extra-key="${escapeSelector(key)}"]`);
            choiceButtons.forEach((button) => {
                const isSelected = String(button.dataset.extraValue || "") === normalizedValue;
                button.classList.toggle("is-selected", isSelected);
                button.setAttribute("aria-pressed", isSelected ? "true" : "false");
            });
            const customButton = refs.extraMenu.querySelector(`[data-extra-kind="image_count_custom"][data-extra-key="${escapeSelector(key)}"]`);
            if (customButton) {
                const isCustomSelected = normalizedValue !== "0" && !["1", "2", "3", "4"].includes(normalizedValue);
                customButton.classList.toggle("is-selected", isCustomSelected);
                customButton.setAttribute("aria-pressed", isCustomSelected ? "true" : "false");
                customButton.textContent = isCustomSelected ? `自定义 ${normalizedValue}` : "自定义";
            }
        }
    }

    function escapeSelector(value) {
        if (window.CSS && typeof window.CSS.escape === "function") {
            return window.CSS.escape(String(value));
        }
        return String(value).replace(/["\\]/g, "\\$&");
    }

    function onModelMenuClick(event) {
        const option = event.target.closest("[data-model-id]");
        if (!option) return;
        refs.modelButton.dataset.value = option.dataset.modelId;
        closeAllMenus();
        renderControls();
    }

    function onThinkingMenuClick(event) {
        const option = event.target.closest("[data-thinking-value]");
        if (!option) return;
        getCurrentSettings().thinking = option.dataset.thinkingValue;
        closeAllMenus();
        renderControls();
    }

    function toggleMenu(kind) {
        const menuMap = {
            model: refs.modelMenu,
            thinking: refs.thinkingMenu,
            extra: refs.extraMenu,
        };
        const triggerMap = {
            model: refs.modelButton,
            thinking: refs.thinkingButton,
            extra: refs.extraButton,
        };
        const menu = menuMap[kind];
        const trigger = triggerMap[kind];
        if (!menu) return;
        const isOpen = menu.dataset.open === "true";
        if (kind === "extra" && isOpen) {
            menu.dataset.open = "true";
            menu.hidden = false;
            trigger?.classList.add("is-open");
            return;
        }
        closeAllMenus();
        if (isOpen) return;
        menu.dataset.open = "true";
        menu.hidden = false;
        trigger?.classList.add("is-open");
    }

    function closeAllMenus() {
        [refs.modelMenu, refs.thinkingMenu, refs.extraMenu].forEach((menu) => {
            delete menu.dataset.open;
            menu.hidden = true;
        });
        [refs.modelButton, refs.thinkingButton, refs.extraButton].forEach((button) => button?.classList.remove("is-open"));
    }

    function openImageLightbox(src, caption) {
        const resolvedSrc = String(src || "").trim();
        if (!resolvedSrc || !refs.imageLightboxOverlay || !refs.imageLightboxImage) return;
        refs.imageLightboxImage.src = resolvedSrc;
        refs.imageLightboxImage.alt = String(caption || "").trim() || "图片预览";
        if (refs.imageLightboxCaption) {
            refs.imageLightboxCaption.textContent = String(caption || "").trim();
            refs.imageLightboxCaption.hidden = !refs.imageLightboxCaption.textContent;
        }
        refs.imageLightboxOverlay.hidden = false;
        refs.imageLightboxOverlay.setAttribute("aria-hidden", "false");
        refs.imageLightboxClose?.focus({ preventScroll: true });
    }

    function closeImageLightbox() {
        if (!refs.imageLightboxOverlay || refs.imageLightboxOverlay.hidden) return;
        refs.imageLightboxOverlay.hidden = true;
        refs.imageLightboxOverlay.setAttribute("aria-hidden", "true");
        if (refs.imageLightboxImage) refs.imageLightboxImage.removeAttribute("src");
    }

    function shouldShowField(field, extras) {
        if (!field.show_when) return true;
        return extras[field.show_when.key] === field.show_when.equals;
    }

    function renderExtraField(field, value) {
        if (field.type === "boolean") {
            const description = typeof field.description === "string" ? field.description.trim() : "";
            const copyHtml = description
                ? `<span class="extra-toggle-copy"><span class="extra-toggle-label">${escapeHtml(field.label)}</span><span class="extra-toggle-description">${escapeHtml(description)}</span></span>`
                : `<span class="extra-toggle-label">${escapeHtml(field.label)}</span>`;
            return `<button class="extra-toggle${value ? " is-checked" : ""}" type="button" data-extra-key="${escapeAttr(field.key)}" data-extra-kind="boolean" aria-pressed="${value ? "true" : "false"}" title="${escapeAttr(field.label)}"><span class="extra-toggle-indicator" aria-hidden="true"></span>${copyHtml}</button>`;
        }
        if (field.type === "select") {
            return `<div class="extra-field extra-field--choices"><label>${escapeHtml(field.label)}</label><div class="extra-choice-list">${field.options.map((option) => {
                const selectedClass = option.value === value ? " is-selected" : "";
                return `<button class="extra-choice-button${selectedClass}" type="button" data-extra-key="${escapeAttr(field.key)}" data-extra-kind="select" data-extra-value="${escapeAttr(option.value)}" aria-pressed="${option.value === value ? "true" : "false"}" title="${escapeAttr(option.label)}">${escapeHtml(option.label)}</button>`;
            }).join("")}</div></div>`;
        }
        if (field.type === "image_count") {
            const normalizedValue = String(normalizeGeneratedImageCount(value, Number.parseInt(String(field.default || "1"), 10) || 1));
            const availableMax = getAvailableGeneratedImageCount();
            return `<div class="extra-field extra-field--choices"><label>${escapeHtml(field.label)}</label><div class="extra-choice-list">${field.options.map((option) => {
                const optionValue = String(option.value || "");
                const numericValue = Number.parseInt(optionValue, 10);
                const isDisabled = !Number.isFinite(numericValue) || numericValue > availableMax || availableMax <= 0;
                const selectedClass = optionValue === normalizedValue ? " is-selected" : "";
                const disabledAttr = isDisabled ? " disabled" : "";
                return `<button class="extra-choice-button${selectedClass}" type="button" data-extra-key="${escapeAttr(field.key)}" data-extra-kind="image_count" data-extra-value="${escapeAttr(optionValue)}" aria-pressed="${optionValue === normalizedValue ? "true" : "false"}"${disabledAttr}>${escapeHtml(option.label)}</button>`;
            }).join("")}<button class="extra-choice-button${!["1", "2", "3", "4"].includes(normalizedValue) && normalizedValue !== "0" ? " is-selected" : ""}" type="button" data-extra-key="${escapeAttr(field.key)}" data-extra-kind="image_count_custom" aria-pressed="${!["1", "2", "3", "4"].includes(normalizedValue) && normalizedValue !== "0" ? "true" : "false"}"${availableMax <= 0 ? " disabled" : ""}>${!["1", "2", "3", "4"].includes(normalizedValue) && normalizedValue !== "0" ? `自定义 ${escapeHtml(normalizedValue)}` : "自定义"}</button></div></div>`;
        }
        return `<div class="extra-field"><label>${escapeHtml(field.label)}</label><input type="text" value="${escapeAttr(String(value ?? ""))}" data-extra-key="${escapeAttr(field.key)}"></div>`;
    }

    function reopenExtraMenu() {
        refs.extraMenu.dataset.open = "true";
        refs.extraMenu.hidden = false;
    }

    function animateExtraDetailsEnter() {
        const detailItems = Array.from(refs.extraMenu.querySelectorAll(".extra-menu-grid > *"));
        if (!detailItems.length) return;
        detailItems.forEach((item, index) => {
            item.classList.remove("is-detail-enter");
            item.style.setProperty("--detail-enter-delay", `${Math.min(index * 34, 170)}ms`);
        });
        requestAnimationFrame(() => {
            detailItems.forEach((item) => item.classList.add("is-detail-enter"));
            window.setTimeout(() => {
                detailItems.forEach((item) => {
                    item.classList.remove("is-detail-enter");
                    item.style.removeProperty("--detail-enter-delay");
                });
            }, 520);
        });
    }

    function onExtraMenuClick(event) {
        event.stopPropagation();
        const toggle = event.target.closest("[data-extra-kind][data-extra-key]");
        if (!toggle) return;
        const key = String(toggle.dataset.extraKey || "").trim();
        const kind = String(toggle.dataset.extraKind || "").trim();
        if (!key || !kind) return;

        const meta = getCurrentModelMeta();
        const settings = getCurrentSettings();
        const previousVisibleKeys = getVisibleExtraFieldKeys(meta, settings);
        if (kind === "boolean") {
            settings.extras[key] = !(settings.extras[key] === true);
        } else if (kind === "select") {
            settings.extras[key] = String(toggle.dataset.extraValue || "");
        } else if (kind === "image_count") {
            settings.extras[key] = String(normalizeGeneratedImageCount(toggle.dataset.extraValue || "1", 1));
        } else if (kind === "image_count_custom") {
            const nextValue = window.prompt("输入生成张数", String(settings.extras[key] || "1"));
            if (nextValue === null) return;
            const normalizedValue = normalizeGeneratedImageCount(nextValue, 1);
            if (!(normalizedValue > 0)) return;
            settings.extras[key] = String(normalizedValue);
        } else {
            return;
        }

        const nextVisibleKeys = getVisibleExtraFieldKeys(meta, settings);
        if (didVisibleExtraFieldsChange(previousVisibleKeys, nextVisibleKeys)) {
            renderExtraMenuContent();
            reopenExtraMenu();
            animateExtraDetailsEnter();
        } else {
            syncExtraFieldStateInPlace(key, kind, settings.extras[key]);
            updateToolbarButtonStates(meta, settings);
        }
    }

    function onExtraFieldChange(event) {
        event.stopPropagation();
        const key = event.target.dataset.extraKey;
        if (!key) return;
        const meta = getCurrentModelMeta();
        const settings = getCurrentSettings();
        const previousVisibleKeys = getVisibleExtraFieldKeys(meta, settings);
        settings.extras[key] = event.target.value;
        const nextVisibleKeys = getVisibleExtraFieldKeys(meta, settings);
        if (didVisibleExtraFieldsChange(previousVisibleKeys, nextVisibleKeys)) {
            renderExtraMenuContent();
            reopenExtraMenu();
            animateExtraDetailsEnter();
        } else {
            updateToolbarButtonStates(meta, settings);
        }
    }

    function currentModelSupportsAttachments() {
        return !!getCurrentModelMeta().supports_attachments;
    }

    function addFilesToAttachments(files, source) {
        const normalizedFiles = normalizeAttachmentFiles(files, source);
        if (!normalizedFiles.length) return;
        if (!currentModelSupportsAttachments()) {
            showToast("当前模型不支持附件", "error");
            return;
        }

        for (const file of normalizedFiles) {
            const isImage = isImageFile(file);
            state.attachments.push({
                id: randomId(),
                file,
                isImage,
                previewUrl: isImage ? URL.createObjectURL(file) : "",
            });
        }
        renderAttachmentStrip();
        refreshDynamicImageCountField();
    }

    function normalizeAttachmentFiles(files, source) {
        return Array.from(files || []).map((file, index) => normalizeAttachmentFile(file, source, index)).filter(Boolean);
    }

    function normalizeAttachmentFile(file, source, index) {
        if (!(file instanceof Blob)) return null;
        const type = String(file.type || "").trim();
        const rawName = typeof file.name === "string" ? file.name.trim() : "";
        if (file instanceof File && rawName) return file;
        return new File(
            [file],
            rawName || generateAttachmentName(type, source, index),
            { type: type || "application/octet-stream", lastModified: Date.now() }
        );
    }

    function generateAttachmentName(type, source, index) {
        const prefix = source === "paste" ? "pasted-image" : source === "drop" ? "dropped-file" : "upload-file";
        const stamp = new Date().toISOString().replace(/[^\d]/g, "").slice(0, 14);
        return `${prefix}-${stamp}-${index + 1}.${inferExtensionFromMime(type)}`;
    }

    function inferExtensionFromMime(type) {
        const normalizedType = String(type || "").toLowerCase();
        const mapping = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/webp": "webp",
            "image/gif": "gif",
            "image/bmp": "bmp",
            "image/svg+xml": "svg",
            "application/pdf": "pdf",
            "text/plain": "txt",
        };
        if (mapping[normalizedType]) return mapping[normalizedType];
        if (normalizedType.startsWith("image/")) {
            return normalizedType.slice(6).replace(/[^a-z0-9]+/g, "") || "png";
        }
        return "bin";
    }

    function isImageFile(file) {
        return String(file?.type || "").toLowerCase().startsWith("image/");
    }

    function hasTransferFiles(dataTransfer) {
        if (!dataTransfer) return false;
        if ((dataTransfer.files || []).length > 0) return true;
        return Array.from(dataTransfer.types || []).includes("Files");
    }

    function onComposerDragEnter(event) {
        if (!hasTransferFiles(event.dataTransfer) || !currentModelSupportsAttachments()) return;
        event.preventDefault();
        state.dragDepth += 1;
        refs.composerCard.classList.add("is-drag-over");
    }

    function onComposerDragOver(event) {
        if (!hasTransferFiles(event.dataTransfer) || !currentModelSupportsAttachments()) return;
        event.preventDefault();
        if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
        refs.composerCard.classList.add("is-drag-over");
    }

    function onComposerDragLeave(event) {
        if (!hasTransferFiles(event.dataTransfer)) return;
        event.preventDefault();
        state.dragDepth = Math.max(0, state.dragDepth - 1);
        if (state.dragDepth === 0) refs.composerCard.classList.remove("is-drag-over");
    }

    function onComposerDrop(event) {
        if (!hasTransferFiles(event.dataTransfer)) return;
        event.preventDefault();
        state.dragDepth = 0;
        refs.composerCard.classList.remove("is-drag-over");
        addFilesToAttachments(event.dataTransfer.files || [], "drop");
        focusComposerInput();
    }

    function onInputPaste(event) {
        const clipboard = event.clipboardData;
        if (!clipboard) return;
        const files = extractClipboardFiles(clipboard);
        if (!files.length) return;

        const plainText = clipboard.getData("text/plain");
        if (plainText) insertTextAtCursor(plainText);
        event.preventDefault();
        addFilesToAttachments(files, "paste");
        syncTextareaHeight();
    }

    function extractClipboardFiles(clipboard) {
        const items = Array.from(clipboard.items || []);
        const files = [];
        for (const item of items) {
            if (item.kind !== "file") continue;
            const file = item.getAsFile();
            if (file) files.push(file);
        }
        return files.length ? files : Array.from(clipboard.files || []);
    }

    function insertTextAtCursor(text) {
        if (!text) return;
        const start = refs.input.selectionStart ?? refs.input.value.length;
        const end = refs.input.selectionEnd ?? refs.input.value.length;
        refs.input.setRangeText(text, start, end, "end");
    }

    function clearPendingAttachments() {
        for (const item of state.attachments) releaseAttachmentPreview(item);
        state.attachments = [];
        state.dragDepth = 0;
        refs.composerCard.classList.remove("is-drag-over");
        refs.fileInput.value = "";
        renderAttachmentStrip();
        refreshDynamicImageCountField();
    }

    function detachPendingAttachments() {
        if (state.attachments.length === 0) {
            state.dragDepth = 0;
            refs.composerCard.classList.remove("is-drag-over");
            refs.fileInput.value = "";
            return [];
        }
        const detached = state.attachments;
        state.attachments = [];
        state.dragDepth = 0;
        refs.composerCard.classList.remove("is-drag-over");
        refs.fileInput.value = "";
        renderAttachmentStrip();
        refreshDynamicImageCountField();
        return detached;
    }

    function restorePendingAttachments(attachments) {
        releaseAttachmentList(state.attachments);
        state.attachments = Array.isArray(attachments) ? attachments : [];
        state.dragDepth = 0;
        refs.composerCard.classList.remove("is-drag-over");
        refs.fileInput.value = "";
        renderAttachmentStrip();
        refreshDynamicImageCountField();
    }

    function releaseAttachmentList(attachments) {
        for (const item of attachments || []) releaseAttachmentPreview(item);
    }

    function releaseAttachmentPreview(item) {
        if (!item || !item.previewUrl) return;
        URL.revokeObjectURL(item.previewUrl);
        item.previewUrl = "";
    }

    function onFilesSelected(event) {
        addFilesToAttachments(event.target.files || [], "picker");
        refs.fileInput.value = "";
    }

    function renderAttachmentStrip() {
        if (state.attachments.length === 0) {
            refs.attachmentStrip.hidden = true;
            refs.attachmentStrip.innerHTML = "";
            syncComposerLayout();
            return;
        }
        refs.attachmentStrip.hidden = false;
        refs.attachmentStrip.innerHTML = state.attachments.map((item) => `<span class="attachment-chip"><span>${escapeHtml(item.file.name)}</span><button type="button" data-remove-id="${escapeAttr(item.id)}">×</button></span>`).join("");
        refs.attachmentStrip.querySelectorAll("[data-remove-id]").forEach((button) => {
            button.addEventListener("click", () => {
                state.attachments = state.attachments.filter((item) => item.id !== button.dataset.removeId);
                renderAttachmentStrip();
            });
        });
    }

    function renderAttachmentStrip() {
        if (state.attachments.length === 0) {
            refs.attachmentStrip.hidden = true;
            refs.attachmentStrip.innerHTML = "";
            syncComposerLayout();
            return;
        }
        refs.attachmentStrip.hidden = false;
        refs.attachmentStrip.innerHTML = state.attachments.map((item) => {
            const thumb = item.isImage && item.previewUrl
                ? `<img class="attachment-thumb" src="${escapeAttr(item.previewUrl)}" alt="${escapeAttr(item.file.name)}">`
                : `<span class="attachment-thumb-placeholder">${escapeHtml(item.isImage ? "IMG" : "FILE")}</span>`;
            const kindLabel = item.isImage ? "图片" : "附件";
            return `<div class="attachment-card">${thumb}<div class="attachment-text"><div class="attachment-name">${escapeHtml(item.file.name)}</div><div class="attachment-kind">${escapeHtml(kindLabel)}</div></div><button class="attachment-remove" type="button" data-remove-id="${escapeAttr(item.id)}">×</button></div>`;
        }).join("");
        refs.attachmentStrip.querySelectorAll("[data-remove-id]").forEach((button) => {
            button.addEventListener("click", () => {
                state.attachments.filter((item) => item.id === button.dataset.removeId).forEach(releaseAttachmentPreview);
                state.attachments = state.attachments.filter((item) => item.id !== button.dataset.removeId);
                renderAttachmentStrip();
                refreshDynamicImageCountField();
            });
        });
        syncComposerLayout();
    }

    function toggleExpanded() {
        const nextExpanded = !state.isExpanded;
        state.isExpanded = nextExpanded;
        refs.composerCard.classList.toggle("expanded", nextExpanded);
        playComposerResizeAnimation(nextExpanded);
        syncExpandButtonState();
        syncTextareaHeight({ animate: false });
        window.requestAnimationFrame(syncComposerLayout);
        focusComposerInput();
    }

    function focusComposerInput() {
        if (!refs.input) return;
        try {
            refs.input.focus({ preventScroll: true });
        } catch {
            refs.input.focus();
        }
    }

    function syncExpandButtonState() {
        if (!refs.expandButton) return;
        const label = state.isExpanded ? "缩小输入框" : "放大输入框";
        refs.expandButton.classList.toggle("is-expanded", state.isExpanded);
        refs.expandButton.setAttribute("aria-pressed", state.isExpanded ? "true" : "false");
        refs.expandButton.setAttribute("aria-label", label);
        refs.expandButton.title = label;
    }

    function playComposerResizeAnimation(isExpanding) {
        if (!refs.composerCard) return;
        window.clearTimeout(composerExpansionAnimationTimer);
        refs.composerCard.classList.remove("is-expanding", "is-collapsing");
        void refs.composerCard.offsetWidth;
        refs.composerCard.classList.add(isExpanding ? "is-expanding" : "is-collapsing");
        composerExpansionAnimationTimer = window.setTimeout(() => {
            refs.composerCard.classList.remove("is-expanding", "is-collapsing");
            syncTextareaHeight({ animate: false });
            syncComposerLayout();
        }, isExpanding ? 300 : 260);
    }

    function syncTextareaHeight(options = {}) {
        const shouldAnimate = options.animate !== false;
        const bounds = getTextareaHeightBounds();
        const previousHeight = Math.ceil(refs.input.getBoundingClientRect().height || 0);
        const contentHeight = measureTextareaContentHeight();
        const targetHeight = Math.min(Math.max(contentHeight, bounds.min), bounds.max);

        if (shouldAnimate && previousHeight && Math.abs(previousHeight - targetHeight) > 1) {
            refs.input.style.transition = "none";
            refs.input.style.minHeight = `${bounds.min}px`;
            refs.input.style.maxHeight = `${bounds.max}px`;
            refs.input.style.height = `${previousHeight}px`;
            void refs.input.offsetHeight;
            refs.input.style.removeProperty("transition");
        } else if (!shouldAnimate) {
            refs.input.style.transition = "none";
        }

        refs.input.style.minHeight = `${bounds.min}px`;
        refs.input.style.maxHeight = `${bounds.max}px`;
        refs.input.style.height = `${targetHeight}px`;
        refs.input.style.overflowY = contentHeight > bounds.max ? "auto" : "hidden";
        if (!shouldAnimate) {
            void refs.input.offsetHeight;
            refs.input.style.removeProperty("transition");
        }
        syncComposerLayout();
    }

    function measureTextareaContentHeight() {
        const previousTransition = refs.input.style.transition;
        const previousMinHeight = refs.input.style.minHeight;
        const previousMaxHeight = refs.input.style.maxHeight;
        const previousHeight = refs.input.style.height;
        const previousOverflowY = refs.input.style.overflowY;

        refs.input.style.transition = "none";
        refs.input.style.minHeight = "0px";
        refs.input.style.maxHeight = "none";
        refs.input.style.height = "0px";
        refs.input.style.overflowY = "hidden";
        const contentHeight = Math.ceil(refs.input.scrollHeight || 0);

        refs.input.style.transition = previousTransition;
        refs.input.style.minHeight = previousMinHeight;
        refs.input.style.maxHeight = previousMaxHeight;
        refs.input.style.height = previousHeight;
        refs.input.style.overflowY = previousOverflowY;

        return contentHeight;
    }

    function getTextareaHeightBounds() {
        return state.isExpanded
            ? { min: COMPOSER_EXPANDED_MIN_HEIGHT, max: COMPOSER_EXPANDED_MAX_HEIGHT }
            : { min: COMPOSER_COLLAPSED_MIN_HEIGHT, max: COMPOSER_COLLAPSED_MAX_HEIGHT };
    }

    function onInputKeyDown(event) {
        if (state.isStreaming) return;
        if (state.isExpanded) {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault();
                void sendMessage();
            }
            return;
        }
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void sendMessage();
        }
    }

    function updateSendButtonState() {
        if (!refs.sendButton) return;
        refs.sendButton.classList.toggle("is-streaming", state.isStreaming);
        refs.sendButton.classList.toggle("is-stop-blocked", state.isStreaming && state.streamStopBlocked);
        refs.sendButton.disabled = false;
        if (state.isStreaming) {
            const blocked = state.streamStopBlocked;
            refs.sendButton.setAttribute("aria-disabled", blocked ? "true" : "false");
            refs.sendButton.setAttribute("aria-label", blocked ? "工具调用中，暂不能停止" : "停止流式输出");
            refs.sendButton.title = blocked ? "工具调用中，暂不能停止" : "停止流式输出";
            return;
        }
        refs.sendButton.removeAttribute("aria-disabled");
        refs.sendButton.setAttribute("aria-label", "发送消息");
        refs.sendButton.title = "发送消息";
    }

    function setStreamStopBlocked(blocked) {
        const nextBlocked = !!blocked;
        if (state.streamStopBlocked === nextBlocked) return;
        state.streamStopBlocked = nextBlocked;
        updateSendButtonState();
    }

    function stopStreaming() {
        if (!state.isStreaming) return;
        if (state.streamStopBlocked) {
            showToast("工具调用中，暂不能停止流式输出。", "info");
            return;
        }
        if (!state.streamAbortController) return;
        state.stopStreamRequested = true;
        state.streamAbortController.abort();
    }

    async function sendMessage() {
        if (state.isStreaming || !state.sessionId) return;
        const text = refs.input.value;
        const selectedReferenceImagesForTurn = getSelectedReferenceImageEntries();
        const meta = getCurrentModelMeta();
        const settings = getCurrentSettings();
        syncDynamicImageCountSetting(meta, settings);
        if (!text.trim() && state.attachments.length === 0 && selectedReferenceImagesForTurn.length === 0) return;
        if (selectedReferenceImagesForTurn.length > 0 && !currentModelSupportsAttachments()) {
            showToast("当前模型不支持图片输入", "error");
            return;
        }

        if (isSeedreamModel(meta) && getAvailableGeneratedImageCount() <= 0) {
            showToast("当前图片数量已达到上限", "error");
            return;
        }

        const previousContextMessages = cloneContextMessages();
        const previousTitle = state.currentTitle;
        const previousSavedBasename = state.currentSavedBasename;
        const controller = new AbortController();
        state.streamAbortController = controller;
        state.stopStreamRequested = false;
        state.streamStopBlocked = false;
        state.isStreaming = true;
        state.followStreaming = isAtPageBottom();
        updateSendButtonState();
        syncSystemPromptToggle();
        closeAllMenus();
        closeRecordActionMenu();

        const referenceImagePaths = selectedReferenceImagesForTurn.map((item) => item.path).filter(Boolean);
        const attachmentsForTurn = state.attachments.slice().concat(
            selectedReferenceImagesForTurn.map((item) => ({ file: { name: item.name || "reference-image" } }))
        );
        const formData = new FormData();
        formData.append("request", JSON.stringify({
            session_id: state.sessionId,
            message: text,
            model: meta.id,
            thinking: settings.thinking,
            extras: settings.extras,
            reference_images: referenceImagePaths,
            enable_system_prompt: !!state.enableSystemPrompt,
        }));
        for (const item of state.attachments) formData.append("attachments", item.file, item.file.name);

        refs.input.value = "";
        let detachedAttachments = detachPendingAttachments();
        let requestCompleted = false;
        syncTextareaHeight({ animate: false });
        setContextMessages([...previousContextMessages, { role: "user", content: text }]);
        const turn = createTurn(text.trim() || "(空消息)", attachmentsForTurn);
        turn.restoreContextEstimate = () => setContextMessages(previousContextMessages);

        try {
            const response = await fetch("/api/chat", { method: "POST", body: formData, signal: controller.signal });
            if (!response.ok || !response.body) throw new Error("请求失败");

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";
                for (const line of lines) {
                    if (!line.trim()) continue;
                    const event = JSON.parse(line);
                    handleStreamEvent(turn, event);
                    if (event.type === "done") requestCompleted = true;
                }
            }
            if (buffer.trim()) {
                const event = JSON.parse(buffer);
                handleStreamEvent(turn, event);
                if (event.type === "done") requestCompleted = true;
            }
            if (requestCompleted) clearSelectedReferenceImages();
        } catch (error) {
            setContextMessages(previousContextMessages);
            if (state.stopStreamRequested && error?.name === "AbortError") {
                turn.remove();
                refs.input.value = text;
                restorePendingAttachments(detachedAttachments);
                detachedAttachments = [];
                setConversationTitle(previousTitle, { refreshRecords: false });
                setCurrentSavedBasename(previousSavedBasename, { refreshRecords: false });
                syncTextareaHeight({ animate: false });
                renderContextUsage();
                showToast("已停止本轮输出，输入已回填。", "info");
            } else {
            turn.showError(error.message || "请求失败");
            }
        } finally {
            releaseAttachmentList(detachedAttachments);
            state.isStreaming = false;
            state.streamAbortController = null;
            state.stopStreamRequested = false;
            state.streamStopBlocked = false;
            updateSendButtonState();
            syncSystemPromptToggle();
            focusComposerInput();
        }
    }

    function padConversationTimestampPart(value) {
        return String(value).padStart(2, "0");
    }

    function parseConversationTimestamp(value) {
        if (value instanceof Date) {
            return Number.isNaN(value.getTime()) ? null : value;
        }

        const text = String(value || "").trim();
        if (!text) return null;

        const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(text)
            ? text.replace(" ", "T")
            : text;
        const parsed = new Date(normalized);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    }

    function formatConversationTimestamp(value) {
        const parsed = parseConversationTimestamp(value);
        if (!parsed) return "";

        const now = new Date();
        const timeText = `${padConversationTimestampPart(parsed.getHours())}:${padConversationTimestampPart(parsed.getMinutes())}`;
        const monthDayText = `${padConversationTimestampPart(parsed.getMonth() + 1)}-${padConversationTimestampPart(parsed.getDate())}`;
        const isSameYear = parsed.getFullYear() === now.getFullYear();
        const isSameDay = isSameYear
            && parsed.getMonth() === now.getMonth()
            && parsed.getDate() === now.getDate();

        if (isSameDay) return timeText;
        if (isSameYear) return `${monthDayText} ${timeText}`;
        return `${parsed.getFullYear()}-${monthDayText} ${timeText}`;
    }

    function createTurn(userText, attachments) {
        refs.emptyState.hidden = true;
        const article = document.createElement("article");
        article.className = "turn";
        article.dataset.userRaw = userText;
        const userRow = document.createElement("div");
        userRow.className = "user-row";
        const userBubble = document.createElement("div");
        userBubble.className = "user-bubble";
        userBubble.innerHTML = `<div class="message-content message-content--live">${escapeHtml(userText).replace(/\n/g, "<br>")}</div>${renderAttachmentPreview(attachments)}`;
        const userTimestamp = document.createElement("div");
        userTimestamp.className = "user-timestamp";
        userTimestamp.textContent = formatConversationTimestamp(new Date());
        userTimestamp.hidden = !userTimestamp.textContent;
        userRow.appendChild(userBubble);
        userRow.appendChild(userTimestamp);
        const assistantBlock = document.createElement("div");
        assistantBlock.className = "assistant-block";
        assistantBlock.innerHTML = '<div class="assistant-response-row"><div class="assistant-status-indicator is-loading" aria-label="模型处理中"><span class="assistant-status-spinner" aria-hidden="true"></span><span class="assistant-status-check" aria-hidden="true"></span></div><div class="assistant-response-main"></div></div>';
        article.appendChild(userRow);
        article.appendChild(assistantBlock);
        refs.conversation.appendChild(article);
        annotateTurnEpochs();
        enhanceConversationActions();
        scrollConversationToBottom();

        const statusIndicator = assistantBlock.querySelector(".assistant-status-indicator");
        const responseMain = assistantBlock.querySelector(".assistant-response-main");
        const streamSequence = document.createElement("div");
        streamSequence.className = "assistant-stream-sequence";
        responseMain.appendChild(streamSequence);
        let activeAnswerRenderer = null;
        let activeThinkingRenderer = null;
        let activeThinkingSummaryLabel = null;
        let activeProcessHost = null;
        let activeImageHost = null;
        let activeKind = "";
        let liveThinkingStartedAt = 0;
        let liveThinkingElapsedMs = 0;
        let liveThinkingTimerId = 0;
        let statusDoneTimerId = 0;

        function formatThinkingDuration(elapsedMs) {
            return `${(Math.max(0, elapsedMs) / 1000).toFixed(1)}s`;
        }

        function getLiveThinkingElapsedMs() {
            if (!liveThinkingStartedAt) return liveThinkingElapsedMs;
            return liveThinkingElapsedMs + (performance.now() - liveThinkingStartedAt);
        }

        function setLiveThinkingSummary(text) {
            if (!activeThinkingSummaryLabel) return;
            activeThinkingSummaryLabel.textContent = text;
        }

        function refreshLiveThinkingSummary() {
            const elapsedMs = getLiveThinkingElapsedMs();
            if (!(elapsedMs > 0)) return;
            setLiveThinkingSummary(`\u601d\u8003\u4e2d ${formatThinkingDuration(elapsedMs)}`);
        }

        function startLiveThinkingTimer() {
            if (!liveThinkingStartedAt) {
                liveThinkingStartedAt = performance.now();
                if (liveThinkingTimerId) window.clearInterval(liveThinkingTimerId);
                liveThinkingTimerId = window.setInterval(refreshLiveThinkingSummary, 100);
            }
            refreshLiveThinkingSummary();
        }

        function stopLiveThinkingTimer() {
            if (liveThinkingStartedAt) {
                liveThinkingElapsedMs += performance.now() - liveThinkingStartedAt;
                liveThinkingStartedAt = 0;
            }
            if (liveThinkingTimerId) {
                window.clearInterval(liveThinkingTimerId);
                liveThinkingTimerId = 0;
            }
            if (liveThinkingElapsedMs > 0) {
                setLiveThinkingSummary(`\u5df2\u601d\u8003 ${formatThinkingDuration(liveThinkingElapsedMs)}`);
            }
        }

        function resetThinkingTimer() {
            liveThinkingStartedAt = 0;
            liveThinkingElapsedMs = 0;
            if (liveThinkingTimerId) {
                window.clearInterval(liveThinkingTimerId);
                liveThinkingTimerId = 0;
            }
        }

        function setActiveKind(nextKind) {
            if (activeKind === "thinking" && nextKind !== "thinking") stopLiveThinkingTimer();
            if (nextKind !== "answer") activeAnswerRenderer = null;
            if (nextKind !== "thinking") {
                activeThinkingRenderer = null;
                activeThinkingSummaryLabel = null;
                resetThinkingTimer();
            }
            if (nextKind !== "process") activeProcessHost = null;
            activeKind = nextKind;
        }

        function ensureAnswerRenderer() {
            if (activeKind === "answer" && activeAnswerRenderer) return activeAnswerRenderer;
            setActiveKind("answer");
            const answerNode = document.createElement("div");
            answerNode.className = "assistant-answer";
            answerNode.innerHTML = '<div class="stream-render-surface"><div class="message-content stream-render-target"></div></div>';
            streamSequence.appendChild(answerNode);
            activeAnswerRenderer = createStreamingMarkdownRenderer(answerNode.querySelector(".message-content"));
            return activeAnswerRenderer;
        }

        function ensureThinkingRenderer() {
            if (activeKind === "thinking" && activeThinkingRenderer) return activeThinkingRenderer;
            setActiveKind("thinking");
            const thinkingNode = document.createElement("details");
            thinkingNode.className = "meta-box assistant-meta-box assistant-thinking-box live-log";
            thinkingNode.open = !state.browserPreferences.collapse_thinking_by_default;
            thinkingNode.innerHTML = `<summary><div class="summary-row"><span class="summary-label">\u601d\u8003\u4e2d</span><span class="summary-caret" aria-hidden="true"></span></div></summary><div class="meta-content"><div class="stream-render-surface"><div class="message-content stream-render-target"></div></div></div>`;
            streamSequence.appendChild(thinkingNode);
            activeThinkingSummaryLabel = thinkingNode.querySelector(".summary-label");
            activeThinkingRenderer = createStreamingMarkdownRenderer(thinkingNode.querySelector(".message-content"));
            resetThinkingTimer();
            return activeThinkingRenderer;
        }

        function ensureProcessHost() {
            if (activeKind === "process" && activeProcessHost) return activeProcessHost;
            setActiveKind("process");
            activeProcessHost = document.createElement("div");
            activeProcessHost.className = "live-activity-host";
            streamSequence.appendChild(activeProcessHost);
            return activeProcessHost;
        }

        function ensureImageHost() {
            if (activeImageHost) return activeImageHost;
            activeImageHost = document.createElement("div");
            activeImageHost.className = "assistant-live-image-host";
            streamSequence.appendChild(activeImageHost);
            return activeImageHost;
        }

        function clearStatusDoneTimer() {
            if (!statusDoneTimerId) return;
            window.clearTimeout(statusDoneTimerId);
            statusDoneTimerId = 0;
        }

        function markStatusCompleted() {
            if (!statusIndicator) return;
            clearStatusDoneTimer();
            statusIndicator.classList.remove("is-fadeout");
            statusIndicator.classList.remove("is-loading");
            statusIndicator.classList.add("is-done");
            statusDoneTimerId = window.setTimeout(() => {
                statusIndicator.classList.add("is-fadeout");
                window.setTimeout(() => {
                    if (statusIndicator.isConnected) statusIndicator.remove();
                }, 320);
            }, 1500);
        }

        function hideStatusImmediately() {
            if (!statusIndicator) return;
            clearStatusDoneTimer();
            statusIndicator.classList.add("is-fadeout");
            window.setTimeout(() => {
                if (statusIndicator.isConnected) statusIndicator.remove();
            }, 320);
        }

        return {
            remove() {
                stopLiveThinkingTimer();
                clearStatusDoneTimer();
                if (article.isConnected) article.remove();
                annotateTurnEpochs();
                enhanceConversationActions();
                refreshTurnNavigator();
                syncScrollBottomButtonVisibility();
            },
            updateLiveActivity(html) {
                const host = ensureProcessHost();
                host.innerHTML = html || "";
                host.hidden = !html;
                applyOutputPreferenceState(host);
                scrollConversationToBottom();
            },
            updateLiveImages(html) {
                const host = ensureImageHost();
                host.innerHTML = html || "";
                host.hidden = !html;
                hydrateAssistantReferenceImages(host);
                scrollConversationToBottom();
            },
            appendWarning(text) {
                const node = document.createElement("div");
                node.className = "warning-banner";
                node.textContent = text;
                responseMain.insertBefore(node, responseMain.firstChild);
                scrollConversationToBottom();
            },
            appendAnswer(text) {
                if (!text) return;
                const renderer = ensureAnswerRenderer();
                renderer.append(text);
                scrollConversationToBottom();
            },
            appendThinking(text) {
                if (!text) return;
                const renderer = ensureThinkingRenderer();
                startLiveThinkingTimer();
                renderer.append(text);
                scrollConversationToBottom();
            },
            appendSystem(text) {
                if (text) scrollConversationToBottom();
            },
            finalize(event) {
                stopLiveThinkingTimer();
                userBubble.innerHTML = event.user_html || userBubble.innerHTML;
                if (typeof event.user_timestamp_display === "string") {
                    const nextTimestamp = event.user_timestamp_display.trim();
                    userTimestamp.textContent = nextTimestamp;
                    userTimestamp.hidden = !nextTimestamp;
                }
                responseMain.innerHTML = event.assistant_blocks_html || '<div class="assistant-answer"><div class="message-content"></div></div>';
                renderMathInContent(article);
                hydrateAssistantReferenceImages(article);
                if (typeof event.assistant_answer_text === "string") {
                    article.dataset.assistantRaw = event.assistant_answer_text;
                }
                if (Number(event.epoch) > 0) {
                    article.dataset.turnEpoch = String(event.epoch);
                }
                if (Array.isArray(event.context_messages)) {
                    setContextMessages(event.context_messages);
                }
                const streamedTotalTokens = event.total_tokens ?? event.token_count;
                if (streamedTotalTokens !== undefined) {
                    setTotalConversationTokens(streamedTotalTokens);
                }
                if (typeof event.latest_assistant_thinking === "string") {
                    setLatestAssistantThinking(event.latest_assistant_thinking);
                }
                applyOutputPreferenceState(article, { forceCollapse: state.browserPreferences.auto_collapse_output_meta });
                markStatusCompleted();
                enhanceConversationActions();
                if (event.title) setConversationTitle(event.title, { refreshRecords: false });
                if (event.saved_basename) setCurrentSavedBasename(event.saved_basename, { refreshRecords: false });
                renderRecordsPanel();
                if (event.autosave_error) {
                    showToast("自动保存失败：" + event.autosave_error, "error");
                } else if (event.saved_basename) {
                    void refreshRecordsPanel({ silent: true });
                }
                scrollConversationToBottom();
            },
            showError(text) {
                stopLiveThinkingTimer();
                hideStatusImmediately();
                this.appendWarning(text);
            },
        };
    }

    function handleStreamEvent(turn, event) {
        if ("tool_call_active" in event) setStreamStopBlocked(!!event.tool_call_active);
        if ("assistant_live_meta_html" in event) turn.updateLiveActivity(event.assistant_live_meta_html || "");
        if ("assistant_live_images_html" in event) turn.updateLiveImages(event.assistant_live_images_html || "");
        if (event.type === "title" && event.title) {
            setConversationTitle(event.title);
        }
        if (event.type === "content") turn.appendAnswer(event.content || "");
        if (event.type === "thinking") turn.appendThinking(event.content || "");
        if (event.type === "system") turn.appendSystem(event.content || "");
        if (event.type === "warning") turn.appendWarning(event.content || "");
        if (event.type === "error") {
            if (typeof turn.restoreContextEstimate === "function") turn.restoreContextEstimate();
            turn.showError(event.content || "请求失败");
        }
        if (event.type === "done") turn.finalize(event);
    }

    function renderAttachmentPreview(attachments) {
        if (!attachments.length) return "";
        const chips = attachments.map((item) => `<span class="chip">${escapeHtml(item.file.name)}</span>`).join("");
        return `<div class="browser-attachment-meta"><div class="meta-title">附件</div><div class="chip-list">${chips}</div></div>`;
    }

    function scrollConversationToBottom() {
        window.requestAnimationFrame(() => {
            if (!state.followStreaming) return;
            scrollPageToBottom({ behavior: "auto" });
        });
    }

    function updateFollowStreamingState() {
        const atBottom = isAtPageBottom();
        if (state.isStreaming) state.followStreaming = atBottom;
        syncScrollBottomButtonVisibility(atBottom);
    }

    function isAtPageBottom() {
        const scrollTop = window.scrollY || window.pageYOffset || 0;
        const viewportBottom = scrollTop + window.innerHeight;
        const documentHeight = Math.max(
            document.documentElement.scrollHeight,
            document.body ? document.body.scrollHeight : 0
        );
        const threshold = 3;
        return documentHeight - viewportBottom <= threshold;
    }

    function scrollPageToBottom(options = {}) {
        const behavior = options.behavior === "smooth" ? "smooth" : "auto";
        window.scrollTo({ top: document.documentElement.scrollHeight, behavior });
    }

    function syncScrollBottomButtonVisibility(cachedAtBottom) {
        if (!refs.scrollBottomButton) return;
        const atBottom = typeof cachedAtBottom === "boolean" ? cachedAtBottom : isAtPageBottom();
        refs.scrollBottomButton.hidden = atBottom;
        refs.scrollBottomButton.classList.toggle("is-visible", !atBottom);
        syncScrollBottomButtonLayout();
    }

    function syncScrollBottomButtonLayout() {
        if (!refs.scrollBottomButton) return;
        const button = refs.scrollBottomButton;
        const buttonSize = 34;
        const edgeGap = 10;
        const navGap = 10;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;

        const maxTop = Math.max(edgeGap, viewportHeight - buttonSize - edgeGap);

        let rightPx = clampNumber(Math.round(viewportWidth * 0.024), edgeGap, 24);
        let targetTop = Math.max(edgeGap, maxTop);

        if (refs.turnMap && !refs.turnMap.hidden) {
            const turnMapRect = refs.turnMap.getBoundingClientRect();
            rightPx = Math.max(edgeGap, Math.round(viewportWidth - turnMapRect.right));

            const belowTop = Math.round(turnMapRect.bottom + navGap);
            const aboveTop = Math.round(turnMapRect.top - navGap - buttonSize);
            if (belowTop <= maxTop) {
                targetTop = Math.max(edgeGap, belowTop);
            } else if (aboveTop >= edgeGap) {
                targetTop = aboveTop;
            } else {
                targetTop = maxTop;
            }
        }

        targetTop = clampNumber(targetTop, edgeGap, Math.max(edgeGap, maxTop));
        const bottomPx = Math.max(edgeGap, Math.round(viewportHeight - targetTop - buttonSize));
        button.style.setProperty("--scroll-bottom-right", `${rightPx}px`);
        button.style.setProperty("--scroll-bottom-bottom", `${bottomPx}px`);
    }

    function clampNumber(value, min, max) {
        if (!Number.isFinite(value)) return min;
        return Math.min(max, Math.max(min, value));
    }

    function normalizeSystemText(text) {
        return String(text || "").replace(/\u001b\[[0-9;]*m/g, "").trim();
    }

    function createStreamingMarkdownRenderer(contentEl) {
        let buffer = "";
        let rafId = 0;
        let lastHtml = "";

        function flush() {
            rafId = 0;
            const html = renderMarkdownToHtml(buffer);
            if (html === lastHtml) return;
            patchStreamingContent(contentEl, html);
            lastHtml = html;
        }

        return {
            append(text) {
                buffer += text;
                if (rafId) return;
                rafId = window.requestAnimationFrame(flush);
            },
            set(text) {
                buffer = text;
                if (rafId) {
                    window.cancelAnimationFrame(rafId);
                    rafId = 0;
                }
                flush();
            },
            hasContent() {
                return buffer.trim().length > 0;
            },
        };
    }

    function patchStreamingContent(contentEl, html) {
        if (!contentEl) return;
        normalizeStreamingArtifacts(contentEl);
        const template = document.createElement("template");
        template.innerHTML = html;
        patchChildNodes(contentEl, Array.from(template.content.childNodes));
        renderMathInContent(contentEl);
    }

    function renderMathInContent(root) {
        if (!root || typeof window.renderMathInElement !== "function") return;
        window.renderMathInElement(root, {
            delimiters: [
                { left: "$$", right: "$$", display: true },
                { left: "\\[", right: "\\]", display: true },
                { left: "\\(", right: "\\)", display: false },
                { left: "$", right: "$", display: false },
            ],
            throwOnError: false,
            strict: "ignore",
            ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code"],
        });
    }

    function armStreamFade(node) {
        if (!node || node.nodeType !== Node.ELEMENT_NODE) return;
        node.classList.remove("stream-fade-burst");
        void node.offsetWidth;
        node.classList.add("stream-fade-burst");
        node.addEventListener("animationend", () => {
            node.classList.remove("stream-fade-burst");
        }, { once: true });
    }

    function normalizeStreamingArtifacts(root) {
        if (!root) return;
        root.querySelectorAll("[data-stream-inline-fade='1']").forEach((node) => {
            const textNode = document.createTextNode(node.textContent || "");
            node.replaceWith(textNode);
        });
        root.querySelectorAll(".stream-fade-burst").forEach((node) => {
            node.classList.remove("stream-fade-burst");
        });
        root.normalize();
    }

    function patchChildNodes(parent, nextNodes) {
        const currentNodes = Array.from(parent.childNodes);
        let index = 0;

        while (index < nextNodes.length || index < currentNodes.length) {
            const currentNode = currentNodes[index] || null;
            const nextNode = nextNodes[index] || null;

            if (!nextNode) {
                if (currentNode) {
                    currentNode.remove();
                    currentNodes.splice(index, 1);
                    continue;
                }
                break;
            }

            if (!currentNode) {
                const insertedNode = createPatchedNode(nextNode, true);
                if (insertedNode) {
                    parent.appendChild(insertedNode);
                    currentNodes.push(insertedNode);
                }
                index += 1;
                continue;
            }

            if (canPatchNode(currentNode, nextNode)) {
                patchNode(currentNode, nextNode);
                index += 1;
                continue;
            }

            const lookaheadCurrent = currentNodes[index + 1] || null;
            const lookaheadNext = nextNodes[index + 1] || null;

            if (lookaheadCurrent && canPatchNode(lookaheadCurrent, nextNode)) {
                const insertedNode = createPatchedNode(nextNode, true);
                if (insertedNode) {
                    parent.insertBefore(insertedNode, currentNode);
                    currentNodes.splice(index, 0, insertedNode);
                }
                index += 1;
                continue;
            }

            if (lookaheadNext && canPatchNode(currentNode, lookaheadNext)) {
                currentNode.remove();
                currentNodes.splice(index, 1);
                continue;
            }

            const replacementNode = createPatchedNode(nextNode, false);
            if (replacementNode) {
                parent.replaceChild(replacementNode, currentNode);
                currentNodes[index] = replacementNode;
            } else {
                currentNode.remove();
                currentNodes.splice(index, 1);
                continue;
            }
            index += 1;
        }
    }

    function canPatchNode(currentNode, nextNode) {
        if (!currentNode || !nextNode) return false;
        if (currentNode.nodeType !== nextNode.nodeType) return false;
        if (currentNode.nodeType === Node.TEXT_NODE) return true;
        if (currentNode.nodeType === Node.ELEMENT_NODE) {
            return currentNode.tagName === nextNode.tagName;
        }
        return false;
    }

    function patchNode(currentNode, nextNode) {
        if (currentNode.nodeType === Node.TEXT_NODE && nextNode.nodeType === Node.TEXT_NODE) {
            patchTextNode(currentNode, nextNode.textContent || "");
            return;
        }
        if (currentNode.nodeType === Node.ELEMENT_NODE && nextNode.nodeType === Node.ELEMENT_NODE) {
            patchElementNode(currentNode, nextNode);
        }
    }

    function patchTextNode(currentNode, nextText) {
        const currentText = currentNode.textContent || "";
        if (currentText === nextText) return;
        currentNode.textContent = nextText;
        if (nextText.startsWith(currentText) && nextText.length > currentText.length) {
            animateTextNodeSuffix(currentNode, currentText.length, nextText.length);
        }
    }

    function patchElementNode(currentNode, nextNode) {
        patchElementAttributes(currentNode, nextNode);
        patchChildNodes(currentNode, Array.from(nextNode.childNodes));
    }

    function patchElementAttributes(currentNode, nextNode) {
        Array.from(currentNode.attributes).forEach((attr) => {
            if (!nextNode.hasAttribute(attr.name)) {
                currentNode.removeAttribute(attr.name);
            }
        });
        Array.from(nextNode.attributes).forEach((attr) => {
            const nextValue = attr.name === "class"
                ? stripStreamFadeClass(attr.value)
                : attr.value;
            const currentValue = attr.name === "class"
                ? stripStreamFadeClass(currentNode.getAttribute(attr.name) || "")
                : (currentNode.getAttribute(attr.name) || "");
            if (currentValue !== nextValue) {
                currentNode.setAttribute(attr.name, nextValue);
            }
        });
    }

    function stripStreamFadeClass(value) {
        return String(value || "")
            .split(/\s+/)
            .filter((token) => token && token !== "stream-fade-burst")
            .join(" ");
    }

    function createPatchedNode(node, animate) {
        if (!node) return null;
        if (node.nodeType === Node.TEXT_NODE) {
            const textValue = node.textContent || "";
            if (!animate || !textValue) return document.createTextNode(textValue);
            const span = document.createElement("span");
            span.dataset.streamInlineFade = "1";
            span.textContent = textValue;
            armStreamFade(span);
            span.addEventListener("animationend", () => {
                if (!span.isConnected) return;
                const parent = span.parentNode;
                span.replaceWith(document.createTextNode(span.textContent || ""));
                if (parent) parent.normalize();
            }, { once: true });
            return span;
        }
        const clone = node.cloneNode(true);
        if (animate && clone.nodeType === Node.ELEMENT_NODE) {
            armStreamFade(clone);
        }
        return clone;
    }

    function animateTextNodeSuffix(textNode, startOffset, endOffset) {
        if (!textNode || textNode.nodeType !== Node.TEXT_NODE) return;
        if (startOffset < 0 || endOffset <= startOffset) return;
        const range = document.createRange();
        range.setStart(textNode, startOffset);
        range.setEnd(textNode, endOffset);
        const span = document.createElement("span");
        span.dataset.streamInlineFade = "1";
        try {
            range.surroundContents(span);
        } catch (error) {
            return;
        }
        armStreamFade(span);
        span.addEventListener("animationend", () => {
            if (!span.isConnected) return;
            const parent = span.parentNode;
            span.replaceWith(document.createTextNode(span.textContent || ""));
            if (parent) parent.normalize();
        }, { once: true });
    }

    function renderMarkdownToHtml(text) {
        const placeholders = {};
        let source = stabilizeStreamingMarkdown(String(text ?? "").replace(/\r\n/g, "\n"));

        source = source.replace(/```([^\n`]*)\n([\s\S]*?)```/g, (_, language, code) => {
            const key = `__CODE_BLOCK_${Object.keys(placeholders).length}__`;
            const lang = escapeHtml((language || "").trim());
            const classAttr = lang ? ` class="language-${lang}"` : "";
            placeholders[key] = `<pre><code${classAttr}>${escapeHtml(code)}</code></pre>`;
            return key;
        });

        source = source.replace(/\\\[([\s\S]*?)\\\]/g, (_, expression) => {
            const key = `__MATH_BLOCK_${Object.keys(placeholders).length}__`;
            placeholders[key] = renderMathExpression(expression, true);
            return key;
        });
        source = source.replace(/\$\$([\s\S]*?)\$\$/g, (_, expression) => {
            const key = `__MATH_BLOCK_${Object.keys(placeholders).length}__`;
            placeholders[key] = renderMathExpression(expression, true);
            return key;
        });
        source = source.replace(/\\\(([\s\S]*?)\\\)/g, (_, expression) => {
            const key = `__MATH_BLOCK_${Object.keys(placeholders).length}__`;
            placeholders[key] = renderMathExpression(expression, false);
            return key;
        });
        source = source.replace(/(^|[^\\])\$(?!\$)([^\n$]*?)\$(?!\$)/g, (_, prefix, expression) => {
            const key = `__MATH_BLOCK_${Object.keys(placeholders).length}__`;
            placeholders[key] = renderMathExpression(expression, false);
            return `${prefix}${key}`;
        });

        source = escapeHtml(source);
        source = source.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, src) => renderInlineImage(alt, src));
        source = source.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, href) => {
            return `<a href="${normalizeHref(unescapeHtml(href))}" target="_blank" rel="noreferrer">${label}</a>`;
        });
        source = source.replace(/`([^`]+)`/g, "<code>$1</code>");
        source = source.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
        source = source.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>");

        const lines = source.split("\n");
        const htmlParts = [];
        let paragraphLines = [];
        let listItems = [];
        let listTag = null;
        let blockquoteLines = [];
        let index = 0;

        function flushParagraph() {
            if (!paragraphLines.length) return;
            htmlParts.push(`<p>${paragraphLines.join("<br>")}</p>`);
            paragraphLines = [];
        }

        function flushList() {
            if (listItems.length && listTag) {
                htmlParts.push(`<${listTag}>${listItems.join("")}</${listTag}>`);
            }
            listItems = [];
            listTag = null;
        }

        function flushBlockquote() {
            if (!blockquoteLines.length) return;
            htmlParts.push(`<blockquote>${blockquoteLines.join("<br>")}</blockquote>`);
            blockquoteLines = [];
        }

        function getNextListTag(startIndex) {
            for (let nextIndex = startIndex; nextIndex < lines.length; nextIndex += 1) {
                const nextStripped = lines[nextIndex].trim();
                if (!nextStripped) continue;
                if (placeholders[nextStripped]) return null;
                if (/^[-*]\s+(.*)$/.test(nextStripped)) return "ul";
                if (/^\d+\.\s+(.*)$/.test(nextStripped)) return "ol";
                return null;
            }
            return null;
        }

        while (index < lines.length) {
            const line = lines[index];
            const stripped = line.trim();
            if (!stripped) {
                const nextListTag = getNextListTag(index + 1);
                if (listTag && nextListTag === listTag) {
                    index += 1;
                    continue;
                }
                flushParagraph();
                flushList();
                flushBlockquote();
                index += 1;
                continue;
            }

            if (placeholders[stripped]) {
                flushParagraph();
                flushList();
                flushBlockquote();
                htmlParts.push(placeholders[stripped]);
                index += 1;
                continue;
            }

            if (index + 1 < lines.length) {
                const headerCandidate = lines[index];
                const separatorCandidate = lines[index + 1];
                if (looksLikeMarkdownTable(headerCandidate, separatorCandidate)) {
                    flushParagraph();
                    flushList();
                    flushBlockquote();

                    const tableRows = [headerCandidate, separatorCandidate];
                    let rowIndex = index + 2;
                    while (rowIndex < lines.length) {
                        const rowLine = lines[rowIndex];
                        const rowStripped = rowLine.trim();
                        if (!rowStripped) break;
                        if (placeholders[rowStripped]) break;
                        if (!isMarkdownTableRow(rowLine)) break;
                        tableRows.push(rowLine);
                        rowIndex += 1;
                    }

                    htmlParts.push(renderMarkdownTable(tableRows));
                    index = rowIndex;
                    continue;
                }
            }

            if (isMarkdownThematicBreak(stripped)) {
                flushParagraph();
                flushList();
                flushBlockquote();
                htmlParts.push("<hr>");
                index += 1;
                continue;
            }

            const headingMatch = stripped.match(/^(#{1,4})\s+(.*)$/);
            if (headingMatch) {
                flushParagraph();
                flushList();
                flushBlockquote();
                const level = headingMatch[1].length;
                htmlParts.push(`<h${level}>${headingMatch[2]}</h${level}>`);
                index += 1;
                continue;
            }

            const quoteMatch = stripped.match(/^&gt;\s?(.*)$/);
            if (quoteMatch) {
                flushParagraph();
                flushList();
                blockquoteLines.push(quoteMatch[1]);
                index += 1;
                continue;
            }

            flushBlockquote();

            const ulMatch = stripped.match(/^[-*]\s+(.*)$/);
            const olMatch = stripped.match(/^\d+\.\s+(.*)$/);
            if (ulMatch || olMatch) {
                flushParagraph();
                const tag = ulMatch ? "ul" : "ol";
                const item = ulMatch ? ulMatch[1] : olMatch[1];
                if (listTag && listTag !== tag) flushList();
                listTag = tag;
                listItems.push(`<li>${item}</li>`);
                index += 1;
                continue;
            }

            flushList();
            paragraphLines.push(stripped);
            index += 1;
        }

        flushParagraph();
        flushList();
        flushBlockquote();

        let rendered = htmlParts.join("");
        for (const [key, value] of Object.entries(placeholders)) {
            rendered = rendered.replaceAll(key, value);
        }
        return rendered;
    }

    function splitMarkdownTableRow(line) {
        let raw = String(line ?? "").trim();
        if (raw.startsWith("|")) raw = raw.slice(1);
        if (raw.endsWith("|")) raw = raw.slice(0, -1);
        return raw.split("|").map((cell) => cell.trim());
    }

    function isMarkdownTableRow(line) {
        const row = String(line ?? "").trim();
        return row.includes("|") && !row.startsWith("#") && !row.startsWith("&gt;");
    }

    function isMarkdownThematicBreak(line) {
        const stripped = String(line ?? "").trim();
        return /^([-*_])(?:\s*\1){2,}$/.test(stripped);
    }

    function looksLikeMarkdownTable(headerLine, separatorLine) {
        if (!isMarkdownTableRow(headerLine)) return false;
        const sepCells = splitMarkdownTableRow(separatorLine);
        if (!sepCells.length) return false;
        return sepCells.every((cell) => /^:?-{3,}:?$/.test(cell));
    }

    function renderMarkdownTable(lines) {
        const headerCells = splitMarkdownTableRow(lines[0] || "");
        const alignCells = splitMarkdownTableRow(lines[1] || "");
        const bodyLines = lines.slice(2);
        const bodyCellWidths = bodyLines.map((row) => splitMarkdownTableRow(row).length);
        const colCount = Math.max(headerCells.length, alignCells.length, ...bodyCellWidths, 1);

        function resolveAlign(cell) {
            const value = String(cell ?? "").trim();
            if (value.startsWith(":") && value.endsWith(":")) return "center";
            if (value.endsWith(":")) return "right";
            return "left";
        }

        const aligns = Array.from({ length: colCount }, (_, idx) => resolveAlign(alignCells[idx] || ""));

        function cellsToHtml(cells, tagName) {
            const normalized = cells.slice(0, colCount);
            while (normalized.length < colCount) normalized.push("");
            return normalized.map((cell, idx) => `<${tagName} style="text-align:${aligns[idx] || "left"};">${cell}</${tagName}>`).join("");
        }

        const headHtml = `<thead><tr>${cellsToHtml(headerCells, "th")}</tr></thead>`;
        let bodyHtml = "";
        if (bodyLines.length) {
            const rows = bodyLines.map((row) => `<tr>${cellsToHtml(splitMarkdownTableRow(row), "td")}</tr>`).join("");
            bodyHtml = `<tbody>${rows}</tbody>`;
        }
        return `<table>${headHtml}${bodyHtml}</table>`;
    }

    function renderMathExpression(expression, displayMode) {
        const source = String(expression ?? "").trim();
        if (!source) return "";
        if (!window.katex || typeof window.katex.renderToString !== "function") {
            return escapeHtml(source);
        }
        try {
            return window.katex.renderToString(source, {
                displayMode,
                throwOnError: false,
                strict: "ignore",
            });
        } catch (error) {
            return escapeHtml(source);
        }
    }

    function stabilizeStreamingMarkdown(source) {
        const fenceMatches = source.match(/```/g);
        if (fenceMatches && fenceMatches.length % 2 === 1) {
            source += "\n```";
        }
        return source;
    }

    function renderInlineImage(alt, src) {
        const sourceText = unescapeHtml(src);
        const realSrc = normalizeHref(sourceText);
        const altText = escapeHtml(unescapeHtml(alt));
        const localPathMatch = /^[a-zA-Z]:[\\/]/.test(sourceText.trim()) ? sourceText.trim() : "";
        const localPathAttr = localPathMatch ? ` data-local-image-path="${escapeAttr(localPathMatch)}"` : "";
        return `<figure class="image-card message-image-card"${localPathAttr}><a class="image-card-link" href="${realSrc}" target="_blank" rel="noreferrer"><img class="zoomable-image" src="${realSrc}" alt="${altText}"></a></figure>`;
    }

    function normalizeHref(href) {
        const value = String(href ?? "").trim();
        if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(value)) {
            return escapeAttr(value);
        }
        return escapeAttr(value);
    }

    function unescapeHtml(value) {
        const textarea = document.createElement("textarea");
        textarea.innerHTML = String(value ?? "");
        return textarea.value;
    }

    function showToast(message, kind) {
        const node = document.createElement("div");
        node.className = "warning-banner";
        node.style.position = "fixed";
        node.style.right = "20px";
        node.style.bottom = "20px";
        node.style.maxWidth = "420px";
        node.style.zIndex = "100";
        if (kind === "success") {
            node.style.background = "#f1f9ef";
            node.style.borderColor = "#b9d9b1";
            node.style.color = "#355a2c";
        }
        if (kind === "error") {
            node.style.background = "#fff0ee";
            node.style.borderColor = "#e4b5ad";
            node.style.color = "#8c3327";
        }
        node.textContent = message;
        document.body.appendChild(node);
        window.setTimeout(() => node.remove(), 2600);
    }

    function escapeHtml(value) {
        return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    }
    function escapeAttr(value) { return escapeHtml(value).replace(/`/g, "&#96;"); }
    function cloneValue(value) { return value && typeof value === "object" ? JSON.parse(JSON.stringify(value)) : value; }
    function randomId() { return window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : "id_" + Math.random().toString(36).slice(2); }
})();
