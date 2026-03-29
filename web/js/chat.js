// Chat module — SSE streaming
const chat = {
    conversationId: 'default',
    isStreaming: false,

    async send(message) {
        if (!message.trim() || this.isStreaming) return;
        this.isStreaming = true;

        // Add user message
        this.addMessage('user', message);

        // Show typing indicator
        const typing = document.getElementById('typing');
        typing.classList.add('visible');

        // Create assistant message placeholder
        const msgEl = this.addMessage('assistant', '', true);
        const contentEl = msgEl.querySelector('.content');
        let fullText = '';
        let metadata = {};

        try {
            const resp = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId,
                    stream: true,
                }),
            });

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        var eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ') && eventType) {
                        const data = line.slice(6);

                        if (eventType === 'token') {
                            fullText += data;
                            contentEl.innerHTML = this.renderMarkdown(fullText);
                            this.scrollToBottom();
                        } else if (eventType === 'metadata') {
                            try { metadata = JSON.parse(data); } catch(e) {}
                        } else if (eventType === 'done') {
                            try {
                                const doneData = JSON.parse(data);
                                metadata.total_tokens = doneData.total_tokens;
                            } catch(e) {}
                        } else if (eventType === 'error') {
                            contentEl.innerHTML = `<span style="color:var(--error)">Error: ${data}</span>`;
                        }
                        eventType = null;
                    }
                }
            }
        } catch (e) {
            contentEl.innerHTML = `<span style="color:var(--error)">${i18n.t('error_llm')}: ${e.message}</span>`;
        }

        // Hide typing, add metadata
        typing.classList.remove('visible');

        if (metadata.model || metadata.has_rag_context) {
            const metaEl = document.createElement('div');
            metaEl.className = 'meta';
            let metaHTML = '';
            if (metadata.model) metaHTML += `<span>${metadata.model}</span>`;
            if (metadata.backend) metaHTML += `<span>${metadata.backend}</span>`;
            if (metadata.has_rag_context) metaHTML += `<span class="rag-badge">RAG</span>`;
            metaEl.innerHTML = metaHTML;
            msgEl.appendChild(metaEl);
        }

        this.isStreaming = false;
        this.scrollToBottom();
    },

    addMessage(role, content, isPlaceholder = false) {
        const container = document.getElementById('chatMessages');
        const msgEl = document.createElement('div');
        msgEl.className = `message ${role}`;

        const roleLabel = role === 'user' ? 'Tu' : 'Localisa';
        msgEl.innerHTML = `
            <div class="role ${role === 'assistant' ? 'ai' : ''}">${roleLabel}</div>
            <div class="content">${isPlaceholder ? '' : this.renderMarkdown(content)}</div>
        `;

        container.appendChild(msgEl);
        this.scrollToBottom();
        return msgEl;
    },

    renderMarkdown(text) {
        // Simple markdown: bold, italic, code, code blocks, links
        return text
            .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    },

    scrollToBottom() {
        const container = document.getElementById('chatMessages');
        container.scrollTop = container.scrollHeight;
    },

    clear() {
        document.getElementById('chatMessages').innerHTML = '';
        fetch(`/api/chat/${this.conversationId}`, { method: 'DELETE' });
        // Show greeting
        this.addMessage('assistant', i18n.t('greeting'));
    }
};
