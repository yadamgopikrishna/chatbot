/**
 * Multimodal AI Assistant - Vision, Forensics & OCR Module
 */

const VisionManager = {
    async runOCR(imageFile, language = 'auto', targetType = 'general') {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('language', language);
        formData.append('type', targetType);

        showToast('Running high-accuracy OCR extraction...', 'info');

        try {
            const resp = await fetch('/api/images/ocr', {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();
            if (data.extracted_text) {
                // Populate composer or OCR modal
                setPrompt(`Here is the text extracted from the document:\n\n${data.extracted_text}`);
                showToast('OCR text extracted to composer!', 'success');
            } else {
                showToast(data.error || 'Failed to extract text', 'error');
            }
        } catch (e) {
            showToast('OCR Error: ' + e.message, 'error');
        }
    },

    async runAuthenticityCheck(imageFile) {
        const formData = new FormData();
        formData.append('image', imageFile);

        showToast('Inspecting image metadata & synthesis forensics...', 'info');

        try {
            const resp = await fetch('/api/images/detect', {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();
            const forensics = data.forensics;

            openModal('forensicsModal');
            const container = document.getElementById('forensicsModalContent');
            const levelClass = forensics.ai_probability > 60 ? 'high' : (forensics.ai_probability > 30 ? 'medium' : 'low');

            container.innerHTML = `
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="font-size: 22px; font-weight: 800; color: var(--text-primary); margin-bottom: 6px;">
                        ${escapeHtml(forensics.classification)}
                    </div>
                    <div style="font-size: 13px; color: var(--text-muted);">
                        Confidence: ${forensics.confidence}% • AI Likelihood: ${forensics.ai_probability}%
                    </div>
                </div>

                <div class="prob-meter" style="height: 12px; margin-bottom: 20px;">
                    <div class="prob-fill ${levelClass}" style="width: ${forensics.ai_probability}%"></div>
                </div>

                <h4 style="margin-bottom: 10px;">Forensic Signals Detected:</h4>
                <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px;">
                    ${forensics.signals.map(s => `
                        <div style="padding: 10px; background: var(--bg-tertiary); border-radius: 6px; font-size: 13px;">
                            <div style="font-weight: 600; color: var(--text-primary);">${escapeHtml(s.feature)}</div>
                            <div style="color: var(--text-secondary); margin-top: 2px;">${escapeHtml(s.finding)}</div>
                            <div style="color: var(--text-muted); font-size: 11px; margin-top: 2px;">Implication: ${escapeHtml(s.implication)}</div>
                        </div>
                    `).join('')}
                </div>

                ${forensics.visual_explanation ? `
                    <div style="padding: 14px; background: var(--bg-tertiary); border-radius: 8px; margin-bottom: 16px;">
                        <h4 style="margin-bottom: 6px;">Visual Forensics Assessment:</h4>
                        <div class="markdown-body" style="font-size: 13px;">${renderMarkdown(forensics.visual_explanation)}</div>
                    </div>
                ` : ''}

                <div style="font-size: 12px; color: var(--text-muted); text-align: center;">
                    ${escapeHtml(forensics.limitations_disclaimer)}
                </div>
            `;
        } catch (e) {
            showToast('Forensics Error: ' + e.message, 'error');
        }
    }
};

window.VisionManager = VisionManager;
