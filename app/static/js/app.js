/**
 * Ollama Desktop Chatbot - Frontend Application Controller
 * Inspired by Antigravity and Cursor
 */

(function () {
  'use strict';

  // State
  let currentConversationId = null;
  let conversations = [];
  let attachedFiles = [];
  let webSearchEnabled = false;
  let appendChatEnabled = true;
  let agentModeEnabled = false;
  let savedModelSelection = null;
  let hasInitializedModelSelection = false;
  let currentAgentTaskId = null;
  let isGenerating = false;
  let activeAbortController = null;
  let sessionTokens = 0;
  let isDownloadingModel = false;
  let currentDownloadingModel = null;
  let modelSearchItems = [];
  let modelSearchActiveIndex = -1;
  let installedModelsCache = [];
  let recommendedModelsCache = [];
  let modelLibraryQuery = '';
  let permissionQueue = [];
  let activePermissionRequest = null;
  let permissionResponding = false;

  // Antigravity Project State
  let currentProjectId = null;
  let currentProjectPath = null;
  let currentProjectName = null;
  let projectsList = [];
  let modifiedFilesMap = new Map(); // path -> { action: 'created'|'modified'|'deleted', tool: string, timestamp: number }

  // DOM Elements
  const btnNewChat = document.getElementById('btnNewChat');
  const conversationsList = document.getElementById('conversationsList');
  const searchHistoryInput = document.getElementById('searchHistoryInput');
  const modelSelector = document.getElementById('modelSelector');
  const modelSelectorWrapper = document.getElementById('modelSelectorWrapper');
  const modelSelectorButton = document.getElementById('modelSelectorButton');
  const modelSelectorLabel = document.getElementById('modelSelectorLabel');
  const modelSearchPopover = document.getElementById('modelSearchPopover');
  const modelSearchInput = document.getElementById('modelSearchInput');
  const modelSearchClear = document.getElementById('modelSearchClear');
  const modelSearchSummary = document.getElementById('modelSearchSummary');
  const modelSearchResults = document.getElementById('modelSearchResults');
  const optGroupOllama = document.getElementById('optGroupOllama');
  const optGroupOnline = document.getElementById('optGroupOnline');
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const sessionTokensCount = document.getElementById('sessionTokensCount');
  const messagesContainer = document.getElementById('messagesContainer');
  const messageInput = document.getElementById('messageInput');
  const btnSendMessage = document.getElementById('btnSendMessage');
  const btnPlusAttach = document.getElementById('btnPlusAttach');
  const filePickerInput = document.getElementById('filePickerInput');
  const attachmentsTray = document.getElementById('attachmentsTray');
  const btnToggleWebSearch = document.getElementById('btnToggleWebSearch');
  const btnToggleAppendChat = document.getElementById('btnToggleAppendChat');
  const btnToggleAgentMode = document.getElementById('btnToggleAgentMode');
  const btnExportChat = document.getElementById('btnExportChat');

  // Project DOM Elements
  const btnProjectSelector = document.getElementById('btnProjectSelector');
  const activeProjectLabel = document.getElementById('activeProjectLabel');
  const projectDropdownMenu = document.getElementById('projectDropdownMenu');
  const btnDropdownGlobal = document.getElementById('btnDropdownGlobal');
  const btnDropdownOpenProject = document.getElementById('btnDropdownOpenProject');
  const btnDropdownProjectDetails = document.getElementById('btnDropdownProjectDetails');
  const recentProjectsContainer = document.getElementById('recentProjectsContainer');

  // Project Modal DOM Elements
  const projectModal = document.getElementById('projectModal');
  const projectModalTitle = document.getElementById('projectModalTitle');
  const projectPathInput = document.getElementById('projectPathInput');
  const projectNameInput = document.getElementById('projectNameInput');
  const projectInstructionsInput = document.getElementById('projectInstructionsInput');
  const projectOverviewSection = document.getElementById('projectOverviewSection');
  const projStatFiles = document.getElementById('projStatFiles');
  const projStatDirs = document.getElementById('projStatDirs');
  const projFileTree = document.getElementById('projFileTree');
  const btnCloseProjectModal = document.getElementById('btnCloseProjectModal');
  const btnCancelProjectModal = document.getElementById('btnCancelProjectModal');
  const btnConfirmOpenProject = document.getElementById('btnConfirmOpenProject');

  // Changes Review DOM Elements
  const btnReviewChanges = document.getElementById('btnReviewChanges');
  const modifiedFilesCount = document.getElementById('modifiedFilesCount');
  const changesReviewModal = document.getElementById('changesReviewModal');
  const btnCloseChangesModal = document.getElementById('btnCloseChangesModal');
  const btnDismissChanges = document.getElementById('btnDismissChanges');
  const btnClearChanges = document.getElementById('btnClearChanges');
  const modifiedFilesList = document.getElementById('modifiedFilesList');
  const diffViewerWrapper = document.getElementById('diffViewerWrapper');
  const diffViewerFileName = document.getElementById('diffViewerFileName');
  const diffViewerCode = document.getElementById('diffViewerCode');

  // Modals
  const settingsModal = document.getElementById('settingsModal');
  const btnOpenSettings = document.getElementById('btnOpenSettings');
  const btnCloseSettings = document.getElementById('btnCloseSettings');
  const btnCancelSettings = document.getElementById('btnCancelSettings');
  const btnSaveSettings = document.getElementById('btnSaveSettings');

  const analyticsModal = document.getElementById('analyticsModal');
  const btnOpenAnalytics = document.getElementById('btnOpenAnalytics');
  const btnCloseAnalytics = document.getElementById('btnCloseAnalytics');
  const btnDismissAnalytics = document.getElementById('btnDismissAnalytics');

  // Settings inputs
  const settingOllamaUrl = document.getElementById('settingOllamaUrl');
  const settingOpenAiKey = document.getElementById('settingOpenAiKey');
  const settingAnthropicKey = document.getElementById('settingAnthropicKey');
  const settingGeminiKey = document.getElementById('settingGeminiKey');
  const settingGroqKey = document.getElementById('settingGroqKey');
  const settingOpenRouterKey = document.getElementById('settingOpenRouterKey');
  const settingVisionModel = document.getElementById('settingVisionModel');
  const settingKeepAlive = document.getElementById('settingKeepAlive');
  const settingAgentWorkspace = document.getElementById('settingAgentWorkspace');
  const settingTokenBudget = document.getElementById('settingTokenBudget');
  const settingAgentPermissionMode = document.getElementById('settingAgentPermissionMode');

  // Agent permission approval modal
  const permissionModal = document.getElementById('permissionModal');
  const permissionSubtitle = document.getElementById('permissionSubtitle');
  const permissionToolName = document.getElementById('permissionToolName');
  const permissionTitle = document.getElementById('permissionTitle');
  const permissionDetail = document.getElementById('permissionDetail');
  const permissionRisk = document.getElementById('permissionRisk');
  const permissionPreviewWrapper = document.getElementById('permissionPreviewWrapper');
  const permissionPreviewLabel = document.getElementById('permissionPreviewLabel');
  const permissionPreview = document.getElementById('permissionPreview');
  const btnDenyPermission = document.getElementById('btnDenyPermission');
  const btnAlwaysAllowPermission = document.getElementById('btnAlwaysAllowPermission');
  const btnAllowPermission = document.getElementById('btnAllowPermission');

  // Local Model Library
  const modelsModal = document.getElementById('modelsModal');
  const btnOpenModels = document.getElementById('btnOpenModels');
  const btnCloseModels = document.getElementById('btnCloseModels');
  const btnDismissModels = document.getElementById('btnDismissModels');
  const btnRefreshModels = document.getElementById('btnRefreshModels');
  const customModelInput = document.getElementById('customModelInput');
  const btnPullCustomModel = document.getElementById('btnPullCustomModel');
  const installedModelsList = document.getElementById('installedModelsList');
  const recommendedModelsList = document.getElementById('recommendedModelsList');
  const modelLibrarySearchInput = document.getElementById('modelLibrarySearchInput');
  const modelLibrarySearchClear = document.getElementById('modelLibrarySearchClear');
  const modelLibrarySearchStatus = document.getElementById('modelLibrarySearchStatus');
  const installedModelsCount = document.getElementById('installedModelsCount');
  const recommendedModelsCount = document.getElementById('recommendedModelsCount');
  const modelDownloadStatus = document.getElementById('modelDownloadStatus');
  const modelDownloadLabel = document.getElementById('modelDownloadLabel');
  const modelDownloadPercent = document.getElementById('modelDownloadPercent');
  const modelDownloadProgressFill = document.getElementById('modelDownloadProgressFill');
  const modelDownloadDetail = document.getElementById('modelDownloadDetail');
  const btnCancelDownload = document.getElementById('btnCancelDownload');

  // Analytics displays
  const statTotalTokens = document.getElementById('statTotalTokens');
  const statEstimatedCost = document.getElementById('statEstimatedCost');
  const statPromptTokens = document.getElementById('statPromptTokens');
  const statCompletionTokens = document.getElementById('statCompletionTokens');
  const budgetUsageLabel = document.getElementById('budgetUsageLabel');
  const budgetProgressFill = document.getElementById('budgetProgressFill');
  const budgetRemainingLabel = document.getElementById('budgetRemainingLabel');

  // Simple offline markdown fallback if marked.js CDN is unavailable
  function renderMarkdown(rawText) {
    if (window.marked && typeof window.marked.parse === 'function') {
      try {
        return window.marked.parse(rawText);
      } catch (e) {
        console.warn('Marked parsing error:', e);
      }
    }
    // Fallback simple parser
    let escaped = rawText
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks
    escaped = escaped.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    // Inline code
    escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Newlines to br
    escaped = escaped.replace(/\n/g, '<br>');
    return escaped;
  }

  // Highlight syntax inside a DOM element
  function highlightCodeBlocks(container) {
    if (window.hljs) {
      container.querySelectorAll('pre code').forEach((block) => {
        window.hljs.highlightElement(block);
        // Add copy button if not exists
        const pre = block.parentElement;
        if (!pre.querySelector('.copy-code-btn')) {
          const btn = document.createElement('button');
          btn.className = 'copy-code-btn';
          btn.textContent = 'Copy';
          btn.addEventListener('click', () => {
            navigator.clipboard.writeText(block.innerText);
            btn.textContent = 'Copied!';
            setTimeout(() => (btn.textContent = 'Copy'), 2000);
          });
          pre.appendChild(btn);
        }
      });
    }
  }

  // --------------------------------------------------------------------------
  // Initialization
  // --------------------------------------------------------------------------
  // Initialization
  // --------------------------------------------------------------------------
  async function init() {
    setupEventListeners();
    await loadSettings();
    await loadModels();
    await loadActiveProjectAndProjects();
    await updateAnalyticsUI();
  }

  function setupEventListeners() {
    // New Chat
    btnNewChat.addEventListener('click', () => createNewChat());

    // Search History
    searchHistoryInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      renderConversationList(q);
    });

    // Send Message on Enter (Shift+Enter for newline)
    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto resize textarea
    messageInput.addEventListener('input', () => {
      messageInput.style.height = 'auto';
      messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + 'px';
    });

    // Send Button click
    btnSendMessage.addEventListener('click', () => {
      if (isGenerating) {
        stopGeneration();
      } else {
        sendMessage();
      }
    });

    // Plus Attach Button
    btnPlusAttach.addEventListener('click', () => filePickerInput.click());
    filePickerInput.addEventListener('change', handleFileUpload);

    // Web Search Toggle
    btnToggleWebSearch.addEventListener('click', () => {
      webSearchEnabled = !webSearchEnabled;
      btnToggleWebSearch.classList.toggle('active', webSearchEnabled);
    });

    // Append Chat Memory Toggle
    if (btnToggleAppendChat) {
      btnToggleAppendChat.addEventListener('click', () => {
        appendChatEnabled = !appendChatEnabled;
        btnToggleAppendChat.classList.toggle('active', appendChatEnabled);
      });
    }

    // Agent Mode Toggle
    if (btnToggleAgentMode) {
      btnToggleAgentMode.addEventListener('click', () => {
        agentModeEnabled = !agentModeEnabled;
        btnToggleAgentMode.classList.toggle('active', agentModeEnabled);
      });
    }

    // Export Chat
    btnExportChat.addEventListener('click', handleExportChat);

    // Settings Modal
    btnOpenSettings.addEventListener('click', () => settingsModal.classList.add('open'));
    btnCloseSettings.addEventListener('click', () => settingsModal.classList.remove('open'));
    btnCancelSettings.addEventListener('click', () => settingsModal.classList.remove('open'));
    btnSaveSettings.addEventListener('click', saveSettings);

    // Agent permission approval controls
    if (btnDenyPermission) btnDenyPermission.addEventListener('click', () => respondToPermission('deny'));
    if (btnAlwaysAllowPermission) btnAlwaysAllowPermission.addEventListener('click', () => respondToPermission('always_allow'));
    if (btnAllowPermission) btnAllowPermission.addEventListener('click', () => respondToPermission('allow'));

    // Local Model Library Modal
    if (btnOpenModels) {
      btnOpenModels.addEventListener('click', openModelLibrary);
    }
    if (btnCloseModels) btnCloseModels.addEventListener('click', () => modelsModal.classList.remove('open'));
    if (btnDismissModels) btnDismissModels.addEventListener('click', () => modelsModal.classList.remove('open'));
    if (btnRefreshModels) btnRefreshModels.addEventListener('click', refreshModelLibrary);
    if (btnPullCustomModel) {
      btnPullCustomModel.addEventListener('click', () => {
        const name = customModelInput.value.trim();
        if (!name) {
          alert('Enter a model name first, for example llama3.2:3b.');
          return;
        }
        pullModel(name);
      });
    }
    if (customModelInput) {
      customModelInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const name = customModelInput.value.trim();
          if (name) pullModel(name);
        }
      });
    }
    if (btnCancelDownload) {
      btnCancelDownload.disabled = true; // disabled until a download starts
      btnCancelDownload.addEventListener('click', cancelModelDownload);
    }

    // Analytics Modal
    btnOpenAnalytics.addEventListener('click', async () => {
      await updateAnalyticsUI();
      analyticsModal.classList.add('open');
    });
    btnCloseAnalytics.addEventListener('click', () => analyticsModal.classList.remove('open'));
    btnDismissAnalytics.addEventListener('click', () => analyticsModal.classList.remove('open'));

    // Project Selector Menu Toggle
    if (btnProjectSelector) {
      btnProjectSelector.addEventListener('click', (e) => {
        e.stopPropagation();
        const isShown = projectDropdownMenu.style.display === 'flex';
        projectDropdownMenu.style.display = isShown ? 'none' : 'flex';
      });
    }

    // Document click to close project dropdown
    document.addEventListener('click', (e) => {
      if (projectDropdownMenu && !projectDropdownMenu.contains(e.target) && !btnProjectSelector.contains(e.target)) {
        projectDropdownMenu.style.display = 'none';
      }
    });

    // Dropdown Action: Global Workspace
    if (btnDropdownGlobal) {
      btnDropdownGlobal.addEventListener('click', async () => {
        projectDropdownMenu.style.display = 'none';
        await closeActiveProject();
      });
    }

    // Dropdown Action: Open / Create Project
    if (btnDropdownOpenProject) {
      btnDropdownOpenProject.addEventListener('click', () => {
        projectDropdownMenu.style.display = 'none';
        projectModalTitle.textContent = 'Open or Create Project';
        projectPathInput.value = '';
        projectNameInput.value = '';
        projectInstructionsInput.value = '';
        projectOverviewSection.style.display = 'none';
        btnConfirmOpenProject.textContent = 'Open Project';
        projectModal.classList.add('open');
        projectPathInput.focus();
      });
    }

    // Dropdown Action: Project Details / Settings
    if (btnDropdownProjectDetails) {
      btnDropdownProjectDetails.addEventListener('click', async () => {
        projectDropdownMenu.style.display = 'none';
        if (!currentProjectId) return;
        try {
          const res = await fetch(`/api/projects/${currentProjectId}`);
          if (res.ok) {
            const data = await res.json();
            projectModalTitle.textContent = `Project: ${data.name}`;
            projectPathInput.value = data.path;
            projectNameInput.value = data.name;
            projectInstructionsInput.value = data.instructions_content || data.instructions || '';

            const ov = data.overview || {};
            projStatFiles.textContent = ov.total_files || 0;
            projStatDirs.textContent = ov.total_dirs || 0;
            if (ov.file_tree && ov.file_tree.length > 0) {
              projFileTree.innerHTML = ov.file_tree.slice(0, 40).map(f => escapeHtml(f)).join('<br>');
            } else {
              projFileTree.textContent = 'No files found or empty directory';
            }
            projectOverviewSection.style.display = 'block';
            btnConfirmOpenProject.textContent = 'Save Changes';
            projectModal.classList.add('open');
          }
        } catch (e) {
          console.error('Failed to load project details:', e);
        }
      });
    }

    // Project Modal Close & Confirm
    if (btnCloseProjectModal) btnCloseProjectModal.addEventListener('click', () => projectModal.classList.remove('open'));
    if (btnCancelProjectModal) btnCancelProjectModal.addEventListener('click', () => projectModal.classList.remove('open'));
    if (btnConfirmOpenProject) btnConfirmOpenProject.addEventListener('click', handleSaveOrOpenProject);

    // Changes Review Modal
    if (btnReviewChanges) {
      btnReviewChanges.addEventListener('click', () => {
        renderModifiedFilesList();
        changesReviewModal.classList.add('open');
      });
    }
    if (btnCloseChangesModal) btnCloseChangesModal.addEventListener('click', () => changesReviewModal.classList.remove('open'));
    if (btnDismissChanges) btnDismissChanges.addEventListener('click', () => changesReviewModal.classList.remove('open'));
    if (btnClearChanges) {
      btnClearChanges.addEventListener('click', () => {
        modifiedFilesMap.clear();
        updateModifiedFilesBadge();
        changesReviewModal.classList.remove('open');
      });
    }

    // Searchable model selector
    if (modelSelectorButton) {
      modelSelectorButton.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleModelSearch(modelSearchPopover.hidden);
      });
      modelSelectorButton.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggleModelSearch(true);
        }
      });
    }

    if (modelSearchInput) {
      modelSearchInput.addEventListener('input', () => {
        renderModelSearchResults(modelSearchInput.value);
      });
      modelSearchInput.addEventListener('keydown', handleModelSearchKeydown);
    }

    if (modelSearchClear) {
      modelSearchClear.addEventListener('click', () => {
        modelSearchInput.value = '';
        renderModelSearchResults('');
        modelSearchInput.focus();
      });
    }

    if (modelSearchPopover) {
      modelSearchPopover.addEventListener('click', (e) => e.stopPropagation());
    }

    document.addEventListener('click', (e) => {
      if (modelSearchPopover && !modelSearchPopover.hidden &&
          modelSelectorWrapper && !modelSelectorWrapper.contains(e.target)) {
        toggleModelSearch(false);
      }
    });

    // Model Selector change
    modelSelector.addEventListener('change', async () => {
      updateModelSelectorLabel();
      const val = modelSelector.value;
      const [provider, ...rest] = val.split(':');
      const model = rest.join(':');
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: { selected_provider: provider, selected_model: model } })
      });
    });

    // Model Library search
    if (modelLibrarySearchInput) {
      modelLibrarySearchInput.addEventListener('input', () => {
        modelLibraryQuery = modelLibrarySearchInput.value;
        updateModelLibrarySearchUI();
        renderInstalledModels();
        renderRecommendedModels();
      });
    }
    if (modelLibrarySearchClear) {
      modelLibrarySearchClear.addEventListener('click', () => {
        modelLibrarySearchInput.value = '';
        modelLibraryQuery = '';
        updateModelLibrarySearchUI();
        renderInstalledModels();
        renderRecommendedModels();
        modelLibrarySearchInput.focus();
      });
    }
  }

  // --------------------------------------------------------------------------
  // Models & Providers (with Hardware Recommendation Stars)
  // --------------------------------------------------------------------------
  async function loadModels() {
    try {
      const previousSelection = modelSelector.value;
      const res = await fetch('/api/models');
      const data = await res.json();

      optGroupOllama.innerHTML = '';
      const ollamaData = data.ollama || {};
      const ollamaModels = ollamaData.models || [];

      if (ollamaModels.length > 0) {
        statusDot.classList.remove('offline');
        statusText.textContent = `Ollama (${ollamaModels.length} models)`;
        ollamaModels.forEach((m) => {
          const opt = document.createElement('option');
          opt.value = `ollama:${m.id}`;
          const starPrefix = m.is_recommended ? '⭐ ' : '';
          opt.textContent = `${starPrefix}${m.raw_name || m.name || m.id}`;
          if (m.is_recommended && m.recommendation_reason) {
            opt.title = m.recommendation_reason;
          }
          optGroupOllama.appendChild(opt);
        });
      } else {
        statusDot.classList.add('offline');
        statusText.textContent = 'Ollama Offline';
        const opt = document.createElement('option');
        opt.value = 'ollama:none';
        opt.textContent = 'No local models found';
        opt.disabled = true;
        optGroupOllama.appendChild(opt);
      }

      // Online models
      optGroupOnline.innerHTML = '';
      ['openai', 'anthropic', 'gemini', 'groq', 'openrouter'].forEach((prov) => {
        if (data[prov] && data[prov].models) {
          data[prov].models.forEach((m) => {
            const opt = document.createElement('option');
            opt.value = `${prov}:${m.id}`;
            const starPrefix = m.is_recommended ? '⭐ ' : '';
            opt.textContent = `${starPrefix}${data[prov].name}: ${m.raw_name || m.name}`;
            if (m.is_recommended && m.recommendation_reason) {
              opt.title = m.recommendation_reason;
            }
            optGroupOnline.appendChild(opt);
          });
        }
      });

      // Keep the user's current selection if it survived the refresh. On the
      // first load, honour the model saved in settings instead of the static
      // HTML default so the selected model persists across app restarts.
      const availableValues = Array.from(modelSelector.options).map((o) => o.value);
      const preferredSelection = (!hasInitializedModelSelection && savedModelSelection)
        ? savedModelSelection
        : previousSelection;
      let targetSelection = preferredSelection;
      if (!targetSelection || !availableValues.includes(targetSelection)) {
        targetSelection = previousSelection;
      }
      if (targetSelection && availableValues.includes(targetSelection)) {
        modelSelector.value = targetSelection;
      }
      hasInitializedModelSelection = true;

      updateModelSelectorLabel();
      if (modelSearchPopover && !modelSearchPopover.hidden) {
        renderModelSearchResults(modelSearchInput.value);
      }
    } catch (e) {
      console.error('Failed to load models:', e);
      statusDot.classList.add('offline');
      statusText.textContent = 'Ollama Error';
    }
  }

  // --------------------------------------------------------------------------
  // Searchable model selector
  // --------------------------------------------------------------------------
  function getModelOptions() {
    const providerNames = {
      ollama: 'Local Ollama',
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      gemini: 'Google Gemini',
      groq: 'Groq',
      openrouter: 'OpenRouter'
    };

    return Array.from(modelSelector.options).map((opt, index) => {
      const providerId = String(opt.value || '').split(':')[0];
      const groupLabel = opt.parentElement && opt.parentElement.tagName === 'OPTGROUP'
        ? opt.parentElement.label
        : 'Models';
      return {
        value: opt.value,
        label: opt.textContent || opt.value,
        provider: providerNames[providerId] || groupLabel,
        providerId,
        title: opt.title || '',
        disabled: opt.disabled,
        index
      };
    });
  }

  function updateModelSelectorLabel() {
    if (!modelSelectorLabel) return;
    const selected = modelSelector.options[modelSelector.selectedIndex];
    if (selected) {
      modelSelectorLabel.textContent = selected.textContent || selected.value;
      modelSelectorLabel.title = selected.title || selected.value;
    } else {
      modelSelectorLabel.textContent = 'Select a model';
      modelSelectorLabel.title = '';
    }
  }

  function toggleModelSearch(open) {
    if (!modelSearchPopover) return;
    if (open) {
      modelSearchPopover.hidden = false;
      if (modelSelectorButton) modelSelectorButton.setAttribute('aria-expanded', 'true');
      if (modelSearchInput) {
        modelSearchInput.value = '';
        renderModelSearchResults('');
        requestAnimationFrame(() => modelSearchInput.focus());
      }
    } else {
      modelSearchPopover.hidden = true;
      if (modelSelectorButton) modelSelectorButton.setAttribute('aria-expanded', 'false');
      modelSearchActiveIndex = -1;
    }
  }

  function normalizeModelSearchText(value) {
    return String(value || '')
      .toLowerCase()
      .replace(/[⭐★]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function modelOptionScore(option, query) {
    if (!query) return 0;
    const label = normalizeModelSearchText(option.label);
    const value = normalizeModelSearchText(option.value);
    const provider = normalizeModelSearchText(option.provider);

    if (label === query || value === query) return 0;
    if (label.startsWith(query) || value.startsWith(query)) return 1;
    if (provider === query) return 1;
    if (value.split(/[:\s/._-]+/).some((part) => part.startsWith(query))) return 2;
    if (label.includes(query) || value.includes(query) || provider.includes(query)) return 3;
    return 4;
  }

  function renderModelSearchResults(rawQuery) {
    if (!modelSearchResults) return;

    const query = normalizeModelSearchText(rawQuery);
    const tokens = query.split(' ').filter(Boolean);
    const allOptions = getModelOptions().filter((o) => !o.disabled);

    const filtered = allOptions.filter((option) => {
      const haystack = normalizeModelSearchText(
        `${option.label} ${option.value} ${option.provider} ${option.title}`
      );
      return tokens.every((token) => haystack.includes(token));
    });

    if (modelSearchClear) {
      modelSearchClear.style.display = rawQuery ? 'block' : 'none';
    }

    if (modelSearchSummary) {
      if (filtered.length === 0) {
        modelSearchSummary.textContent = 'No matching models';
      } else if (query) {
        modelSearchSummary.textContent = `${filtered.length} model${filtered.length === 1 ? '' : 's'} matching “${rawQuery.trim()}”`;
      } else {
        modelSearchSummary.textContent = `${filtered.length} model${filtered.length === 1 ? '' : 's'} available`;
      }
    }

    modelSearchResults.innerHTML = '';
    modelSearchItems = [];
    modelSearchActiveIndex = -1;

    if (filtered.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'model-search-empty';
      empty.textContent = rawQuery
        ? `No models match “${rawQuery.trim()}”. Try a model name, provider, or tag.`
        : 'No models are available yet.';
      modelSearchResults.appendChild(empty);
      return;
    }

    // Keep provider grouping, but rank the best matches first inside each group.
    const groups = new Map();
    filtered.forEach((option) => {
      if (!groups.has(option.provider)) groups.set(option.provider, []);
      groups.get(option.provider).push(option);
    });

    groups.forEach((options, providerName) => {
      options.sort((a, b) => {
        return modelOptionScore(a, query) - modelOptionScore(b, query) || a.index - b.index;
      });

      const groupLabel = document.createElement('div');
      groupLabel.className = 'model-search-group-label';
      groupLabel.textContent = providerName;
      modelSearchResults.appendChild(groupLabel);

      options.forEach((option) => {
        const itemIndex = modelSearchItems.length;
        modelSearchItems.push(option);

        const row = document.createElement('div');
        row.className = 'model-search-item' + (option.value === modelSelector.value ? ' selected' : '');
        row.setAttribute('role', 'option');
        row.dataset.index = String(itemIndex);

        const left = document.createElement('div');
        left.className = 'model-search-item-left';

        const name = document.createElement('span');
        name.className = 'model-search-item-name';
        name.textContent = option.label;

        const id = document.createElement('span');
        id.className = 'model-search-item-id';
        id.textContent = option.value;

        left.appendChild(name);
        left.appendChild(id);

        const badge = document.createElement('span');
        badge.className = 'model-search-item-badge';
        badge.textContent = option.providerId === 'ollama' ? 'Local' : option.provider;

        row.appendChild(left);
        row.appendChild(badge);
        row.addEventListener('click', () => selectModelOption(option.value));
        row.addEventListener('mouseenter', () => setModelSearchActive(itemIndex));
        modelSearchResults.appendChild(row);
      });
    });
  }

  function setModelSearchActive(index) {
    if (!modelSearchResults || modelSearchItems.length === 0) return;
    modelSearchActiveIndex = (index + modelSearchItems.length) % modelSearchItems.length;
    const rows = modelSearchResults.querySelectorAll('.model-search-item');
    rows.forEach((row, i) => row.classList.toggle('active', i === modelSearchActiveIndex));
    const activeRow = rows[modelSearchActiveIndex];
    if (activeRow && activeRow.scrollIntoView) {
      activeRow.scrollIntoView({ block: 'nearest' });
    }
  }

  function handleModelSearchKeydown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      toggleModelSearch(false);
      if (modelSelectorButton) modelSelectorButton.focus();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setModelSearchActive(modelSearchActiveIndex < 0 ? 0 : modelSearchActiveIndex + 1);
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setModelSearchActive(
        modelSearchActiveIndex < 0 ? modelSearchItems.length - 1 : modelSearchActiveIndex - 1
      );
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const index = modelSearchActiveIndex >= 0 ? modelSearchActiveIndex : 0;
      const option = modelSearchItems[index];
      if (option) selectModelOption(option.value);
    }
  }

  function selectModelOption(value) {
    modelSelector.value = value;
    modelSelector.dispatchEvent(new Event('change', { bubbles: true }));
    updateModelSelectorLabel();
    toggleModelSearch(false);
  }

  // --------------------------------------------------------------------------
  // Local Model Library (download / delete without helper scripts)
  // --------------------------------------------------------------------------
  function openModelLibrary() {
    if (!modelsModal) return;
    modelsModal.classList.add('open');
    updateModelLibrarySearchUI();
    refreshModelLibrary();
    if (modelLibrarySearchInput) {
      requestAnimationFrame(() => modelLibrarySearchInput.focus());
    }
  }

  async function refreshModelLibrary() {
    await Promise.all([loadInstalledModels(), loadRecommendedModels()]);
  }

  const DOWNLOAD_ICON_SVG = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 3v12"></path>
      <polyline points="7 10 12 15 17 10"></polyline>
      <path d="M4 21h16"></path>
    </svg>`;

  const TRASH_ICON_SVG = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="3 6 5 6 21 6"></polyline>
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
    </svg>`;

  const CHECK_ICON_SVG = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>`;

  function modelMatchesLibraryQuery(m) {
    const query = normalizeModelSearchText(modelLibraryQuery);
    if (!query) return true;
    const tokens = query.split(' ').filter(Boolean);
    const haystack = normalizeModelSearchText(
      `${m.id || ''} ${m.name || ''} ${m.raw_name || ''} ${m.description || ''} ${m.approx_size || ''}`
    );
    return tokens.every((token) => haystack.includes(token));
  }

  function updateModelLibrarySearchUI() {
    if (modelLibrarySearchClear) {
      modelLibrarySearchClear.style.display = modelLibraryQuery ? 'block' : 'none';
    }
    if (!modelLibrarySearchStatus) return;

    const installedMatches = installedModelsCache.filter(modelMatchesLibraryQuery).length;
    const recommendedMatches = recommendedModelsCache.filter(modelMatchesLibraryQuery).length;

    if (modelLibraryQuery.trim()) {
      const total = installedMatches + recommendedMatches;
      modelLibrarySearchStatus.textContent = `${total} match${total === 1 ? '' : 'es'} for “${modelLibraryQuery.trim()}”`;
    } else {
      modelLibrarySearchStatus.textContent = `${installedModelsCache.length} installed • ${recommendedModelsCache.length} recommended`;
    }
  }

  async function loadInstalledModels() {
    if (!installedModelsList) return;
    installedModelsList.innerHTML = '<div class="model-list-empty">Loading installed models...</div>';
    try {
      const res = await fetch('/api/models');
      const data = await res.json();
      installedModelsCache = (data.ollama && data.ollama.models) || [];
      renderInstalledModels();
      updateModelLibrarySearchUI();
    } catch (e) {
      installedModelsList.innerHTML = `<div class="model-list-empty">Could not read installed models: ${escapeHtml(e.message)}</div>`;
    }
  }

  function renderInstalledModels() {
    if (!installedModelsList) return;
    const models = installedModelsCache.filter(modelMatchesLibraryQuery);

    if (installedModelsCount) {
      installedModelsCount.textContent = modelLibraryQuery.trim()
        ? `${models.length}/${installedModelsCache.length}`
        : String(installedModelsCache.length);
    }

    if (installedModelsCache.length === 0) {
      installedModelsList.innerHTML = '<div class="model-list-empty">No local models installed yet. Pick one below to download.</div>';
      return;
    }
    if (models.length === 0) {
      installedModelsList.innerHTML = `<div class="model-list-empty">No installed models match “${escapeHtml(modelLibraryQuery.trim())}”.</div>`;
      return;
    }

    installedModelsList.innerHTML = '';
    models.forEach((m) => {
      const card = document.createElement('div');
      card.className = 'model-card';

      const info = document.createElement('div');
      info.className = 'model-card-info';
      info.innerHTML = `
        <div class="model-card-title-row">
          <span class="model-card-title">${escapeHtml(m.raw_name || m.id)}</span>
          <span class="model-tag installed">Installed</span>
        </div>
        <span class="model-card-id">${escapeHtml(m.id)}</span>
        <span class="model-card-desc">${escapeHtml(m.name)}</span>
      `;

      const action = document.createElement('div');
      action.className = 'model-card-action';
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn-danger';
      deleteBtn.innerHTML = `${TRASH_ICON_SVG}<span>Delete</span>`;
      deleteBtn.title = `Delete ${m.id}`;
      deleteBtn.addEventListener('click', () => deleteModel(m.id));
      action.appendChild(deleteBtn);

      card.appendChild(info);
      card.appendChild(action);
      installedModelsList.appendChild(card);
    });
  }

  async function loadRecommendedModels() {
    if (!recommendedModelsList) return;
    recommendedModelsList.innerHTML = '<div class="model-list-empty">Loading recommendations...</div>';
    try {
      const res = await fetch('/api/models/recommended');
      const data = await res.json();
      recommendedModelsCache = data.models || [];
      renderRecommendedModels();
      updateModelLibrarySearchUI();
    } catch (e) {
      recommendedModelsList.innerHTML = `<div class="model-list-empty">Could not load recommendations: ${escapeHtml(e.message)}</div>`;
    }
  }

  function renderRecommendedModels() {
    if (!recommendedModelsList) return;
    const models = recommendedModelsCache.filter(modelMatchesLibraryQuery);

    if (recommendedModelsCount) {
      recommendedModelsCount.textContent = modelLibraryQuery.trim()
        ? `${models.length}/${recommendedModelsCache.length}`
        : String(recommendedModelsCache.length);
    }

    if (recommendedModelsCache.length === 0) {
      recommendedModelsList.innerHTML = '<div class="model-list-empty">No recommendations available.</div>';
      return;
    }
    if (models.length === 0) {
      recommendedModelsList.innerHTML = `<div class="model-list-empty">No recommended models match “${escapeHtml(modelLibraryQuery.trim())}”.</div>`;
      return;
    }

    recommendedModelsList.innerHTML = '';
    models.forEach((m) => {
      const card = document.createElement('div');
      card.className = 'model-card';

      const info = document.createElement('div');
      info.className = 'model-card-info';
      const badges = [];
      if (m.is_installed) badges.push('<span class="model-tag installed">Installed</span>');
      if (m.is_compatible === false) badges.push('<span class="model-tag incompatible">Needs more RAM</span>');
      info.innerHTML = `
        <div class="model-card-title-row">
          <span class="model-card-title">${escapeHtml(m.name)}</span>
          ${badges.join('')}
        </div>
        <span class="model-card-id">${escapeHtml(m.id)}</span>
        <span class="model-card-desc">${escapeHtml(m.description)} ${escapeHtml(m.approx_size)}.</span>
      `;

      const action = document.createElement('div');
      action.className = 'model-card-action';
      const pullBtn = document.createElement('button');
      if (m.is_installed) {
        pullBtn.className = 'btn-secondary';
        pullBtn.innerHTML = `${CHECK_ICON_SVG}<span>Installed</span>`;
        pullBtn.disabled = true;
      } else {
        pullBtn.className = 'btn-primary';
        pullBtn.innerHTML = `${DOWNLOAD_ICON_SVG}<span>Download</span>`;
        pullBtn.title = `Download ${m.id}`;
        pullBtn.addEventListener('click', () => pullModel(m.id));
      }
      action.appendChild(pullBtn);

      card.appendChild(info);
      card.appendChild(action);
      recommendedModelsList.appendChild(card);
    });
  }

  async function deleteModel(modelName) {
    if (!confirm(`Delete "${modelName}" from this computer?\n\nYou can download it again later.`)) return;
    try {
      const res = await fetch(`/api/models?model=${encodeURIComponent(modelName)}`, { method: 'DELETE' });
      if (!res.ok) {
        let detail = `Server returned ${res.status}`;
        try {
          const data = await res.json();
          if (data.detail) detail = data.detail;
        } catch (_) {}
        throw new Error(detail);
      }
      await loadModels();
      await refreshModelLibrary();
    } catch (e) {
      alert(`Could not delete ${modelName}: ${e.message}`);
    }
  }

  async function pullModel(modelName) {
    if (isDownloadingModel) {
      alert('A model download is already in progress. Wait for it to finish first.');
      return;
    }

    isDownloadingModel = true;
    currentDownloadingModel = modelName;
    if (btnPullCustomModel) btnPullCustomModel.disabled = true;
    if (btnCancelDownload) btnCancelDownload.disabled = false;
    if (modelDownloadStatus) modelDownloadStatus.style.display = 'flex';
    if (modelDownloadLabel) modelDownloadLabel.textContent = `Downloading ${modelName}...`;
    if (modelDownloadPercent) modelDownloadPercent.textContent = '0%';
    if (modelDownloadProgressFill) modelDownloadProgressFill.style.width = '0%';
    if (modelDownloadDetail) modelDownloadDetail.textContent = 'Contacting Ollama...';

    let finished = false;

    try {
      const res = await fetch('/api/models/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelName })
      });
      if (!res.ok) {
        let detail = `Server returned ${res.status}`;
        try {
          const data = await res.json();
          if (data.detail) detail = data.detail;
        } catch (_) {}
        throw new Error(detail);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim().startsWith('data: ')) continue;
          let event;
          try {
            event = JSON.parse(line.trim().slice(6));
          } catch (_) {
            continue;
          }

          if (event.type === 'progress') {
            if (event.percent !== null && event.percent !== undefined) {
              if (modelDownloadPercent) modelDownloadPercent.textContent = `${event.percent}%`;
              if (modelDownloadProgressFill) modelDownloadProgressFill.style.width = `${Math.min(100, event.percent)}%`;
              if (modelDownloadDetail) {
                modelDownloadDetail.textContent = `${formatModelStatus(event.status)} — ${formatBytes(event.completed)} / ${formatBytes(event.total)}`;
              }
            } else if (modelDownloadDetail) {
              modelDownloadDetail.textContent = formatModelStatus(event.status);
            }
          } else if (event.type === 'done') {
            finished = true;
            if (modelDownloadPercent) modelDownloadPercent.textContent = '100%';
            if (modelDownloadProgressFill) modelDownloadProgressFill.style.width = '100%';
            if (modelDownloadLabel) modelDownloadLabel.textContent = `${modelName} is ready`;
            if (modelDownloadDetail) modelDownloadDetail.textContent = 'Download complete. It is now available in the model selector.';
          } else if (event.type === 'cancelled') {
            if (modelDownloadLabel) modelDownloadLabel.textContent = `Download cancelled`;
            if (modelDownloadDetail) modelDownloadDetail.textContent = `${modelName} download was cancelled.`;
            if (modelDownloadPercent) modelDownloadPercent.textContent = '';
            if (modelDownloadProgressFill) modelDownloadProgressFill.style.width = '0%';
            break;
          } else if (event.type === 'error') {
            throw new Error(event.error || 'Download failed.');
          }
        }
      }

      if (finished) {
        customModelInput.value = '';
        await loadModels();
        await refreshModelLibrary();
      }
    } catch (e) {
      if (modelDownloadLabel) modelDownloadLabel.textContent = `Download failed: ${modelName}`;
      if (modelDownloadDetail) modelDownloadDetail.textContent = e.message;
      if (modelDownloadPercent) modelDownloadPercent.textContent = '';
      if (modelDownloadProgressFill) modelDownloadProgressFill.style.width = '0%';
    } finally {
      isDownloadingModel = false;
      currentDownloadingModel = null;
      if (btnPullCustomModel) btnPullCustomModel.disabled = false;
      if (btnCancelDownload) btnCancelDownload.disabled = true;
    }
  }

  // Cancel an in-progress download
  async function cancelModelDownload() {
    if (!currentDownloadingModel) return;
    try {
      await fetch(`/api/models/pull?model=${encodeURIComponent(currentDownloadingModel)}`, {
        method: 'DELETE'
      });
      if (btnCancelDownload) btnCancelDownload.disabled = true;
      if (modelDownloadDetail) modelDownloadDetail.textContent = 'Cancelling download…';
    } catch (e) {
      console.error('Cancel failed:', e);
    }
  }

  function formatModelStatus(status) {
    if (!status) return 'Working...';
    const text = String(status).replace(/_/g, ' ');
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function formatBytes(bytes) {
    const value = Number(bytes) || 0;
    if (value <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
    const amount = value / Math.pow(1024, index);
    return `${amount.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
  }

  // --------------------------------------------------------------------------
  // --------------------------------------------------------------------------
  // Antigravity Projects / Workspaces
  // --------------------------------------------------------------------------
  async function loadActiveProjectAndProjects() {
    try {
      const pRes = await fetch('/api/projects');
      projectsList = await pRes.json();
      renderRecentProjects();

      const aRes = await fetch('/api/projects/active');
      const activeData = await aRes.json();
      if (activeData && activeData.id) {
        setProjectActiveState(activeData);
      } else {
        setGlobalWorkspaceState();
      }
    } catch (e) {
      console.error('Error loading projects:', e);
      setGlobalWorkspaceState();
    }
  }

  function setProjectActiveState(proj) {
    currentProjectId = proj.id;
    currentProjectPath = proj.path;
    currentProjectName = proj.name;
    if (activeProjectLabel) {
      activeProjectLabel.textContent = proj.name;
      activeProjectLabel.title = `Project: ${proj.name}\nPath: ${proj.path}`;
    }
    if (btnDropdownProjectDetails) {
      btnDropdownProjectDetails.style.display = 'flex';
    }
    renderRecentProjects();
    fetchConversations(currentProjectId);
  }

  function setGlobalWorkspaceState() {
    currentProjectId = null;
    currentProjectPath = null;
    currentProjectName = null;
    if (activeProjectLabel) {
      activeProjectLabel.textContent = 'Global Workspace';
      activeProjectLabel.title = 'Global Scratch Workspace (No Project)';
    }
    if (btnDropdownProjectDetails) {
      btnDropdownProjectDetails.style.display = 'none';
    }
    renderRecentProjects();
    fetchConversations(null);
  }

  function renderRecentProjects() {
    if (!recentProjectsContainer) return;
    recentProjectsContainer.innerHTML = '';
    if (!projectsList || projectsList.length === 0) {
      recentProjectsContainer.innerHTML = '<div style="padding: 6px 8px; font-size: 11px; color: var(--text-dim);">No recent projects</div>';
      return;
    }

    projectsList.forEach((p) => {
      const item = document.createElement('div');
      item.className = 'recent-proj-item' + (p.id === currentProjectId ? ' active' : '');

      const left = document.createElement('div');
      left.className = 'recent-proj-left';
      left.innerHTML = `
        <span class="recent-proj-name">${escapeHtml(p.name)}</span>
        <span class="recent-proj-path">${escapeHtml(p.path)}</span>
      `;
      left.addEventListener('click', async () => {
        if (projectDropdownMenu) projectDropdownMenu.style.display = 'none';
        await switchProject(p.id);
      });

      const removeBtn = document.createElement('button');
      removeBtn.className = 'recent-proj-remove';
      removeBtn.innerHTML = '&times;';
      removeBtn.title = 'Remove project from history';
      removeBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await deleteProject(p.id);
      });

      item.appendChild(left);
      item.appendChild(removeBtn);
      recentProjectsContainer.appendChild(item);
    });
  }

  async function switchProject(projectId) {
    try {
      const res = await fetch(`/api/projects/${projectId}/open`, { method: 'POST' });
      if (res.ok) {
        const proj = await res.json();
        setProjectActiveState(proj);
      }
    } catch (e) {
      console.error('Failed to switch project:', e);
    }
  }

  async function deleteProject(projectId) {
    if (!confirm('Remove this project from workspace history? (Files will remain on disk)')) return;
    try {
      const res = await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
      if (res.ok) {
        projectsList = projectsList.filter((p) => p.id !== projectId);
        if (currentProjectId === projectId) {
          await closeActiveProject();
        } else {
          renderRecentProjects();
        }
      }
    } catch (e) {
      console.error('Failed to delete project:', e);
    }
  }

  async function closeActiveProject() {
    try {
      await fetch('/api/projects/close', { method: 'POST' });
      setGlobalWorkspaceState();
    } catch (e) {
      console.error('Failed to close active project:', e);
    }
  }

  async function handleSaveOrOpenProject() {
    const path = projectPathInput.value.trim();
    if (!path) {
      alert('Please specify a project folder path.');
      return;
    }
    const name = projectNameInput.value.trim();
    const instructions = projectInstructionsInput.value;

    try {
      if (projectModalTitle.textContent.startsWith('Project:') && currentProjectId) {
        const res = await fetch(`/api/projects/${currentProjectId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name || undefined, instructions: instructions })
        });
        if (res.ok) {
          const updated = await res.json();
          setProjectActiveState(updated);
          projectModal.classList.remove('open');
        } else {
          alert('Failed to update project settings.');
        }
      } else {
        const res = await fetch('/api/projects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path, name, instructions })
        });
        if (res.ok) {
          const proj = await res.json();
          const pRes = await fetch('/api/projects');
          projectsList = await pRes.json();
          setProjectActiveState(proj);
          projectModal.classList.remove('open');
        } else {
          alert('Failed to open or create project.');
        }
      }
    } catch (e) {
      console.error('Error opening project:', e);
      alert('Error opening project: ' + e.message);
    }
  }

  function updateModifiedFilesBadge() {
    if (!btnReviewChanges || !modifiedFilesCount) return;
    if (modifiedFilesMap.size > 0) {
      btnReviewChanges.style.display = 'flex';
      modifiedFilesCount.textContent = modifiedFilesMap.size;
    } else {
      btnReviewChanges.style.display = 'none';
    }
  }

  function renderModifiedFilesList() {
    if (!modifiedFilesList) return;
    modifiedFilesList.innerHTML = '';
    if (diffViewerWrapper) diffViewerWrapper.style.display = 'none';
    if (modifiedFilesMap.size === 0) {
      modifiedFilesList.innerHTML = '<div style="color: var(--text-dim); font-size: 13px;">No files modified yet in this session.</div>';
      return;
    }
    modifiedFilesMap.forEach((meta, path) => {
      const item = document.createElement('div');
      item.className = 'modified-file-item';
      item.innerHTML = `
        <span class="modified-file-name">${escapeHtml(path)}</span>
        <span class="modified-file-badge ${meta.action}">${escapeHtml(meta.action)}</span>
      `;
      item.addEventListener('click', () => {
        if (!diffViewerWrapper || !diffViewerFileName || !diffViewerCode) return;
        diffViewerFileName.textContent = `${meta.action.toUpperCase()}: ${path}`;
        diffViewerWrapper.style.display = 'block';
        diffViewerCode.textContent = `File Path: ${path}\nAction: ${meta.action.toUpperCase()}\nTool: ${meta.tool}\nRecorded: ${new Date(meta.timestamp).toLocaleTimeString()}`;
      });
      modifiedFilesList.appendChild(item);
    });
  }

  // --------------------------------------------------------------------------
  // Conversations (Chat History)
  // --------------------------------------------------------------------------
  async function fetchConversations(projectId = currentProjectId) {
    try {
      const url = projectId ? `/api/conversations?project_id=${encodeURIComponent(projectId)}` : '/api/conversations';
      const res = await fetch(url);
      conversations = await res.json();

      if (conversations.length === 0) {
        await createNewChat();
      } else {
        renderConversationList();
        // Load first conversation
        loadConversation(conversations[0].id);
      }
    } catch (e) {
      console.error('Failed to fetch conversations:', e);
    }
  }

  function renderConversationList(filterQuery = '') {
    conversationsList.innerHTML = '';
    const filtered = conversations.filter((c) =>
      c.title.toLowerCase().includes(filterQuery)
    );

    filtered.forEach((conv) => {
      const item = document.createElement('div');
      item.className = 'history-item' + (conv.id === currentConversationId ? ' active' : '');
      item.onclick = () => loadConversation(conv.id);

      const titleSpan = document.createElement('span');
      titleSpan.className = 'history-title';
      titleSpan.textContent = conv.title || 'Untitled Chat';

      const actionsDiv = document.createElement('div');
      actionsDiv.className = 'history-actions';

      // Delete button
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'icon-btn-sm';
      deleteBtn.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        </svg>
      `;
      deleteBtn.title = 'Delete Chat';
      deleteBtn.onclick = (e) => {
        e.stopPropagation();
        deleteConversation(conv.id);
      };

      actionsDiv.appendChild(deleteBtn);
      item.appendChild(titleSpan);
      item.appendChild(actionsDiv);
      conversationsList.appendChild(item);
    });
  }

  async function createNewChat() {
    try {
      const selected = modelSelector.value || 'ollama:llama3.2:1b';
      const [provider, ...rest] = selected.split(':');
      const model = rest.join(':');

      const res = await fetch('/api/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'New Chat',
          provider,
          model,
          project_id: currentProjectId
        })
      });
      const newConv = await res.json();
      conversations.unshift(newConv);
      currentConversationId = newConv.id;
      renderConversationList();
      renderMessages([]);
      messageInput.focus();
    } catch (e) {
      console.error('Failed to create chat:', e);
    }
  }

  async function loadConversation(id) {
    if (isGenerating) return;
    currentConversationId = id;
    renderConversationList();

    try {
      const res = await fetch(`/api/conversations/${id}`);
      const conv = await res.json();
      renderMessages(conv.messages || []);
    } catch (e) {
      console.error('Failed to load conversation:', e);
    }
  }

  async function deleteConversation(id) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    try {
      await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
      conversations = conversations.filter((c) => c.id !== id);
      if (currentConversationId === id) {
        if (conversations.length > 0) {
          loadConversation(conversations[0].id);
        } else {
          createNewChat();
        }
      } else {
        renderConversationList();
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e);
    }
  }

  // --------------------------------------------------------------------------
  // Message Rendering
  // --------------------------------------------------------------------------
  function renderMessages(messages) {
    messagesContainer.innerHTML = '';

    if (!messages || messages.length === 0) {
      // Empty welcome screen
      const welcome = document.createElement('div');
      welcome.className = 'welcome-screen';
      welcome.innerHTML = `
        <div class="welcome-icon">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        </div>
        <h2 class="welcome-title">How can I assist you today?</h2>
        <p class="welcome-desc">
          Chat with your local Ollama models or online AI agents. Attach PDFs, DOCX, Spreadsheets, or code files with the <strong>+</strong> button, or toggle <strong>Web Search</strong> for real-time internet knowledge.
        </p>
        <div class="quick-prompts-grid">
          <div class="quick-prompt-card" onclick="window.usePrompt('Summarize the key differences between Ollama models and online APIs.')">
            Compare local vs online models
          </div>
          <div class="quick-prompt-card" onclick="window.usePrompt('Help me write a Python script for asynchronous file processing.')">
            Write a fast async Python script
          </div>
          <div class="quick-prompt-card" onclick="window.usePrompt('What are recent advances in local open-source LLMs?')">
            Search web for recent open LLM trends
          </div>
          <div class="quick-prompt-card" onclick="window.usePrompt('Explain how Retrieval-Augmented Generation (RAG) works in simple terms.')">
            Explain RAG & Document Search
          </div>
        </div>
      `;
      messagesContainer.appendChild(welcome);
      return;
    }

    messages.forEach((msg) => {
      appendMessageBubble(msg.role, msg.content, {
        msgId: msg.id,
        attachments: msg.attachments,
        searchResults: msg.search_results,
        promptTokens: msg.prompt_tokens,
        completionTokens: msg.completion_tokens,
        durationSec: msg.duration_sec
      });
    });

    scrollToBottom();
  }

  window.usePrompt = function (text) {
    messageInput.value = text;
    messageInput.focus();
  };

  function appendMessageBubble(role, content, meta = {}) {
    // If welcome screen is visible, remove it
    const welcome = messagesContainer.querySelector('.welcome-screen');
    if (welcome) welcome.remove();

    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const avatar = document.createElement('div');
    avatar.className = `avatar ${role === 'user' ? 'user-avatar' : 'bot-avatar'}`;
    avatar.textContent = role === 'user' ? 'U' : 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    // Render attachments if user message
    if (meta.attachments && meta.attachments.length > 0) {
      const attTray = document.createElement('div');
      attTray.className = 'attachments-tray';
      attTray.style.marginBottom = '8px';
      meta.attachments.forEach((a) => {
        const chip = document.createElement('div');
        chip.className = 'attachment-chip';
        chip.innerHTML = `<strong>${a.filename}</strong> (${a.size_str || ''})`;
        attTray.appendChild(chip);
      });
      bubble.appendChild(attTray);
    }

    // Render search results if assistant message
    if (meta.searchResults && meta.searchResults.length > 0) {
      const srCard = document.createElement('div');
      srCard.className = 'search-citations';
      let citationsHtml = `<div class="citation-header">Web Search Citations:</div>`;
      meta.searchResults.forEach((r, idx) => {
        citationsHtml += `<div>[${idx + 1}] <a class="citation-link" href="${r.url}" target="_blank">${r.title}</a></div>`;
      });
      srCard.innerHTML = citationsHtml;
      bubble.appendChild(srCard);
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'bubble-content';
    contentDiv.innerHTML = renderMarkdown(content);
    bubble.appendChild(contentDiv);

    // Meta details (tokens & latency)
    if (role === 'assistant' && (meta.completionTokens || meta.promptTokens)) {
      const metaDiv = document.createElement('div');
      metaDiv.className = 'bubble-meta';
      const tokSec = meta.durationSec > 0 ? (meta.completionTokens / meta.durationSec).toFixed(1) : 0;
      metaDiv.innerHTML = `
        <span>${meta.durationSec || 0}s (${tokSec} tok/s)</span>
        <span>&bull;</span>
        <span>${meta.promptTokens || 0} in / ${meta.completionTokens || 0} out</span>
      `;
      bubble.appendChild(metaDiv);
    }

    row.appendChild(avatar);
    row.appendChild(bubble);

    // ── Delete button (shown on hover, only for messages with an ID) ──────
    setMessageId(row, meta.msgId);

    messagesContainer.appendChild(row);

    highlightCodeBlocks(bubble);
    scrollToBottom();
    return bubble;
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // --------------------------------------------------------------------------
  // Delete Message Pair
  // --------------------------------------------------------------------------
  let _pendingDeleteMsgId = null;
  let _pendingDeleteRow   = null;

  // Attach (or update) the persistent DB id for a rendered message row. Rows
  // are first drawn before the server has saved them, then stamped when the
  // corresponding SSE event arrives.
  function setMessageId(row, msgId) {
    if (!row || !msgId) return;
    row.dataset.msgId = msgId;
    if (row.querySelector('.msg-delete-btn')) return;

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'msg-delete-btn';
    deleteBtn.title = 'Delete this message pair';
    deleteBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>`;
    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openDeleteMsgConfirm(row.dataset.msgId, row);
    });
    row.appendChild(deleteBtn);
  }

  function openDeleteMsgConfirm(msgId, row) {
    if (isGenerating) {
      // Deleting the current user turn mid-stream would leave the eventual
      // assistant reply orphaned in the database.
      alert('Please wait for the current response to finish before deleting a message.');
      return;
    }
    _pendingDeleteMsgId = msgId;
    _pendingDeleteRow   = row;
    const overlay = document.getElementById('deleteMsgOverlay');
    if (overlay) overlay.classList.add('open');
  }

  function closeDeleteMsgConfirm() {
    _pendingDeleteMsgId = null;
    _pendingDeleteRow   = null;
    const overlay = document.getElementById('deleteMsgOverlay');
    if (overlay) overlay.classList.remove('open');
  }

  async function confirmDeleteMessagePair() {
    if (!_pendingDeleteMsgId || !currentConversationId) return;
    const msgId = _pendingDeleteMsgId;
    const row   = _pendingDeleteRow;
    closeDeleteMsgConfirm();

    try {
      const res = await fetch(
        `/api/conversations/${currentConversationId}/messages/${msgId}`,
        { method: 'DELETE' }
      );
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      // Remove every row the server actually deleted (both halves of the pair).
      const deletedIds = new Set(data.deleted_ids || []);
      messagesContainer.querySelectorAll('.message-row').forEach((el) => {
        if (deletedIds.has(el.dataset.msgId)) el.remove();
      });

      // Safety net for rows that were rendered before their id was known.
      if (row && row.parentNode) row.remove();

      if (!messagesContainer.querySelector('.message-row')) {
        renderMessages([]);
      }
    } catch (err) {
      console.error('Failed to delete message pair:', err);
      alert('Failed to delete message: ' + err.message);
    }
  }

  // Wire up delete-message-pair modal buttons after DOM is ready
  window.addEventListener('DOMContentLoaded', () => {
    const confirmBtn = document.getElementById('deleteMsgConfirmBtn');
    const cancelBtns = [
      document.getElementById('deleteMsgCancelBtn'),
      document.getElementById('deleteMsgCancelBtn2')
    ];
    const overlay    = document.getElementById('deleteMsgOverlay');
    if (confirmBtn) confirmBtn.addEventListener('click', confirmDeleteMessagePair);
    cancelBtns.forEach((btn) => {
      if (btn) btn.addEventListener('click', closeDeleteMsgConfirm);
    });
    if (overlay)    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeDeleteMsgConfirm();
    });
  });

  // --------------------------------------------------------------------------
  // File Attachments (Plus Icon)
  // --------------------------------------------------------------------------
  async function handleFileUpload(e) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        });
        if (res.ok) {
          const meta = await res.json();
          attachedFiles.push(meta);
          renderAttachmentChips();
        } else {
          alert(`Failed to upload ${file.name}`);
        }
      } catch (err) {
        console.error('File upload error:', err);
      }
    }

    filePickerInput.value = '';
  }

  function renderAttachmentChips() {
    attachmentsTray.innerHTML = '';
    attachedFiles.forEach((file, index) => {
      const chip = document.createElement('div');
      chip.className = 'attachment-chip';
      chip.innerHTML = `
        <span>${file.filename} (${file.size_str})</span>
        <button class="remove-chip-btn" title="Remove attachment">&times;</button>
      `;
      chip.querySelector('.remove-chip-btn').addEventListener('click', () => {
        attachedFiles.splice(index, 1);
        renderAttachmentChips();
      });
      attachmentsTray.appendChild(chip);
    });
  }

  // --------------------------------------------------------------------------
  // Chat Streaming & Sending
  // --------------------------------------------------------------------------
  async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text && attachedFiles.length === 0) return;
    if (isGenerating) return;

    const selected = modelSelector.value || 'ollama:llama3.2:1b';
    const [provider, ...rest] = selected.split(':');
    const model = rest.join(':');

    // Create message payload
    const payload = {
      conversation_id: currentConversationId,
      message: text,
      attachments: [...attachedFiles],
      use_web_search: webSearchEnabled,
      web_search_results_count: parseInt((document.getElementById('settingWebSearchCount') || {value: '10'}).value, 10) || 10,
      append_chat: appendChatEnabled,
      provider: provider,
      model: model,
      agent_mode: agentModeEnabled,
      project_id: currentProjectId
    };

    // Render User message
    const userBubble = appendMessageBubble('user', text, { attachments: payload.attachments });
    const userRow = userBubble.closest('.message-row');

    // Reset input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    attachedFiles = [];
    renderAttachmentChips();

    // Prepare Assistant placeholder
    const botBubble = appendMessageBubble('assistant', '...');
    const botRow = botBubble.closest('.message-row');
    const botContentDiv = botBubble.querySelector('.bubble-content');

    // Update generating state
    isGenerating = true;
    currentAgentTaskId = null;
    btnSendMessage.innerHTML = 'Stop';
    btnSendMessage.title = 'Stop generating';

    activeAbortController = new AbortController();
    let accumulatedText = '';
    let agentErrorText = '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: activeAbortController.signal
      });

      if (!response.ok) {
        let errDetail = `Server returned ${response.status}`;
        try {
          const errData = await response.json();
          if (errData && errData.detail) errDetail = errData.detail;
        } catch (_) {}
        throw new Error(errDetail);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep trailing incomplete segment

        for (const line of lines) {
          if (!line.trim().startsWith('data: ')) continue;
          const jsonStr = line.trim().slice(6);
          try {
            const event = JSON.parse(jsonStr);

            if (event.type === 'user_message') {
              // The server has persisted the user turn and may have created the
              // conversation (first message). Keep both sides in sync.
              if (!currentConversationId && event.conversation_id) {
                currentConversationId = event.conversation_id;
              }
              setMessageId(userRow, event.message_id);
            } else if (event.type === 'search_results') {
              const srCard = document.createElement('div');
              srCard.className = 'search-citations';
              let citationsHtml = `<div class="citation-header">Web Search Citations:</div>`;
              event.results.forEach((r, idx) => {
                citationsHtml += `<div>[${idx + 1}] <a class="citation-link" href="${r.url}" target="_blank">${r.title}</a></div>`;
              });
              srCard.innerHTML = citationsHtml;
              botBubble.insertBefore(srCard, botContentDiv);
            } else if (event.type === 'agent_start') {
              currentAgentTaskId = event.task_id;
              const banner = document.createElement('div');
              banner.className = 'agent-banner';
              const stepLimit = event.max_iterations > 0 ? `${event.max_iterations} max steps` : 'unlimited steps';
              const permissionLabel = event.permission_mode === 'always_ask' ? 'Always Ask' : 'Allow All';
              banner.innerHTML = `<div class="agent-banner-dot"></div><span>Agent Mode Active: Autonomous Execution (${stepLimit} · ${permissionLabel})</span>`;
              botBubble.insertBefore(banner, botContentDiv);
              botContentDiv.innerHTML = '<em>Agent started. Planning the first step...</em>';
            } else if (event.type === 'permission_request') {
              enqueuePermissionRequest(event);
            } else if (event.type === 'permission_resolved') {
              handlePermissionResolved(event);
            } else if (event.type === 'agent_step') {
              let stepPill = botBubble.querySelector('.agent-step-indicator');
              if (!stepPill) {
                stepPill = document.createElement('div');
                stepPill.className = 'agent-step-indicator';
                botBubble.insertBefore(stepPill, botContentDiv);
              }
              stepPill.innerHTML = `<span>⚙</span> <span>${escapeHtml(event.message)}</span>`;
              scrollToBottom();
            } else if (event.type === 'agent_thought') {
              const thought = document.createElement('div');
              thought.className = 'agent-thought-block';
              thought.innerHTML = `<strong>Reasoning:</strong><br>${renderMarkdown(event.content)}`;
              botBubble.insertBefore(thought, botContentDiv);
              scrollToBottom();
            } else if (event.type === 'tool_call') {
              const card = document.createElement('div');
              card.className = 'tool-card running open';
              card.id = `tool-${event.call_id}`;

              let badgeClass = 'terminal';
              if (event.tool_name.includes('file')) badgeClass = 'filesystem';
              else if (event.tool_name.includes('docx')) badgeClass = 'docx';
              else if (event.tool_name.includes('image')) badgeClass = 'vision';

              const argsStr = JSON.stringify(event.arguments, null, 2);

              card.innerHTML = `
                <div class="tool-card-header" onclick="this.parentElement.classList.toggle('open')">
                  <div class="tool-card-header-left">
                    <span class="tool-badge ${badgeClass}">${escapeHtml(event.tool_name)}</span>
                    <span class="tool-card-title">${escapeHtml(getToolSummary(event.tool_name, event.arguments))}</span>
                  </div>
                  <div class="tool-card-header-right">
                    <span class="tool-duration-pill">executing...</span>
                    <div class="tool-status-dot running"></div>
                    <span class="tool-toggle-icon">&#9662;</span>
                  </div>
                </div>
                <div class="tool-card-body">
                  <div class="tool-section-label">Input Arguments:</div>
                  <pre class="tool-code-preview"><code>${escapeHtml(argsStr)}</code></pre>
                  <div class="tool-output-section" style="display: none;">
                    <div class="tool-section-label">Execution Result:</div>
                    <pre class="tool-code-preview result-preview"><code></code></pre>
                  </div>
                </div>
              `;
              botBubble.insertBefore(card, botContentDiv);
              scrollToBottom();
            } else if (event.type === 'tool_result') {
              const card = document.getElementById(`tool-${event.call_id}`);
              if (card) {
                card.classList.remove('running');
                const isSuccess = event.result && event.result.success !== false;
                if (!isSuccess) card.classList.add('error');

                // Only record file changes after the tool actually succeeds.
                if (isSuccess && event.arguments &&
                    (event.tool_name.includes('file') || event.tool_name.includes('edit') || event.tool_name.includes('write'))) {
                  const targetPath = event.arguments.file_path || event.arguments.target_path || event.arguments.path;
                  if (targetPath) {
                    let action = 'modified';
                    if (event.tool_name === 'write_file') action = 'created';
                    else if (event.tool_name === 'delete_file') action = 'deleted';
                    modifiedFilesMap.set(targetPath, { action, tool: event.tool_name, timestamp: Date.now() });
                    updateModifiedFilesBadge();
                  }
                }

                const statusDot = card.querySelector('.tool-status-dot');
                if (statusDot) {
                  statusDot.className = `tool-status-dot ${isSuccess ? 'success' : 'error'}`;
                }
                const durPill = card.querySelector('.tool-duration-pill');
                if (durPill) {
                  durPill.textContent = `${event.duration_sec || 0}s`;
                }
                const outputSec = card.querySelector('.tool-output-section');
                const preview = card.querySelector('.result-preview code');
                if (outputSec && preview) {
                  outputSec.style.display = 'block';
                  preview.textContent = JSON.stringify(event.result, null, 2);
                }
              }
              scrollToBottom();
            } else if (event.type === 'chunk') {
              accumulatedText += event.content;
              botContentDiv.innerHTML = renderMarkdown(accumulatedText);
              highlightCodeBlocks(botBubble);
              scrollToBottom();
            } else if (event.type === 'done') {
              clearPermissionPrompts();
              sessionTokens += (event.total_tokens || 0);
              sessionTokensCount.textContent = `${sessionTokens} tokens`;

              const doneStatus = event.status || 'completed';

              if (doneStatus === 'failed') {
                const message = event.error || agentErrorText || event.final_answer ||
                  'The agent stopped before completing the task.';
                botContentDiv.innerHTML = `
                  <div class="agent-error-block">
                    <div class="agent-error-title">Agent task failed</div>
                    <div>${escapeHtml(message)}</div>
                  </div>`;
              } else if (doneStatus === 'cancelled') {
                botContentDiv.innerHTML = `
                  <div class="agent-error-block cancelled">
                    <div class="agent-error-title">Agent task cancelled</div>
                    <div>The task was stopped before it could finish.</div>
                  </div>`;
              } else if (event.final_answer && !accumulatedText) {
                // If agent mode produced a final answer and chunk was not sent
                botContentDiv.innerHTML = renderMarkdown(event.final_answer);
                highlightCodeBlocks(botBubble);
              }

              // Append metrics footnote
              const metaDiv = document.createElement('div');
              metaDiv.className = 'bubble-meta';
              const statusLabel = doneStatus !== 'completed'
                ? `<span>&bull; ${escapeHtml(doneStatus.replace(/_/g, ' '))}</span>`
                : '';
              metaDiv.innerHTML = `
                <span>${event.duration_sec}s (${event.tokens_per_sec} tok/s)</span>
                <span>&bull;</span>
                <span>${event.prompt_tokens} in / ${event.completion_tokens} out</span>
                ${event.iterations ? `<span>&bull; ${event.iterations} step(s)</span>` : ''}
                ${statusLabel}
                ${event.estimated_cost > 0 ? `<span>&bull; $${event.estimated_cost.toFixed(4)}</span>` : ''}
              `;
              botBubble.appendChild(metaDiv);

              // The reply has now been saved, so make it deletable as a pair too.
              setMessageId(botRow, event.message_id);

              // Update active conversation title in sidebar if updated
              fetchConversations();
            } else if (event.type === 'error') {
              clearPermissionPrompts();
              agentErrorText = event.error || 'The agent stopped with an unknown error.';
              botContentDiv.innerHTML = `
                <div class="agent-error-block">
                  <div class="agent-error-title">Agent stopped</div>
                  <div>${escapeHtml(agentErrorText)}</div>
                </div>`;
              const stepPill = botBubble.querySelector('.agent-step-indicator');
              if (stepPill) {
                stepPill.innerHTML = '<span>⚠</span> <span>Agent stopped with an error</span>';
              }
            }
          } catch (pe) {
            console.warn('SSE parse error:', pe);
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        botContentDiv.innerHTML += `<div style="color: #f87171; margin-top: 8px;">Request failed: ${err.message}</div>`;
      }
    } finally {
      isGenerating = false;
      currentAgentTaskId = null;
      clearPermissionPrompts();
      btnSendMessage.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"></line>
          <polyline points="5 12 12 5 19 12"></polyline>
        </svg>
      `;
      btnSendMessage.title = 'Send (Enter)';
      activeAbortController = null;
      scrollToBottom();
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function getToolSummary(name, args) {
    if (!args) return name;
    if (name === 'run_terminal') return args.command || name;
    if (name === 'read_file' || name === 'write_file' || name === 'edit_file') return args.path || name;
    if (name === 'list_files') return args.directory || '.';
    if (name === 'manage_docx') return `${args.action} on ${args.file_path || ''}`;
    if (name === 'analyze_image') return `${args.mode || 'general'}: ${args.image_path || ''}`;
    return name;
  }

  function stopGeneration() {
    if (activeAbortController) {
      activeAbortController.abort();
    }
    clearPermissionPrompts();
    if (currentAgentTaskId) {
      fetch(`/api/agent/cancel/${currentAgentTaskId}`, { method: 'POST' }).catch(() => {});
      currentAgentTaskId = null;
    }
  }

  // --------------------------------------------------------------------------
  // Export Chat
  // --------------------------------------------------------------------------
  async function handleExportChat() {
    if (!currentConversationId) return;
    const choice = confirm('Press OK to export to DOCX file, or Cancel to export to Markdown file.');
    const format = choice ? 'docx' : 'md';

    try {
      if (format === 'docx') {
        window.open(`/api/conversations/${currentConversationId}/export?format=docx`, '_blank');
      } else {
        const res = await fetch(`/api/conversations/${currentConversationId}/export?format=md`, { method: 'POST' });
        const data = await res.json();
        const blob = new Blob([data.markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      alert(`Export error: ${err.message}`);
    }
  }

  // --------------------------------------------------------------------------
  // Agent Permission Approval
  // --------------------------------------------------------------------------
  function setPermissionButtonsDisabled(disabled) {
    [btnDenyPermission, btnAlwaysAllowPermission, btnAllowPermission].forEach((btn) => {
      if (btn) btn.disabled = disabled;
    });
  }

  function setPermissionToolCardState(callId, state) {
    if (!callId) return;
    const card = document.getElementById(`tool-${callId}`);
    if (!card) return;

    const pill = card.querySelector('.tool-duration-pill');
    card.classList.toggle('permission-waiting', state === 'waiting');

    if (!pill) return;
    if (state === 'waiting') {
      pill.textContent = 'waiting for approval...';
    } else if (state === 'allow') {
      pill.textContent = 'executing...';
    } else if (state === 'deny') {
      pill.textContent = 'denied';
    } else if (state === 'timeout') {
      pill.textContent = 'timed out';
    } else if (state === 'cancelled') {
      pill.textContent = 'cancelled';
    }
  }

  function enqueuePermissionRequest(event) {
    if (!event || !event.request_id) return;
    setPermissionToolCardState(event.call_id, 'waiting');
    permissionQueue.push(event);
    showNextPermissionRequest();
  }

  function showNextPermissionRequest() {
    if (activePermissionRequest || permissionResponding) return;

    const next = permissionQueue.shift();
    if (!next) {
      permissionModal.classList.remove('open');
      return;
    }

    activePermissionRequest = next;
    const details = next.details || {};
    const toolName = next.tool_name || 'tool';
    const risk = String(details.risk || 'medium').toLowerCase();
    const safeRisk = ['low', 'medium', 'high'].includes(risk) ? risk : 'medium';

    permissionSubtitle.textContent = `The agent is paused before using ${toolName}.`;
    permissionToolName.textContent = toolName;
    permissionTitle.textContent = details.title || `Run ${toolName}`;
    permissionDetail.textContent = details.detail || '';
    permissionRisk.className = `permission-risk ${safeRisk}`;
    permissionRisk.textContent = `${safeRisk} risk`;

    const preview = details.preview || '';
    if (preview) {
      permissionPreviewWrapper.style.display = '';
      permissionPreviewLabel.textContent = details.preview_label || 'Details';
      permissionPreview.textContent = preview;
    } else {
      permissionPreviewWrapper.style.display = 'none';
      permissionPreviewLabel.textContent = '';
      permissionPreview.textContent = '';
    }

    setPermissionButtonsDisabled(false);
    permissionModal.classList.add('open');
  }

  async function respondToPermission(decision) {
    if (!activePermissionRequest || permissionResponding) return;

    permissionResponding = true;
    setPermissionButtonsDisabled(true);
    const requestId = activePermissionRequest.request_id;

    try {
      const res = await fetch(`/api/agent/permission/${encodeURIComponent(requestId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision })
      });

      // A 404 means the request timed out or was already resolved elsewhere.
      if (!res.ok && res.status !== 404) {
        let detail = `Server returned ${res.status}`;
        try {
          const data = await res.json();
          if (data && data.detail) detail = data.detail;
        } catch (_) {}
        throw new Error(detail);
      }

      permissionResponding = false;
      activePermissionRequest = null;
      permissionModal.classList.remove('open');
      setPermissionButtonsDisabled(false);
      showNextPermissionRequest();
    } catch (e) {
      permissionResponding = false;
      setPermissionButtonsDisabled(false);
      alert('Could not send permission decision: ' + e.message);
    }
  }

  function handlePermissionResolved(event) {
    if (!event || !event.request_id) return;

    const decision = String(event.decision || 'deny');
    const cardState = ['allow', 'always_allow', 'allow_all'].includes(decision)
      ? 'allow'
      : decision;
    setPermissionToolCardState(event.call_id, cardState);

    permissionQueue = permissionQueue.filter((req) => req.request_id !== event.request_id);

    if (activePermissionRequest && activePermissionRequest.request_id === event.request_id) {
      permissionResponding = false;
      activePermissionRequest = null;
      permissionModal.classList.remove('open');
      setPermissionButtonsDisabled(false);
      showNextPermissionRequest();
    }
  }

  function clearPermissionPrompts() {
    const outstanding = [activePermissionRequest, ...permissionQueue];
    outstanding.forEach((request) => {
      if (request && request.call_id) {
        setPermissionToolCardState(request.call_id, 'cancelled');
      }
    });
    permissionQueue = [];
    activePermissionRequest = null;
    permissionResponding = false;
    setPermissionButtonsDisabled(false);
    permissionModal.classList.remove('open');
  }

  // --------------------------------------------------------------------------
  // Settings & Analytics
  // --------------------------------------------------------------------------
  async function loadSettings() {
    try {
      const res = await fetch('/api/settings');
      const cfg = await res.json();
      if (cfg.selected_provider && cfg.selected_model) {
        savedModelSelection = `${cfg.selected_provider}:${cfg.selected_model}`;
      }
      settingOllamaUrl.value = cfg.ollama_url || 'http://localhost:11434';
      settingOpenAiKey.placeholder = cfg.masked_api_keys?.openai || 'sk-...';
      settingAnthropicKey.placeholder = cfg.masked_api_keys?.anthropic || 'sk-ant-...';
      settingGeminiKey.placeholder = cfg.masked_api_keys?.gemini || 'AIzaSy...';
      settingGroqKey.placeholder = cfg.masked_api_keys?.groq || 'gsk_...';
      settingOpenRouterKey.placeholder = cfg.masked_api_keys?.openrouter || 'sk-or-...';
      if (settingVisionModel) settingVisionModel.value = cfg.vision_model || '';
      if (settingKeepAlive) settingKeepAlive.value = cfg.keep_alive || '30m';
      if (settingAgentWorkspace) settingAgentWorkspace.value = cfg.agent_workspace || '';
      if (settingAgentPermissionMode) {
        settingAgentPermissionMode.value = cfg.agent_permission_mode === 'always_ask'
          ? 'always_ask'
          : 'allow_all';
      }
      settingTokenBudget.value = cfg.token_budget_limit || 100000;
      const wsSlider = document.getElementById('settingWebSearchCount');
      const wsDisplay = document.getElementById('webSearchCountDisplay');
      if (wsSlider && cfg.web_search_results_count) {
        wsSlider.value = cfg.web_search_results_count;
        if (wsDisplay) wsDisplay.textContent = cfg.web_search_results_count;
      }
      if (cfg.remember_context !== undefined && btnToggleAppendChat) {
        appendChatEnabled = Boolean(cfg.remember_context);
        btnToggleAppendChat.classList.toggle('active', appendChatEnabled);
      }
      if (cfg.agent_mode !== undefined && btnToggleAgentMode) {
        agentModeEnabled = Boolean(cfg.agent_mode);
        btnToggleAgentMode.classList.toggle('active', agentModeEnabled);
      }
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
  }

  async function saveSettings() {
    const wsSlider = document.getElementById('settingWebSearchCount');
    const payload = {
      settings: {
        ollama_url: settingOllamaUrl.value.trim() || 'http://localhost:11434',
        token_budget_limit: parseInt(settingTokenBudget.value, 10) || 100000,
        web_search_results_count: wsSlider ? (parseInt(wsSlider.value, 10) || 10) : 10,
        vision_model: settingVisionModel ? settingVisionModel.value.trim() : '',
        keep_alive: settingKeepAlive ? settingKeepAlive.value : '30m',
        agent_workspace: settingAgentWorkspace ? settingAgentWorkspace.value.trim() : '',
        agent_permission_mode: settingAgentPermissionMode ? settingAgentPermissionMode.value : 'allow_all',
        agent_mode: agentModeEnabled,
        api_keys: {}
      }
    };

    if (settingOpenAiKey.value.trim()) payload.settings.api_keys.openai = settingOpenAiKey.value.trim();
    if (settingAnthropicKey.value.trim()) payload.settings.api_keys.anthropic = settingAnthropicKey.value.trim();
    if (settingGeminiKey.value.trim()) payload.settings.api_keys.gemini = settingGeminiKey.value.trim();
    if (settingGroqKey.value.trim()) payload.settings.api_keys.groq = settingGroqKey.value.trim();
    if (settingOpenRouterKey.value.trim()) payload.settings.api_keys.openrouter = settingOpenRouterKey.value.trim();

    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      settingsModal.classList.remove('open');
      await loadModels();
      alert('Settings saved successfully!');
    } catch (e) {
      alert('Failed to save settings: ' + e.message);
    }
  }

  async function updateAnalyticsUI() {
    try {
      const res = await fetch('/api/analytics');
      const data = await res.json();
      const overall = data.summary?.overall || {};
      const budget = data.budget_status || {};

      statTotalTokens.textContent = (overall.grand_total_tokens || 0).toLocaleString();
      statEstimatedCost.textContent = `$${(overall.total_estimated_cost || 0).toFixed(4)}`;
      statPromptTokens.textContent = (overall.total_prompt_tokens || 0).toLocaleString();
      statCompletionTokens.textContent = (overall.total_completion_tokens || 0).toLocaleString();

      const pct = budget.percentage_used || 0;
      budgetProgressFill.style.width = `${pct}%`;
      budgetProgressFill.className = 'progress-bar-fill' + (pct >= 90 ? ' danger' : pct >= 75 ? ' warning' : '');

      const limit = budget.budget_limit || 100000;
      const used = budget.tokens_used || 0;
      budgetUsageLabel.textContent = `${used.toLocaleString()} / ${limit.toLocaleString()} (${pct}%)`;

      const remaining = budget.remaining_tokens !== null ? budget.remaining_tokens.toLocaleString() : 'Unlimited';
      budgetRemainingLabel.textContent = `Remaining: ${remaining} tokens`;
    } catch (e) {
      console.error('Failed to load analytics:', e);
    }
  }

  // Start app
  document.addEventListener('DOMContentLoaded', init);
})();
