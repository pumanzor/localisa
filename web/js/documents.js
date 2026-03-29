// Documents module — upload and manage
const documents = {
    collections: [],

    init() {
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');

        if (!dropzone) return;

        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', e => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length) this.upload(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) this.upload(fileInput.files[0]);
        });

        this.refresh();
    },

    async upload(file) {
        const status = document.getElementById('uploadStatus');
        status.textContent = `Subiendo ${file.name}...`;
        status.style.color = 'var(--accent)';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const resp = await fetch('/api/documents/upload', { method: 'POST', body: formData });
            const data = await resp.json();
            if (data.status === 'ok') {
                status.textContent = `${file.name} — ${data.chunks} chunks indexados`;
                status.style.color = 'var(--success)';
                this.refresh();
            } else {
                status.textContent = `Error: ${data.detail}`;
                status.style.color = 'var(--error)';
            }
        } catch (e) {
            status.textContent = `Error: ${e.message}`;
            status.style.color = 'var(--error)';
        }
    },

    async refresh() {
        try {
            const resp = await fetch('/api/documents/collections');
            const data = await resp.json();
            this.collections = data.collections || [];
            this.render();
        } catch (e) {
            // RAG not available
        }
    },

    render() {
        const list = document.getElementById('docList');
        if (!list) return;

        if (!this.collections.length) {
            list.innerHTML = `<p style="color:var(--text-muted);font-size:0.85em">${i18n.t('no_documents')}</p>`;
            return;
        }

        list.innerHTML = this.collections.map(c => `
            <div class="doc-item">
                <div>
                    <div class="doc-name">${c.name || c}</div>
                    <div class="doc-meta">${c.count || '?'} documentos</div>
                </div>
                <button class="doc-delete" onclick="documents.deleteCollection('${c.name || c}')" title="Eliminar">x</button>
            </div>
        `).join('');
    },

    async deleteCollection(name) {
        if (!confirm(`Eliminar coleccion "${name}"?`)) return;
        await fetch(`/api/documents/${name}`, { method: 'DELETE' });
        this.refresh();
    }
};
