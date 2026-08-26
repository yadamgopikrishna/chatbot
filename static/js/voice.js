/**
 * Multimodal AI Assistant - Web Speech API Voice Module (STT & TTS)
 */

const VoiceAssistant = {
    recognition: null,
    isListening: false,

    getLanguageLocale(langCode) {
        const map = {
            'te': 'te-IN',
            'hi': 'hi-IN',
            'ta': 'ta-IN',
            'kn': 'kn-IN',
            'ml': 'ml-IN',
            'bn': 'bn-IN',
            'mr': 'mr-IN',
            'gu': 'gu-IN',
            'ur': 'ur-IN',
            'pa': 'pa-IN',
            'es': 'es-ES',
            'fr': 'fr-FR',
            'de': 'de-DE',
            'pt': 'pt-PT',
            'ar': 'ar-SA',
            'zh': 'zh-CN',
            'ja': 'ja-JP',
            'ko': 'ko-KR',
            'en': 'en-US',
            'auto': 'en-US'
        };
        return map[langCode] || 'en-US';
    },

    init() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            console.warn('Web Speech Recognition is not supported in this browser.');
            return;
        }

        this.recognition = new SpeechRec();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;

        this.recognition.onstart = () => {
            this.isListening = true;
            this.updateMicButton(true);
            showToast('Listening... Speak now', 'info');
        };

        this.recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            const input = document.getElementById('chatInput');
            if (input) {
                input.value = transcript;
                input.style.height = 'auto';
                input.style.height = Math.min(input.scrollHeight, 160) + 'px';
            }
        };

        this.recognition.onerror = (event) => {
            this.isListening = false;
            this.updateMicButton(false);
            showToast('Speech recognition error: ' + event.error, 'error');
        };

        this.recognition.onend = () => {
            this.isListening = false;
            this.updateMicButton(false);
        };
    },

    toggleListening() {
        if (!this.recognition) {
            this.init();
            if (!this.recognition) {
                showToast('Speech recognition not supported in this browser.', 'error');
                return;
            }
        }

        if (this.isListening) {
            this.recognition.stop();
        } else {
            const langCode = AppState.preferredLanguage || 'auto';
            this.recognition.lang = this.getLanguageLocale(langCode);
            try {
                this.recognition.start();
            } catch (e) {
                console.warn(e);
            }
        }
    },

    updateMicButton(active) {
        const micBtn = document.getElementById('micBtn');
        if (micBtn) {
            if (active) {
                micBtn.style.color = 'var(--accent-rose)';
                micBtn.style.animation = 'pulse 1.2s infinite';
            } else {
                micBtn.style.color = 'var(--text-secondary)';
                micBtn.style.animation = 'none';
            }
        }
    },

    speak(text, langCode = 'en') {
        if (!window.speechSynthesis) {
            showToast('Text-to-Speech not supported in this browser.', 'error');
            return;
        }

        window.speechSynthesis.cancel(); // Stop any active speech

        // Strip markdown formatting characters for clean speech
        const cleanText = text
            .replace(/```[\s\S]*?```/g, 'Code block omitted.')
            .replace(/`([^`]+)`/g, '$1')
            .replace(/[#\*_\[\]\(\)\>]/g, '')
            .replace(/https?:\/\/\S+/g, '')
            .trim();

        if (!cleanText) return;

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = this.getLanguageLocale(langCode);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        window.speechSynthesis.speak(utterance);
        showToast('Playing voice response...', 'info');
    }
};

window.VoiceAssistant = VoiceAssistant;

document.addEventListener('DOMContentLoaded', () => {
    VoiceAssistant.init();
    const micBtn = document.getElementById('micBtn');
    if (micBtn) {
        micBtn.addEventListener('click', () => VoiceAssistant.toggleListening());
    }
});
