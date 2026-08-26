/**
 * Multimodal AI Assistant - Settings Controller
 */

const SettingsManager = {
    async loadSettings() {
        try {
            const resp = await fetch('/api/settings');
            const data = await resp.json();

            // Populate language select
            const langSelect = document.getElementById('settingsLangSelect');
            if (langSelect && data.languages) {
                langSelect.innerHTML = Object.entries(data.languages).map(([code, name]) => `
                    <option value="${code}" ${data.user_settings.preferred_lang === code ? 'selected' : ''}>${name}</option>
                `).join('');
            }

            // Populate model select
            const modelSelect = document.getElementById('settingsModelSelect');
            if (modelSelect && data.models) {
                modelSelect.innerHTML = Object.entries(data.models).map(([key, model]) => `
                    <option value="${key}" ${AppState.currentModel === key ? 'selected' : ''}>${model.name} (${model.badge})</option>
                `).join('');
            }

            // Populate API Key Input if stored locally
            const apiKeyInput = document.getElementById('apiKeyInput');
            const storedKey = localStorage.getItem('gemini_api_key');
            if (apiKeyInput && storedKey) {
                apiKeyInput.value = storedKey;
            }

            // API Key Status Badge
            const keyStatus = document.getElementById('apiKeyStatus');
            if (keyStatus) {
                if (data.user_settings.has_api_key || storedKey) {
                    const preview = data.user_settings.masked_api_key || (storedKey ? `${storedKey.substring(0,6)}...${storedKey.substring(storedKey.length-4)}` : 'Active');
                    keyStatus.innerHTML = `<span style="color: var(--accent-secondary); font-weight: 600;">● Active (${escapeHtml(preview)})</span>`;
                } else {
                    keyStatus.innerHTML = '<span style="color: var(--accent-amber); font-weight: 600;">● Not Configured (Get key from <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color: var(--accent-primary); text-decoration: underline;">Google AI Studio</a>)</span>';
                }
            }
        } catch (e) {
            console.error('Failed to load settings:', e);
        }
    },

    async saveSettings() {
        const lang = document.getElementById('settingsLangSelect')?.value;
        const model = document.getElementById('settingsModelSelect')?.value;
        const apiKey = document.getElementById('apiKeyInput')?.value.trim();

        const payload = {
            preferred_lang: lang,
            theme: AppState.theme
        };
        if (apiKey) {
            payload.api_key = apiKey;
            localStorage.setItem('gemini_api_key', apiKey);
            AppState.apiKey = apiKey;
        }

        try {
            const resp = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();

            if (data.success) {
                if (lang) {
                    AppState.preferredLanguage = lang;
                    const mainLangSelect = document.getElementById('langSelect');
                    if (mainLangSelect) mainLangSelect.value = lang;
                }
                if (model) {
                    AppState.currentModel = model;
                    const mainModelSelect = document.getElementById('modelSelect');
                    if (mainModelSelect) mainModelSelect.value = model;
                }
                closeModal('settingsModal');
                showToast('Settings and API Key saved successfully!', 'success');
            }
        } catch (e) {
            showToast('Error saving settings: ' + e.message, 'error');
        }
    },

    async changePassword() {
        const currentPass = document.getElementById('currentPasswordInput')?.value.trim();
        const newPass = document.getElementById('newPasswordInput')?.value.trim();
        const confirmPass = document.getElementById('confirmNewPasswordInput')?.value.trim();
        const statusBox = document.getElementById('changePassStatus');

        if (!currentPass || !newPass) {
            showToast('Please enter both current and new password', 'error');
            return;
        }

        if (newPass !== confirmPass) {
            showToast('New passwords do not match', 'error');
            return;
        }

        if (newPass.length < 4) {
            showToast('Password must be at least 4 characters long', 'error');
            return;
        }

        try {
            const resp = await fetch('/api/auth/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_password: currentPass,
                    new_password: newPass
                })
            });
            const data = await resp.json();

            if (data.success) {
                showToast('Password updated successfully!', 'success');
                document.getElementById('currentPasswordInput').value = '';
                document.getElementById('newPasswordInput').value = '';
                document.getElementById('confirmNewPasswordInput').value = '';
                if (statusBox) {
                    statusBox.innerHTML = '<span style="color: #10b981; font-weight: 700;">✓ Password updated successfully!</span>';
                }
            } else {
                showToast(data.error || 'Failed to update password', 'error');
                if (statusBox) {
                    statusBox.innerHTML = `<span style="color: #f43f5e; font-weight: 700;">⚠️ ${escapeHtml(data.error || 'Error')}</span>`;
                }
            }
        } catch (e) {
            showToast('Password update failed: ' + e.message, 'error');
        }
    }
};

window.SettingsManager = SettingsManager;
