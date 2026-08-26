/**
 * OG AI Assistant - Resume Studio & ATS Analyzer Module
 */

const ResumeStudio = {
    activeTab: 'analyze',

    switchTab(tab) {
        this.activeTab = tab;
        const tabAnalyzeBtn = document.getElementById('tabResumeAnalyze');
        const tabGenerateBtn = document.getElementById('tabResumeGenerate');
        const viewAnalyze = document.getElementById('resumeAnalyzeView');
        const viewGenerate = document.getElementById('resumeGenerateView');

        if (tab === 'analyze') {
            tabAnalyzeBtn.classList.add('active');
            tabGenerateBtn.classList.remove('active');
            viewAnalyze.style.display = 'block';
            viewGenerate.style.display = 'none';
        } else {
            tabAnalyzeBtn.classList.remove('active');
            tabGenerateBtn.classList.add('active');
            viewAnalyze.style.display = 'none';
            viewGenerate.style.display = 'block';
        }
    },

    async analyze() {
        const fileInput = document.getElementById('resumeFileInput');
        const textInput = document.getElementById('resumeTextInput');
        const roleInput = document.getElementById('resumeTargetRoleInput');
        const jdInput = document.getElementById('resumeJDInput');
        const resultBox = document.getElementById('resumeAnalysisResult');
        const btn = document.getElementById('btnDoResumeAnalyze');

        const file = fileInput.files[0];
        const text = textInput ? textInput.value.trim() : '';
        const targetRole = roleInput ? roleInput.value.trim() : '';
        const jobDesc = jdInput ? jdInput.value.trim() : '';

        if (!file && !text) {
            showToast('Please upload a resume file or paste resume text', 'error');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> Analyzing Resume ATS Match...';
        resultBox.innerHTML = `
            <div style="text-align: center; padding: 30px; color: var(--text-primary);">
                <div class="pulse-dot" style="margin: 0 auto 12px;"></div>
                <div style="font-weight: 700; font-size: 15px;">Scanning keywords, metrics, and ATS compatibility...</div>
            </div>
        `;

        const formData = new FormData();
        if (file) {
            formData.append('resume_file', file);
        } else {
            formData.append('resume_text', text);
        }
        formData.append('target_role', targetRole);
        formData.append('job_description', jobDesc);
        formData.append('api_key', localStorage.getItem('gemini_custom_api_key') || '');

        try {
            const res = await fetch('/api/resume/analyze', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (data.success) {
                this.renderAnalysisResult(data);
                showToast('Resume ATS Analysis complete!', 'success');
            } else {
                resultBox.innerHTML = `<div class="auth-error-banner" style="margin-top: 14px;">⚠️ ${escapeHtml(data.error || 'Analysis failed')}</div>`;
            }
        } catch (err) {
            resultBox.innerHTML = `<div class="auth-error-banner" style="margin-top: 14px;">⚠️ Request failed: ${escapeHtml(err.message)}</div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '🔍 Run ATS Analysis';
        }
    },

    renderAnalysisResult(data) {
        const resultBox = document.getElementById('resumeAnalysisResult');
        const score = data.ats_score || 0;
        const scoreColor = score >= 80 ? '#10b981' : (score >= 65 ? '#f59e0b' : '#ef4444');

        const matchedTags = (data.matched_skills || []).map(s => `<span class="tag-matched">✓ ${escapeHtml(s)}</span>`).join(' ');
        const missingTags = (data.missing_skills || []).map(s => `<span class="tag-missing">+ ${escapeHtml(s)}</span>`).join(' ');

        const strengthsList = (data.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
        const weaknessesList = (data.weaknesses || []).map(w => `<li>${escapeHtml(w)}</li>`).join('');

        const bulletImprovements = (data.bullet_improvements || []).map(item => `
            <div class="bullet-diff-card">
                <div class="diff-before"><strong>Original:</strong> "${escapeHtml(item.original)}"</div>
                <div class="diff-after"><strong>✨ High-Impact ATS Rewrite:</strong> "${escapeHtml(item.improved)}"</div>
                <div class="diff-rationale">💡 <em>${escapeHtml(item.rationale)}</em></div>
            </div>
        `).join('');

        resultBox.innerHTML = `
            <div class="resume-results-container">
                <!-- Score Header -->
                <div class="ats-score-banner" style="border-left: 6px solid ${scoreColor};">
                    <div class="ats-score-circle" style="border-color: ${scoreColor}; color: ${scoreColor};">
                        <span class="score-number">${score}</span>
                        <span class="score-label">/ 100</span>
                    </div>
                    <div class="ats-verdict-box">
                        <div class="ats-verdict-title">${escapeHtml(data.verdict || 'Analysis Result')}</div>
                        <div class="ats-verdict-desc">${escapeHtml(data.role_match_summary || '')}</div>
                    </div>
                </div>

                <!-- Keywords Match Grid -->
                <div class="resume-grid-2">
                    <div class="analysis-card">
                        <h4>🎯 Matched Keywords (${(data.matched_skills || []).length})</h4>
                        <div class="tags-strip">${matchedTags || '<span style="color: var(--text-muted);">No exact matches found.</span>'}</div>
                    </div>
                    <div class="analysis-card">
                        <h4>⚡ Missing Keywords to Add (${(data.missing_skills || []).length})</h4>
                        <div class="tags-strip">${missingTags || '<span style="color: var(--text-muted);">Great keyword coverage!</span>'}</div>
                    </div>
                </div>

                <!-- Strengths & Weaknesses -->
                <div class="resume-grid-2">
                    <div class="analysis-card">
                        <h4>💪 Strengths & Impact</h4>
                        <ul class="analysis-list green">${strengthsList}</ul>
                    </div>
                    <div class="analysis-card">
                        <h4>🛠️ Critical Gaps to Fix</h4>
                        <ul class="analysis-list orange">${weaknessesList}</ul>
                    </div>
                </div>

                <!-- High-Impact Bullet Rewrites -->
                ${bulletImprovements ? `
                    <div class="analysis-card" style="margin-top: 10px;">
                        <h4>🚀 High-Impact STAR Bullet Point Rewrites</h4>
                        <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
                            ${bulletImprovements}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    },

    async generate() {
        const name = document.getElementById('genNameInput').value.trim();
        const email = document.getElementById('genEmailInput').value.trim();
        const phone = document.getElementById('genPhoneInput').value.trim();
        const location = document.getElementById('genLocationInput').value.trim();
        const role = document.getElementById('genRoleInput').value.trim();
        const skills = document.getElementById('genSkillsInput').value.trim();
        const experience = document.getElementById('genExperienceInput').value.trim();
        const education = document.getElementById('genEducationInput').value.trim();
        const projects = document.getElementById('genProjectsInput').value.trim();

        const resultBox = document.getElementById('resumeGenResult');
        const btn = document.getElementById('btnDoResumeGen');

        if (!role || !skills) {
            showToast('Please enter at least a Target Role and Key Skills', 'error');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> Architecting ATS Resume & Word Doc...';
        resultBox.innerHTML = `
            <div style="text-align: center; padding: 30px; color: var(--text-primary);">
                <div class="pulse-dot" style="margin: 0 auto 12px;"></div>
                <div style="font-weight: 700; font-size: 15px;">Building professional STAR-formatted resume...</div>
            </div>
        `;

        try {
            const apiKey = localStorage.getItem('gemini_custom_api_key') || '';
            const res = await fetch('/api/resume/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name, email, phone, location,
                    target_role: role,
                    skills, experience, education, projects,
                    api_key: apiKey
                })
            });
            const data = await res.json();

            if (data.success) {
                resultBox.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 14px; margin-top: 14px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-tertiary); padding: 14px 18px; border-radius: 12px; border: 1.5px solid var(--border-medium);">
                            <div>
                                <div style="font-weight: 800; font-size: 15.5px; color: var(--text-primary);">✨ Professional Resume Ready</div>
                                <div style="font-size: 13px; color: var(--text-muted);">Formatted for Applicant Tracking Systems (ATS)</div>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <a href="${data.docx_url}" download="${data.filename}" class="msg-btn btn-compare">⬇️ Download Word (.docx)</a>
                                <button class="msg-btn" onclick="ResumeStudio.insertIntoChat('${data.docx_url}', '${escapeHtml(role)}')">💬 Post to Chat</button>
                            </div>
                        </div>

                        <div class="markdown-body" style="background: var(--bg-surface); padding: 22px; border-radius: 12px; border: 1px solid var(--border-subtle); max-height: 420px; overflow-y: auto;">
                            ${renderMarkdown(data.markdown)}
                        </div>
                    </div>
                `;
                showToast('Resume generated & Word document ready!', 'success');
            } else {
                resultBox.innerHTML = `<div class="auth-error-banner" style="margin-top: 14px;">⚠️ ${escapeHtml(data.error || 'Generation failed')}</div>`;
            }
        } catch (err) {
            resultBox.innerHTML = `<div class="auth-error-banner" style="margin-top: 14px;">⚠️ Request failed: ${escapeHtml(err.message)}</div>`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '✨ Generate ATS Resume (.docx)';
        }
    },

    insertIntoChat(docxUrl, role) {
        closeModal('resumeModal');
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.value = `Here is my generated resume for **${role}**:\n\n<a href="${docxUrl}" download class="msg-btn btn-compare">⬇️ Download Word Resume (.docx)</a>`;
            if (typeof sendMessage === 'function') {
                sendMessage();
            }
        }
    },

    fillSample() {
        document.getElementById('genNameInput').value = 'Gopi Krishna';
        document.getElementById('genEmailInput').value = 'gopi@example.com';
        document.getElementById('genPhoneInput').value = '+1 (555) 234-5678';
        document.getElementById('genLocationInput').value = 'San Francisco, CA';
        document.getElementById('genRoleInput').value = 'Senior Full-Stack AI Engineer';
        document.getElementById('genSkillsInput').value = 'Python, Flask, Google Gemini SDK, React, TypeScript, Oracle Database, Docker, Kubernetes, Microservices, RAG, PyTorch';
        document.getElementById('genExperienceInput').value = 'Lead AI Engineer at TechFlow (2022-Present): Architected multimodal AI assistants, scaled systems to 2M users, cut latency by 40%.\nFull-Stack Developer at CyberCore (2020-2022): Built distributed backend APIs and real-time dashboards.';
        document.getElementById('genEducationInput').value = 'B.Tech in Computer Science, State University (2016-2020), First Class with Distinction';
        document.getElementById('genProjectsInput').value = 'Autonomous Multimodal Chatbot with document RAG, image forensics, and live spreadsheet charting.';
        showToast('Loaded sample profile details!', 'info');
    }
};
