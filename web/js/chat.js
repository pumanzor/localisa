// Chat module — SSE streaming
const chat = {
    conversationId: "default",
    isStreaming: false,

    async send(message) {
        if (!message.trim() || this.isStreaming) return;
        this.isStreaming = true;

        this.addMessage("user", message);

        const typing = document.getElementById("typing");
        typing.classList.add("visible");

        const msgEl = this.addMessage("assistant", "", true);
        const contentEl = msgEl.querySelector(".content");
        let fullText = "";
        let metadata = {};

        try {
            const resp = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId,
                    stream: true,
                }),
            });

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let eventType = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                // Split by \r\n or \n, handle both
                const lines = buffer.split(/\r?\n/);
                buffer = lines.pop() || "";

                for (const line of lines) {
                    const trimmed = line.replace(/\r$/, "");

                    if (trimmed.startsWith("event: ")) {
                        eventType = trimmed.slice(7).trim();
                    } else if (trimmed.startsWith("data: ") && eventType) {
                        const data = trimmed.slice(6);

                        if (eventType === "token") {
                            fullText += data;
                            const clean = this.cleanResponse(fullText);
                            contentEl.innerHTML = this.renderMarkdown(clean);
                            this.scrollToBottom();
                        } else if (eventType === "metadata") {
                            try { metadata = JSON.parse(data); } catch(e) {}
                        } else if (eventType === "done") {
                            try { const d = JSON.parse(data); metadata.total_tokens = d.total_tokens; } catch(e) {}
                        } else if (eventType === "error") {
                            contentEl.textContent = "Error: " + data;
                            contentEl.style.color = "var(--error)";
                        }
                        eventType = null;
                    }
                }
            }
        } catch (e) {
            contentEl.textContent = i18n.t("error_llm") + ": " + e.message;
            contentEl.style.color = "var(--error)";
        }

        // Final render
        const finalText = this.cleanResponse(fullText);
        if (finalText) {
            contentEl.innerHTML = this.renderMarkdown(finalText);
        }

        typing.classList.remove("visible");

        if (metadata.model || metadata.has_rag_context) {
            const metaEl = document.createElement("div");
            metaEl.className = "meta";
            let html = "";
            if (metadata.model) html += "<span>" + metadata.model + "</span>";
            if (metadata.backend) html += "<span>" + metadata.backend + "</span>";
            if (metadata.has_rag_context) html += "<span class='rag-badge'>RAG</span>";
            metaEl.innerHTML = html;
            msgEl.appendChild(metaEl);
        }

        this.isStreaming = false;
        this.scrollToBottom();
    },

    cleanResponse(text) {
        let clean = text.replace(/<think>[\s\S]*?<\/think>/g, "");
        clean = clean.replace(/<think>[\s\S]*$/g, "");
        return clean.trim();
    },

    addMessage(role, content, isPlaceholder) {
        const container = document.getElementById("chatMessages");
        const msgEl = document.createElement("div");
        msgEl.className = "message " + role;

        const roleLabel = role === "user" ? "Tu" : "Localisa";
        const roleClass = role === "assistant" ? " ai" : "";

        const roleDiv = document.createElement("div");
        roleDiv.className = "role" + roleClass;
        roleDiv.textContent = roleLabel;

        const contentDiv = document.createElement("div");
        contentDiv.className = "content";
        if (!isPlaceholder && content) {
            contentDiv.innerHTML = this.renderMarkdown(content);
        }

        msgEl.appendChild(roleDiv);
        msgEl.appendChild(contentDiv);
        container.appendChild(msgEl);
        this.scrollToBottom();
        return msgEl;
    },

    renderMarkdown(text) {
        if (!text) return "";
        return text
            .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre><code>$2</code></pre>")
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
            .replace(/\*([^*]+)\*/g, "<em>$1</em>")
            .replace(/\n\n+/g, "<br><br>")
            .replace(/\n/g, "<br>");
    },

    scrollToBottom() {
        const container = document.getElementById("chatMessages");
        container.scrollTop = container.scrollHeight;
    },

    clear() {
        document.getElementById("chatMessages").innerHTML = "";
        fetch("/api/chat/" + this.conversationId, { method: "DELETE" });
        this.addMessage("assistant", i18n.t("greeting"));
    }
};
