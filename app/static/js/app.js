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
  // Conversations (Chat History)
  // --------------------------------------------------------------------------
  async function fetchConversations() {
    try {
      const res = await fetch('/api/conversations');
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
        body: JSON.stringify({ title: 'New Chat', provider, model })
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
    messagesContainer.appendChild(row);

    highlightCodeBlocks(bubble);
    scrollToBottom();
    return bubble;
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

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
      append_chat: appendChatEnabled,
      provider: provider,
      model: model
    };

    // Render User message
    appendMessageBubble('user', text, { attachments: payload.attachments });

    // Reset input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    attachedFiles = [];
    renderAttachmentChips();

    // Prepare Assistant placeholder
    const botBubble = appendMessageBubble('assistant', '...');
    const botContentDiv = botBubble.querySelector('.bubble-content');

    // Update generating state
    isGenerating = true;
    btnSendMessage.innerHTML = 'Stop';
    btnSendMessage.title = 'Stop generating';

    activeAbortController = new AbortController();
    let accumulatedText = '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: activeAbortController.signal
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
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

            if (event.type === 'search_results') {
              const srCard = document.createElement('div');
              srCard.className = 'search-citations';
              let citationsHtml = `<div class="citation-header">Web Search Citations:</div>`;
              event.results.forEach((r, idx) => {
                citationsHtml += `<div>[${idx + 1}] <a class="citation-link" href="${r.url}" target="_blank">${r.title}</a></div>`;
              });
              srCard.innerHTML = citationsHtml;
              botBubble.insertBefore(srCard, botContentDiv);
            } else if (event.type === 'chunk') {
              accumulatedText += event.content;
              botContentDiv.innerHTML = renderMarkdown(accumulatedText);
              highlightCodeBlocks(botBubble);
              scrollToBottom();
            } else if (event.type === 'done') {
              sessionTokens += (event.total_tokens || 0);
              sessionTokensCount.textContent = `${sessionTokens} tokens`;

              // Append metrics footnote
              const metaDiv = document.createElement('div');
              metaDiv.className = 'bubble-meta';
              metaDiv.innerHTML = `
                <span>${event.duration_sec}s (${event.tokens_per_sec} tok/s)</span>
                <span>&bull;</span>
                <span>${event.prompt_tokens} in / ${event.completion_tokens} out</span>
                ${event.estimated_cost > 0 ? `<span>&bull; $${event.estimated_cost.toFixed(4)}</span>` : ''}
              `;
              botBubble.appendChild(metaDiv);

              // Update active conversation title in sidebar if updated
              fetchConversations();
            } else if (event.type === 'error') {
              botContentDiv.innerHTML += `<div style="color: #f87171; margin-top: 8px;">Error: ${event.error}</div>`;
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

  function stopGeneration() {
    if (activeAbortController) {
      activeAbortController.abort();
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
  // Settings & Analytics
  // --------------------------------------------------------------------------
  async function loadSettings() {
    try {
      const res = await fetch('/api/settings');
      const cfg = await res.json();
      settingOllamaUrl.value = cfg.ollama_url || 'http://localhost:11434';
      settingOpenAiKey.placeholder = cfg.masked_api_keys?.openai || 'sk-...';
      settingAnthropicKey.placeholder = cfg.masked_api_keys?.anthropic || 'sk-ant-...';
      settingGeminiKey.placeholder = cfg.masked_api_keys?.gemini || 'AIzaSy...';
      settingGroqKey.placeholder = cfg.masked_api_keys?.groq || 'gsk_...';
      settingOpenRouterKey.placeholder = cfg.masked_api_keys?.openrouter || 'sk-or-...';
      settingTokenBudget.value = cfg.token_budget_limit || 100000;
      if (cfg.remember_context !== undefined && btnToggleAppendChat) {
        appendChatEnabled = Boolean(cfg.remember_context);
        btnToggleAppendChat.classList.toggle('active', appendChatEnabled);
      }
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
  }

  async function saveSettings() {
    const payload = {
      settings: {
        ollama_url: settingOllamaUrl.value.trim() || 'http://localhost:11434',
        token_budget_limit: parseInt(settingTokenBudget.value, 10) || 100000,
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
