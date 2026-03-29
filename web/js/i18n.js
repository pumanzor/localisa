// i18n — simple internationalization
const i18n = {
    locale: 'es',
    messages: {},

    async init() {
        // Detect from localStorage or default
        this.locale = localStorage.getItem('localisa_lang') || 'es';
        await this.load(this.locale);
    },

    async load(locale) {
        try {
            const resp = await fetch(`/locales/${locale}.json`);
            this.messages = await resp.json();
            this.locale = locale;
            localStorage.setItem('localisa_lang', locale);
        } catch (e) {
            console.error('i18n load failed:', e);
        }
    },

    t(key) {
        return this.messages[key] || key;
    },

    async setLocale(locale) {
        await this.load(locale);
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (el.placeholder !== undefined && el.tagName === 'TEXTAREA') {
                el.placeholder = this.t(key);
            } else {
                el.textContent = this.t(key);
            }
        });
    }
};
