// Localisa main app
const app = {
    currentPanel: 'chat',

    async init() {
        await i18n.init();
        this.applyI18n();
        voice.init();
        documents.init();
        this.setupInput();
        this.switchPanel('chat');
        this.fetchHealth();

        // Show greeting
        chat.addMessage('assistant', i18n.t('greeting'));
    },

    applyI18n() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (el.tagName === 'TEXTAREA') {
                el.placeholder = i18n.t(key);
            } else {
                el.textContent = i18n.t(key);
            }
        });
    },

    setupInput() {
        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('btnSend');

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 200) + 'px';
        });

        sendBtn.addEventListener('click', () => this.sendMessage());
    },

    sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        input.style.height = 'auto';

        // Switch to chat panel if not there
        if (this.currentPanel !== 'chat') this.switchPanel('chat');

        chat.send(message);
    },

    switchPanel(panel) {
        this.currentPanel = panel;

        // Update nav
        document.querySelectorAll('.nav-item').forEach(el => {
            el.classList.toggle('active', el.dataset.panel === panel);
        });

        // Update panels
        document.querySelectorAll('.panel').forEach(el => {
            el.classList.toggle('active', el.id === `panel-${panel}`);
        });

        // Update header
        const titles = {
            chat: i18n.t('chat'),
            documents: i18n.t('documents'),
            health: i18n.t('health'),
        };
        document.getElementById('panelTitle').textContent = titles[panel] || panel;
    },

    async fetchHealth() {
        try {
            const resp = await fetch('/api/health');
            const data = await resp.json();

            // Update status dot
            const dot = document.getElementById('statusDot');
            dot.className = `status-dot ${data.status}`;

            // Update model info
            const modelEl = document.getElementById('modelInfo');
            if (modelEl) modelEl.textContent = `${data.model} (${data.backend})`;

            // Update health panel
            const grid = document.getElementById('healthGrid');
            if (grid && data.services) {
                grid.innerHTML = data.services.map(s => `
                    <div class="health-card">
                        <div class="service-name">${s.name}</div>
                        <div class="service-status ${s.status}">${s.status}</div>
                        ${s.error ? `<div style="font-size:0.7em;color:var(--text-muted);margin-top:4px">${s.error}</div>` : ''}
                    </div>
                `).join('');
            }
        } catch (e) {
            // API not available
        }

        // Refresh every 30s
        setTimeout(() => this.fetchHealth(), 30000);
    },

    newChat() {
        chat.clear();
    }
};

// Boot
document.addEventListener('DOMContentLoaded', () => app.init());
