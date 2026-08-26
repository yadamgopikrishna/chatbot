/**
 * Multimodal AI Assistant - Universal Chat & Streaming Engine
 */

let chartInstances = {};

// Initialize Chat Module
document.addEventListener('DOMContentLoaded', () => {
    initComposer();
    initDragAndDrop();
    loadConversations();
});

// Markdown Parser Helper
function renderMarkdown(rawText) {
    if (!rawText) return '';
    let text = escapeHtml(rawText);

    // Code blocks with syntax copy buttons: ```lang\ncode\n```
    text = text.replace(/```([a-zA-Z0-9_\-\+]*)\n([\s\S]*?)```/g, (match, lang, code) => {
        const langLabel = lang ? lang.toUpperCase() : 'CODE';
        const codeId = 'code_' + Math.random().toString(36).substring(2, 9);
        return `
        <div class="code-block-wrapper">
            <div class="code-header">
                <span>${langLabel}</span>
                <button class="code-copy-btn" onclick="copyCodeBlock('${codeId}')">📋 Copy</button>
            </div>
            <pre><code id="${codeId}">${code.trim()}</code></pre>
        </div>`;
    });

    // Inline code: `code`
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Blockquotes
    text = text.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

    // Bold and Italic
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Tables
    text = text.replace(/((?:\|[^\n]+\|\r?\n?)+)/g, (match) => {
        const rows = match.trim().split('\n');
        let tableHtml = '<table>';
        rows.forEach((row, idx) => {
            if (row.includes('---')) return; // skip markdown divider
            const cols = row.split('|').filter((c, i, a) => i > 0 && i < a.length - 1);
            if (idx === 0) {
                tableHtml += '<thead><tr>' + cols.map(c => `<th>${c.trim()}</th>`).join('') + '</tr></thead><tbody>';
            } else {
                tableHtml += '<tr>' + cols.map(c => `<td>${c.trim()}</td>`).join('') + '</tr>';
            }
        });
        tableHtml += '</tbody></table>';
        return tableHtml;
    });

    // Unordered lists
    text = text.replace(/^\s*[\-\*]\s+(.*$)/gim, '<ul><li>$1</li></ul>');
    text = text.replace(/<\/ul>\s*<ul>/g, '');

    // Paragraphs
    text = text.replace(/\n\n+/g, '</p><p>');
    text = `<p>${text}</p>`;

    // If text contains API Key error notice, render direct button
    if (text.includes('API Key Notice') || text.includes('API Configuration Notice') || text.includes('Invalid API Key')) {
        text += `
        <div style="margin-top: 14px;">
            <button class="btn-new-chat" style="margin: 0; padding: 7px 16px; font-size: 13px;" onclick="openModal('settingsModal'); SettingsManager.loadSettings();">
                ⚙️ Configure API Key Now
            </button>
        </div>`;
    }

    return text;
}

// Copy Code Block
function copyCodeBlock(codeId) {
    const el = document.getElementById(codeId);
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(() => {
        showToast('Code copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy code', 'error');
    });
}

// Copy Message
function copyMessage(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Message copied to clipboard!', 'success');
    });
}

// Composer Auto-expand & Events
function initComposer() {
    const textarea = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');

    if (!textarea) return;

    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 160) + 'px';
    });

    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    if (sendBtn) {
        sendBtn.addEventListener('click', () => {
            if (AppState.isGenerating) {
                stopGeneration();
            } else {
                handleSend();
            }
        });
    }

    // Model Selector
    const modelSelect = document.getElementById('modelSelect');
    if (modelSelect) {
        modelSelect.addEventListener('change', (e) => {
            AppState.currentModel = e.target.value;
            showToast(`Switched model to ${e.target.options[e.target.selectedIndex].text}`, 'info');
        });
    }

    // Language Selector
    const langSelect = document.getElementById('langSelect');
    if (langSelect) {
        langSelect.addEventListener('change', (e) => {
            AppState.preferredLanguage = e.target.value;
            fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ preferred_lang: e.target.value })
            });
            showToast(`Language preference: ${e.target.options[e.target.selectedIndex].text}`, 'info');
        });
    }
}

// Drag & Drop for universal file uploads
function initDragAndDrop() {
    const dropzone = document.getElementById('dropzoneOverlay');
    const mainChat = document.querySelector('.main-chat');
    const fileInput = document.getElementById('fileUploadInput');

    if (!dropzone || !mainChat || !fileInput) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        mainChat.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('active');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('active');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files);
        }
    });
}

// Upload Files to server and attach to current composer
async function handleFileUpload(files) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }
    if (AppState.currentConversationId) {
        formData.append('conversation_id', AppState.currentConversationId);
    }

    showToast(`Uploading ${files.length} file(s)...`, 'info');

    try {
        const resp = await fetch('/api/documents/upload', {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();

        if (data.success && data.documents) {
            data.documents.forEach(doc => {
                AppState.activeAttachments.push({
                    name: doc.filename,
                    type: doc.file_type,
                    file_path: doc.file_path,
                    doc_id: doc.doc_id,
                    size: doc.file_size
                });
            });
            renderAttachmentPreview();
            showToast('Files processed and attached successfully!', 'success');
        } else {
            showToast(data.error || 'Failed to upload files', 'error');
        }
    } catch (err) {
        showToast('Error uploading files: ' + err.message, 'error');
    }
}

// Render Attached Files preview strip
function renderAttachmentPreview() {
    const strip = document.getElementById('attachmentStrip');
    if (!strip) return;

    if (AppState.activeAttachments.length === 0) {
        strip.innerHTML = '';
        strip.style.display = 'none';
        return;
    }

    strip.style.display = 'flex';
    strip.innerHTML = AppState.activeAttachments.map((att, idx) => {
        const icon = att.type === 'pdf' ? '📄' : (att.type === 'spreadsheet' ? '📊' : (att.type === 'image' ? '🖼️' : '📝'));
        return `
            <div class="attachment-chip">
                <span>${icon}</span>
                <span>${escapeHtml(att.name)}</span>
                <span class="remove-att-btn" onclick="removeAttachment(${idx})">✕</span>
            </div>
        `;
    }).join('');
}

function removeAttachment(idx) {
    AppState.activeAttachments.splice(idx, 1);
    renderAttachmentPreview();
}

// Main Send Handler (Streaming SSE)
async function handleSend() {
    const textarea = document.getElementById('chatInput');
    const message = textarea.value.trim();
    const attachments = [...AppState.activeAttachments];
    const apiKey = localStorage.getItem('gemini_api_key') || AppState.apiKey || '';

    if (!message && attachments.length === 0) return;
    if (AppState.isGenerating) return;

    // Clear composer input & attachments
    textarea.value = '';
    textarea.style.height = 'auto';
    AppState.activeAttachments = [];
    renderAttachmentPreview();

    // Hide welcome screen
    const welcomeScreen = document.getElementById('welcomeScreen');
    if (welcomeScreen) welcomeScreen.style.display = 'none';

    // Append User message to UI
    appendUserMessage(message, attachments);

    // Prepare Assistant message container
    const msgId = 'msg_' + Date.now();
    const aiBubble = appendAIMessagePlaceholder(msgId);

    // Toggle Send Button to Stop state
    setGeneratingState(true);

    AppState.abortController = new AbortController();

    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                conversation_id: AppState.currentConversationId,
                attachments: attachments,
                model: AppState.currentModel,
                api_key: apiKey
            }),
            signal: AppState.abortController.signal
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let accumulatedText = '';
        let chartData = null;
        let forensicsData = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const payload = JSON.parse(line.substring(6).trim());

                        if (payload.type === 'init') {
                            if (payload.data.conversation_id && !AppState.currentConversationId) {
                                AppState.currentConversationId = payload.data.conversation_id;
                                loadConversations();
                            }
                            if (payload.data.chart_data) chartData = payload.data.chart_data;
                            if (payload.data.forensics) forensicsData = payload.data.forensics;
                        }

                        if (payload.chunk) {
                            accumulatedText += payload.chunk;
                            aiBubble.querySelector('.markdown-body').innerHTML = renderMarkdown(accumulatedText);
                            scrollToBottom();
                        }

                        if (payload.done) {
                            renderPostResponseAddons(aiBubble, accumulatedText, chartData, forensicsData);
                        }
                    } catch (e) {}
                }
            }
        }
    } catch (err) {
        if (err.name !== 'AbortError') {
            aiBubble.querySelector('.markdown-body').innerHTML = `<p style="color: var(--accent-rose);">⚠️ Error: ${escapeHtml(err.message)}</p>`;
        }
    } finally {
        setGeneratingState(false);
        AppState.abortController = null;
    }
}

function setGeneratingState(isGenerating) {
    AppState.isGenerating = isGenerating;
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        if (isGenerating) {
            sendBtn.classList.add('stop');
            sendBtn.innerHTML = '⏹';
            sendBtn.title = 'Stop generating';
        } else {
            sendBtn.classList.remove('stop');
            sendBtn.innerHTML = '➤';
            sendBtn.title = 'Send message';
        }
    }
}

function stopGeneration() {
    if (AppState.abortController) {
        AppState.abortController.abort();
        setGeneratingState(false);
        showToast('Generation stopped.', 'info');
    }
}

// Append User Message to UI
function appendUserMessage(text, attachments) {
    const container = document.getElementById('messagesContainer');
    const msgWrapper = document.createElement('div');
    msgWrapper.className = 'message-wrapper user';

    let attHtml = '';
    if (attachments && attachments.length > 0) {
        attHtml = '<div class="attachment-preview-strip" style="margin-bottom: 6px;">' +
            attachments.map(a => `<div class="attachment-chip">📎 ${escapeHtml(a.name)}</div>`).join('') +
            '</div>';
    }

    msgWrapper.innerHTML = `
        <div class="message-content">
            ${attHtml}
            <div class="message-bubble">${escapeHtml(text)}</div>
        </div>
    `;
    container.appendChild(msgWrapper);
    scrollToBottom();
}

// Append AI Message Placeholder
function appendAIMessagePlaceholder(msgId) {
    const container = document.getElementById('messagesContainer');
    const msgWrapper = document.createElement('div');
    msgWrapper.className = 'message-wrapper ai';
    msgWrapper.id = msgId;

    msgWrapper.innerHTML = `
        <div class="message-avatar ai">✨</div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="markdown-body"><span class="typing-cursor">▋</span></div>
            </div>
            <div class="message-actions">
                <button class="msg-btn" onclick="copyMessageFromEl('${msgId}')">📋 Copy</button>
                <button class="msg-btn" onclick="speakMessageFromEl('${msgId}')">🔊 Listen</button>
            </div>
        </div>
    `;
    container.appendChild(msgWrapper);
    scrollToBottom();
    return msgWrapper;
}

function copyMessageFromEl(msgId) {
    const el = document.getElementById(msgId);
    if (el) {
        const text = el.querySelector('.markdown-body').innerText;
        copyMessage(text);
    }
}

function speakMessageFromEl(msgId) {
    const el = document.getElementById(msgId);
    if (el && window.VoiceAssistant) {
        const text = el.querySelector('.markdown-body').innerText;
        window.VoiceAssistant.speak(text, AppState.preferredLanguage);
    }
}

// Render Post-Response Addons (Citations, Charts, Forensics Gauge)
function renderPostResponseAddons(aiBubble, fullText, chartData, forensicsData) {
    const contentBox = aiBubble.querySelector('.message-content');

    // 1. Citations
    const citationMatches = [...fullText.matchAll(/\[(?:Source:\s*)?([^\]]*?Page\s*(\d+)[^\]]*?)\]/gi)];
    if (citationMatches.length > 0) {
        const strip = document.createElement('div');
        strip.className = 'citations-strip';
        const seen = new Set();
        citationMatches.forEach(m => {
            const label = m[1].trim();
            const page = m[2];
            if (!seen.has(label)) {
                seen.add(label);
                strip.innerHTML += `<div class="citation-chip" onclick="showToast('Referenced from Page ${page}', 'info')">📖 ${escapeHtml(label)}</div>`;
            }
        });
        contentBox.appendChild(strip);
    }

    // 2. Interactive Chart.js
    if (chartData && window.Chart) {
        const chartWrapper = document.createElement('div');
        chartWrapper.style.cssText = 'background: var(--bg-tertiary); padding: 14px; border-radius: 10px; margin-top: 12px; width: 100%; max-width: 500px;';
        const canvasId = 'chart_' + Math.random().toString(36).substring(2, 9);
        chartWrapper.innerHTML = `
            <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px;">📊 ${escapeHtml(chartData.title)}</div>
            <canvas id="${canvasId}" style="max-height: 240px;"></canvas>
        `;
        contentBox.appendChild(chartWrapper);

        setTimeout(() => {
            const ctx = document.getElementById(canvasId).getContext('2d');
            new Chart(ctx, {
                type: chartData.type,
                data: chartData.data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: AppState.theme === 'dark' ? '#f8fafc' : '#0f172a' } } },
                    scales: chartData.type !== 'doughnut' ? {
                        x: { ticks: { color: AppState.theme === 'dark' ? '#94a3b8' : '#475569' } },
                        y: { ticks: { color: AppState.theme === 'dark' ? '#94a3b8' : '#475569' } }
                    } : {}
                }
            });
        }, 100);
    }

    // 3. Forensics Gauge
    if (forensicsData) {
        const fCard = document.createElement('div');
        fCard.className = 'forensics-badge-card';
        const levelClass = forensicsData.ai_probability > 60 ? 'high' : (forensicsData.ai_probability > 30 ? 'medium' : 'low');
        fCard.innerHTML = `
            <div class="forensics-header">
                <strong>🔍 Image Authenticity Analysis: ${escapeHtml(forensicsData.classification)}</strong>
                <span>AI Probability: ${forensicsData.ai_probability}%</span>
            </div>
            <div class="prob-meter">
                <div class="prob-fill ${levelClass}" style="width: ${forensicsData.ai_probability}%"></div>
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">${escapeHtml(forensicsData.limitations_disclaimer)}</div>
        `;
        contentBox.appendChild(fCard);
    }
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

// Conversation Management in Sidebar
async function loadConversations() {
    try {
        const resp = await fetch('/api/conversations');
        const data = await resp.json();
        const nav = document.getElementById('conversationsList');
        if (!nav || !data.conversations) return;

        if (data.conversations.length === 0) {
            nav.innerHTML = '<div style="padding: 12px; color: var(--text-muted); font-size: 13px; text-align: center;">No chat history yet</div>';
            return;
        }

        nav.innerHTML = data.conversations.map(c => `
            <div class="conv-item ${c.conversation_id === AppState.currentConversationId ? 'active' : ''}" onclick="selectConversation('${c.conversation_id}')">
                <span class="conv-title">${escapeHtml(c.title)}</span>
                <div class="conv-actions">
                    <button class="conv-action-btn" onclick="event.stopPropagation(); deleteConv('${c.conversation_id}')" title="Delete">🗑️</button>
                </div>
            </div>
        `).join('');
    } catch (e) {}
}

async function selectConversation(convId) {
    AppState.currentConversationId = convId;
    loadConversations();
    const resp = await fetch(`/api/conversations/${convId}/messages`);
    const data = await resp.json();

    const container = document.getElementById('messagesContainer');
    container.innerHTML = '';
    const welcomeScreen = document.getElementById('welcomeScreen');
    if (welcomeScreen) welcomeScreen.style.display = 'none';

    if (data.messages) {
        data.messages.forEach(msg => {
            if (msg.sender === 'user') {
                appendUserMessage(msg.content, msg.attachments);
            } else {
                const msgId = 'msg_' + Math.random().toString(36).substring(2, 9);
                const bubble = appendAIMessagePlaceholder(msgId);
                bubble.querySelector('.markdown-body').innerHTML = renderMarkdown(msg.content);
                renderPostResponseAddons(bubble, msg.content, msg.chart_data, msg.forensics);
            }
        });
    }
    scrollToBottom();
}

function startNewChat() {
    AppState.currentConversationId = null;
    AppState.activeAttachments = [];
    renderAttachmentPreview();
    const container = document.getElementById('messagesContainer');
    container.innerHTML = `
        <div class="welcome-screen" id="welcomeScreen">
            <div class="welcome-title">What can I help you explore today?</div>
            <div class="welcome-subtitle">Multimodal intelligence for text, images, PDFs, Word documents, Excel spreadsheets, and multilingual conversations.</div>
            <div class="quick-prompts-grid">
                <div class="quick-prompt-card" onclick="setPrompt('Analyze and summarize the main points of this document.')">
                    <div class="quick-prompt-title">📄 Document Summary</div>
                    <div class="quick-prompt-desc">Extract key insights and tables with page citations</div>
                </div>
                <div class="quick-prompt-card" onclick="setPrompt('Inspect this spreadsheet, calculate summary stats, and suggest a chart.')">
                    <div class="quick-prompt-title">📊 Spreadsheet Analytics</div>
                    <div class="quick-prompt-desc">Detect missing values, trends, and visualize metrics</div>
                </div>
                <div class="quick-prompt-card" onclick="setPrompt('ఈ పత్రంలోని ముఖ్యమైన విషయాలను తెలుగులో వివరించండి.')">
                    <div class="quick-prompt-title">🌐 Multilingual Q&A</div>
                    <div class="quick-prompt-desc">Ask in Telugu, Hindi, or any language with native answers</div>
                </div>
                <div class="quick-prompt-card" onclick="setPrompt('Analyze this image, extract text, and check authenticity.')">
                    <div class="quick-prompt-title">🖼️ Vision & Forensics</div>
                    <div class="quick-prompt-desc">OCR, diagram breakdown, and AI generation analysis</div>
                </div>
            </div>
        </div>
    `;
    loadConversations();
}

function setPrompt(text) {
    const input = document.getElementById('chatInput');
    if (input) {
        input.value = text;
        input.focus();
    }
}

async function deleteConv(convId) {
    if (!confirm('Are you sure you want to delete this chat?')) return;
    await fetch(`/api/conversations/${convId}`, { method: 'DELETE' });
    if (AppState.currentConversationId === convId) {
        startNewChat();
    } else {
        loadConversations();
    }
}
