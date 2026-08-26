/**
 * Multimodal AI Assistant - Core App State & UI Manager
 */

// Universal Fetch Interceptor for ngrok & mobile proxy support
(function() {
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        options = options || {};
        options.headers = options.headers || {};
        
        if (options.headers instanceof Headers) {
            options.headers.set('ngrok-skip-browser-warning', 'true');
        } else if (Array.isArray(options.headers)) {
            options.headers.push(['ngrok-skip-browser-warning', 'true']);
        } else {
            options.headers['ngrok-skip-browser-warning'] = 'true';
        }
        
        if (!options.credentials) {
            options.credentials = 'same-origin';
        }
        
        return originalFetch.call(this, url, options);
    };
})();

const AppState = {
    currentConversationId: null,
    currentModel: 'gemini-2.5-flash',
    preferredLanguage: 'auto',
    theme: 'dark',
    activeAttachments: [],
    isGenerating: false,
    abortController: null
};


// Toast Notifications
function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'error' ? '⚠️' : (type === 'success' ? '✅' : '✨');
    toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// HTML Escaping Helper
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('chatbot_theme') || 'dark';
    setTheme(savedTheme);
}

function setTheme(theme) {
    AppState.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('chatbot_theme', theme);
    
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
        themeToggleBtn.title = theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme';
    }
}

function toggleTheme() {
    setTheme(AppState.theme === 'dark' ? 'light' : 'dark');
}

// Modal Management
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('open');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('open');
    }
}

// Mobile Sidebar Drawer Toggle
function toggleMobileSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
}

// AI Image Generation Studio
const ImageStudio = {
    async generate() {
        const promptInput = document.getElementById('imgGenPromptInput');
        const ratioSelect = document.getElementById('imgGenRatioSelect');
        const prompt = promptInput ? promptInput.value.trim() : '';
        const ratio = ratioSelect ? ratioSelect.value : '1:1';
        const resultContainer = document.getElementById('imgGenResult');
        const btn = document.getElementById('btnDoImgGen');

        if (!prompt) {
            showToast('Please enter an image prompt', 'error');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> Generating Image...';
        resultContainer.innerHTML = `
            <div style="text-align: center; padding: 30px; color: var(--text-primary);">
                <div class="pulse-dot" style="margin: 0 auto 12px;"></div>
                <div style="font-weight: 700; font-size: 15px;">Creating artwork with Google AI...</div>
            </div>
        `;

        try {
            const apiKey = localStorage.getItem('gemini_custom_api_key') || '';
            const res = await fetch('/api/images/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, aspect_ratio: ratio, api_key: apiKey })
            });
            const data = await res.json();
            if (data.success) {
                resultContainer.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 14px; align-items: center; margin-top: 10px;">
                        <img src="${data.image_url}" alt="${escapeHtml(prompt)}" style="max-width: 100%; max-height: 380px; border-radius: 12px; border: 2px solid var(--border-medium); box-shadow: var(--shadow-md);">
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <a href="${data.image_url}" download="${data.filename}" class="msg-btn btn-compare">⬇️ Download Image</a>
                            <button class="msg-btn" onclick="ImageStudio.insertIntoChat('${data.image_url}', '${escapeHtml(prompt)}')">💬 Post to Chat</button>
                        </div>
                    </div>
                `;
                showToast('Image created successfully!', 'success');
            } else {
                resultContainer.innerHTML = `<div class="auth-error-banner" style="margin-top: 14px;">⚠️ ${escapeHtml(data.error || 'Failed to generate image')}</div>`;
            }
        } catch (err) {
            resultContainer.innerHTML = `<div class="auth-error-banner" style="margin-top: 14px;">⚠️ Request error: ${escapeHtml(err.message)}</div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '✨ Generate Artwork';
        }
    },
    insertIntoChat(imgUrl, prompt) {
        closeModal('imageGenModal');
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.value = `Here is the generated image for: "${prompt}"\n\n![${prompt}](${imgUrl})`;
            if (typeof sendMessage === 'function') {
                sendMessage();
            }
        }
    }
};

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    // Close modals on clicking backdrop
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                backdrop.classList.remove('open');
            }
        });
    });

    // Close modals on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-backdrop.open').forEach(m => m.classList.remove('open'));
        }
    });
});

function togglePassword(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (!input) return;

    if (input.type === 'password') {
        input.type = 'text';
        if (icon) {
            icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>';
        }
    } else {
        input.type = 'password';
        if (icon) {
            icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
        }
    }
}

