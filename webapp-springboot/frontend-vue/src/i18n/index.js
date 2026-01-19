import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import es from './locales/es.json'

const messages = {
  en,
  es
}

const i18n = createI18n({
  locale: localStorage.getItem('app-language') || 'en',
  fallbackLocale: 'en',
  messages,
  legacy: false,
  globalInjection: true
})

export default i18n