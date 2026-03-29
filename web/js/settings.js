// Settings module
const settings = {
    data: {},
    providers: {},
    plugins: [],

    async init() {
        await this.load();
    },

    async load() {
        try {
            const resp = await fetch('/api/settings');
            const data = await resp.json();
            this.data = data.settings || {};
            this.providers = data.cloud_providers || {};
            this.plugins = data.available_plugins || [];
            this.render();
        } catch (e) {
            console.error('Settings load failed:', e);
        }
    },

    render() {
        const panel = document.getElementById('settingsContent');
        if (!panel) return;

        const d = this.data;
        const backend = d.llm_backend || 'ollama';

        // Build cloud provider options
        const providerOpts = Object.entries(this.providers).map(([k, v]) =>
            `<option value="${k}" ${d.cloud_provider === k ? 'selected' : ''}>${v.name} (${v.cost})</option>`
        ).join('');

        // Build cloud model options for current provider
        const currentProvider = this.providers[d.cloud_provider] || {};
        const modelOpts = (currentProvider.models || []).map(m =>
            `<option value="${m}" ${d.cloud_model === m ? 'selected' : ''}>${m}</option>`
        ).join('');

        // Build plugin checkboxes
        const activePlugins = d.plugins || [];
        const pluginChecks = this.plugins.map(p =>
            `<label class="set-check">
                <input type="checkbox" value="${p.id}" ${activePlugins.includes(p.id) ? 'checked' : ''}
                    onchange="settings.togglePlugin('${p.id}', this.checked)">
                <span><strong>${p.name}</strong> — ${p.description}</span>
            </label>`
        ).join('');

        panel.innerHTML = `
            <div class="set-section">
                <h3>LLM Backend</h3>
                <div class="set-row">
                    <label>Backend</label>
                    <select id="setBackend" onchange="settings.onBackendChange(this.value)">
                        <option value="ollama" ${backend === 'ollama' ? 'selected' : ''}>Ollama (local)</option>
                        <option value="cloud" ${backend === 'cloud' ? 'selected' : ''}>Cloud API</option>
                        <option value="custom" ${backend === 'custom' ? 'selected' : ''}>Custom URL</option>
                    </select>
                </div>

                <div id="setOllama" class="set-group" style="display:${backend === 'ollama' ? '' : 'none'}">
                    <div class="set-row">
                        <label>Ollama URL</label>
                        <input type="text" id="setOllamaHost" value="${d.ollama_host || ''}" placeholder="http://localhost:11434">
                    </div>
                    <div class="set-row">
                        <label>Model</label>
                        <input type="text" id="setOllamaModel" value="${d.ollama_model || ''}" placeholder="qwen3:4b">
                    </div>
                </div>

                <div id="setCloud" class="set-group" style="display:${backend === 'cloud' ? '' : 'none'}">
                    <div class="set-row">
                        <label>Provider</label>
                        <select id="setCloudProvider" onchange="settings.onProviderChange(this.value)">
                            ${providerOpts}
                        </select>
                    </div>
                    <div class="set-row">
                        <label>API Key</label>
                        <input type="password" id="setCloudKey" value="" placeholder="${d.cloud_api_key_masked || 'Enter API key'}">
                    </div>
                    <div class="set-row">
                        <label>Model</label>
                        <select id="setCloudModel">${modelOpts}</select>
                    </div>
                </div>

                <div id="setCustom" class="set-group" style="display:${backend === 'custom' ? '' : 'none'}">
                    <div class="set-row">
                        <label>API URL</label>
                        <input type="text" id="setCustomUrl" value="${d.custom_url || ''}" placeholder="http://192.168.1.100:8100/v1">
                    </div>
                    <div class="set-row">
                        <label>API Key</label>
                        <input type="password" id="setCustomKey" value="" placeholder="${d.custom_api_key_masked || 'Optional'}">
                    </div>
                    <div class="set-row">
                        <label>Model</label>
                        <input type="text" id="setCustomModel" value="${d.custom_model || ''}" placeholder="model name">
                    </div>
                </div>

                <div class="set-row">
                    <label></label>
                    <div class="set-actions">
                        <button class="btn-test" onclick="settings.testConnection()">Test Connection</button>
                        <span id="setTestResult" class="set-result"></span>
                    </div>
                </div>

                <div class="set-row">
                    <label>Cloud Fallback</label>
                    <label class="set-toggle">
                        <input type="checkbox" id="setFallback" ${d.cloud_fallback ? 'checked' : ''}>
                        <span>Use cloud API if local LLM fails</span>
                    </label>
                </div>
            </div>

            <div class="set-section">
                <h3>Telegram Bot</h3>
                <div class="set-row">
                    <label>Bot Token</label>
                    <input type="password" id="setTelegramToken" value="" placeholder="${d.telegram_bot_token_masked || 'Bot token from @BotFather'}">
                </div>
                <div class="set-row">
                    <label>Allowed Users</label>
                    <input type="text" id="setTelegramUsers" value="${d.telegram_allowed_users || ''}" placeholder="Comma-separated user IDs">
                </div>
            </div>

            <div class="set-section">
                <h3>Language</h3>
                <div class="set-row">
                    <label>Interface</label>
                    <select id="setLang" onchange="settings.onLangChange(this.value)">
                        <option value="es" ${d.language === 'es' ? 'selected' : ''}>Espanol</option>
                        <option value="en" ${d.language === 'en' ? 'selected' : ''}>English</option>
                    </select>
                </div>
            </div>

            <div class="set-section">
                <h3>Plugins</h3>
                <div class="set-plugins">${pluginChecks}</div>
            </div>

            <div class="set-section">
                <h3>Voice</h3>
                <div class="set-row">
                    <label>Whisper Model</label>
                    <select id="setWhisperModel">
                        <option value="tiny" ${d.whisper_model === 'tiny' ? 'selected' : ''}>tiny (fast, less accurate)</option>
                        <option value="base" ${d.whisper_model === 'base' ? 'selected' : ''}>base (balanced)</option>
                        <option value="small" ${d.whisper_model === 'small' ? 'selected' : ''}>small (accurate)</option>
                        <option value="medium" ${d.whisper_model === 'medium' ? 'selected' : ''}>medium (best)</option>
                    </select>
                </div>
            </div>

            <div class="set-save">
                <button class="btn-save" onclick="settings.save()">Save Settings</button>
                <span id="setSaveResult" class="set-result"></span>
            </div>
        `;
    },

    onBackendChange(val) {
        document.getElementById('setOllama').style.display = val === 'ollama' ? '' : 'none';
        document.getElementById('setCloud').style.display = val === 'cloud' ? '' : 'none';
        document.getElementById('setCustom').style.display = val === 'custom' ? '' : 'none';
    },

    onProviderChange(val) {
        const provider = this.providers[val] || {};
        const sel = document.getElementById('setCloudModel');
        sel.innerHTML = (provider.models || []).map(m => `<option value="${m}">${m}</option>`).join('');
    },

    onLangChange(val) {
        i18n.setLocale(val);
    },

    togglePlugin(id, checked) {
        const plugins = this.data.plugins || [];
        if (checked && !plugins.includes(id)) plugins.push(id);
        if (!checked) {
            const idx = plugins.indexOf(id);
            if (idx > -1) plugins.splice(idx, 1);
        }
        this.data.plugins = plugins;
    },

    async testConnection() {
        const resultEl = document.getElementById('setTestResult');
        resultEl.textContent = 'Testing...';
        resultEl.style.color = 'var(--accent)';

        const backend = document.getElementById('setBackend').value;
        const payload = { llm_backend: backend };

        if (backend === 'ollama') {
            payload.ollama_host = document.getElementById('setOllamaHost').value;
        } else if (backend === 'cloud') {
            payload.cloud_provider = document.getElementById('setCloudProvider').value;
            payload.cloud_api_key = document.getElementById('setCloudKey').value;
        } else if (backend === 'custom') {
            payload.custom_url = document.getElementById('setCustomUrl').value;
            payload.custom_api_key = document.getElementById('setCustomKey').value;
        }

        try {
            const resp = await fetch('/api/settings/test-llm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            resultEl.textContent = data.message;
            resultEl.style.color = data.status === 'ok' ? 'var(--success)' : 'var(--error)';
        } catch (e) {
            resultEl.textContent = e.message;
            resultEl.style.color = 'var(--error)';
        }
    },

    async save() {
        const resultEl = document.getElementById('setSaveResult');
        resultEl.textContent = 'Saving...';

        const payload = {
            llm_backend: document.getElementById('setBackend').value,
            ollama_host: document.getElementById('setOllamaHost')?.value,
            ollama_model: document.getElementById('setOllamaModel')?.value,
            cloud_provider: document.getElementById('setCloudProvider')?.value,
            cloud_model: document.getElementById('setCloudModel')?.value,
            custom_url: document.getElementById('setCustomUrl')?.value,
            custom_model: document.getElementById('setCustomModel')?.value,
            language: document.getElementById('setLang')?.value,
            plugins: this.data.plugins,
            cloud_fallback: document.getElementById('setFallback')?.checked,
            whisper_model: document.getElementById('setWhisperModel')?.value,
            telegram_allowed_users: document.getElementById('setTelegramUsers')?.value,
        };

        // Only send API keys if user typed something new
        const cloudKey = document.getElementById('setCloudKey')?.value;
        if (cloudKey) payload.cloud_api_key = cloudKey;
        const customKey = document.getElementById('setCustomKey')?.value;
        if (customKey) payload.custom_api_key = customKey;
        const tgToken = document.getElementById('setTelegramToken')?.value;
        if (tgToken) payload.telegram_bot_token = tgToken;

        // Remove undefined/null
        Object.keys(payload).forEach(k => { if (payload[k] === undefined || payload[k] === null) delete payload[k]; });

        try {
            const resp = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            resultEl.textContent = 'Saved!';
            resultEl.style.color = 'var(--success)';
            // Refresh health to show new backend
            app.fetchHealth();
            setTimeout(() => { resultEl.textContent = ''; }, 3000);
        } catch (e) {
            resultEl.textContent = e.message;
            resultEl.style.color = 'var(--error)';
        }
    }
};
