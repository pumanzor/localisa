// Voice module — Web Speech API + fallback to Whisper
const voice = {
    isRecording: false,
    recognition: null,

    init() {
        // Try Web Speech API first
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.lang = i18n.locale === 'es' ? 'es-ES' : 'en-US';
            this.recognition.continuous = false;
            this.recognition.interimResults = false;

            this.recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                document.getElementById('chatInput').value = text;
                this.stop();
                // Auto-send
                app.sendMessage();
            };

            this.recognition.onerror = () => this.stop();
            this.recognition.onend = () => this.stop();
        }
    },

    toggle() {
        if (this.isRecording) {
            this.stop();
        } else {
            this.start();
        }
    },

    start() {
        if (!this.recognition) {
            alert('Voice not supported in this browser. Use Chrome or Edge.');
            return;
        }
        this.isRecording = true;
        this.recognition.start();
        document.getElementById('btnVoice').classList.add('recording');
    },

    stop() {
        this.isRecording = false;
        if (this.recognition) {
            try { this.recognition.stop(); } catch(e) {}
        }
        document.getElementById('btnVoice').classList.remove('recording');
    }
};
