/**
 * Multimodal AI Assistant - Document Library & Comparison Module
 */

const DocumentManager = {
    selectedDocsForCompare: [],

    async loadLibrary() {
        const tbody = document.getElementById('docsTableBody');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">Loading library...</td></tr>';

        try {
            const resp = await fetch('/api/documents/list');
            const data = await resp.json();
            const docs = data.documents || [];

            if (docs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--text-muted);">No documents uploaded yet. Drag & drop files onto the chat to start.</td></tr>';
                return;
            }

            tbody.innerHTML = docs.map(d => {
                const sizeKb = Math.round(d.file_size / 1024);
                return `
                    <tr style="border-bottom: 1px solid var(--border-subtle);">
                        <td style="padding: 10px;">
                            <input type="checkbox" onchange="DocumentManager.toggleCompareSelect('${d.doc_id}', this.checked)">
                        </td>
                        <td style="padding: 10px; font-weight: 500;">${escapeHtml(d.filename)}</td>
                        <td style="padding: 10px;"><span style="text-transform: uppercase; font-size: 11px; padding: 2px 6px; background: var(--bg-tertiary); border-radius: 4px;">${d.file_type}</span></td>
                        <td style="padding: 10px; font-size: 13px; color: var(--text-muted);">${sizeKb} KB (${d.page_count} pgs)</td>
                        <td style="padding: 10px; text-align: right;">
                            <button class="msg-btn" onclick="DocumentManager.attachToChat('${d.doc_id}', '${escapeHtml(d.filename)}', '${d.file_type}', '${d.file_path}')">📎 Attach</button>
                            <button class="msg-btn" style="color: var(--accent-rose);" onclick="DocumentManager.deleteDoc('${d.doc_id}')">🗑️</button>
                        </td>
                    </tr>
                `;
            }).join('');
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--accent-rose);">Failed to load documents</td></tr>';
        }
    },

    toggleCompareSelect(docId, isChecked) {
        if (isChecked) {
            if (this.selectedDocsForCompare.length >= 2) {
                showToast('You can select maximum 2 documents for comparison', 'info');
                return;
            }
            this.selectedDocsForCompare.push(docId);
        } else {
            this.selectedDocsForCompare = this.selectedDocsForCompare.filter(id => id !== docId);
        }
        const compBtn = document.getElementById('btnStartCompare');
        if (compBtn) {
            compBtn.disabled = (this.selectedDocsForCompare.length !== 2);
            compBtn.style.opacity = (this.selectedDocsForCompare.length === 2) ? '1' : '0.5';
        }
    },

    attachToChat(docId, filename, fileType, filePath) {
        AppState.activeAttachments.push({
            name: filename,
            type: fileType,
            file_path: filePath,
            doc_id: docId
        });
        renderAttachmentPreview();
        closeModal('docLibraryModal');
        showToast(`Attached ${filename} to conversation`, 'success');
    },

    async deleteDoc(docId) {
        if (!confirm('Are you sure you want to delete this document?')) return;
        await fetch(`/api/documents/${docId}/delete`, { method: 'DELETE' });
        this.loadLibrary();
        showToast('Document deleted', 'info');
    },

    async runComparison() {
        if (this.selectedDocsForCompare.length !== 2) return;
        const [docIdA, docIdB] = this.selectedDocsForCompare;
        closeModal('docLibraryModal');
        openModal('compareModal');

        const container = document.getElementById('compareContent');
        container.innerHTML = '<div style="padding: 30px; text-align: center;">Analyzing document differences and semantic diff...</div>';

        try {
            const resp = await fetch('/api/documents/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ doc_id_a: docIdA, doc_id_b: docIdB })
            });
            const data = await resp.json();
            const comp = data.comparison;

            container.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div><strong>${escapeHtml(comp.document_a)}</strong> vs <strong>${escapeHtml(comp.document_b)}</strong></div>
                    <div style="font-size: 13px; padding: 4px 10px; background: rgba(59, 130, 246, 0.15); border-radius: 9999px; color: var(--accent-primary);">
                        Similarity: ${comp.similarity_score}%
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px;">
                    <div style="padding: 12px; background: var(--bg-tertiary); border-radius: 8px; text-align: center;">
                        <div style="color: var(--accent-secondary); font-weight: 700; font-size: 20px;">+${comp.added_count}</div>
                        <div style="font-size: 12px; color: var(--text-muted);">Added Sections</div>
                    </div>
                    <div style="padding: 12px; background: var(--bg-tertiary); border-radius: 8px; text-align: center;">
                        <div style="color: var(--accent-rose); font-weight: 700; font-size: 20px;">-${comp.removed_count}</div>
                        <div style="font-size: 12px; color: var(--text-muted);">Removed Sections</div>
                    </div>
                    <div style="padding: 12px; background: var(--bg-tertiary); border-radius: 8px; text-align: center;">
                        <div style="color: var(--accent-amber); font-weight: 700; font-size: 20px;">~${comp.modified_count}</div>
                        <div style="font-size: 12px; color: var(--text-muted);">Modified Clauses</div>
                    </div>
                </div>

                ${comp.modified_sections.length > 0 ? `
                    <div style="margin-bottom: 16px;">
                        <h4 style="margin-bottom: 8px;">Key Modified Clauses:</h4>
                        ${comp.modified_sections.slice(0, 5).map(m => `
                            <div style="padding: 10px; background: var(--bg-tertiary); border-radius: 6px; margin-bottom: 8px; font-size: 13px;">
                                <div style="color: var(--accent-rose); text-decoration: line-through; margin-bottom: 4px;">${escapeHtml(m.from)}</div>
                                <div style="color: var(--accent-secondary);">${escapeHtml(m.to)}</div>
                            </div>
                        `).join('')}
                    </div>
                ` : '<div style="color: var(--text-muted); font-size: 13px;">No major textual clauses were modified.</div>'}
            `;
        } catch (err) {
            container.innerHTML = `<div style="color: var(--accent-rose); padding: 20px;">Error running comparison: ${escapeHtml(err.message)}</div>`;
        }
    }
};

window.DocumentManager = DocumentManager;
