import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from '../locales/en/common.json'
import zh from '../locales/zh/common.json'

// Initialize i18n with in-bundle resources and language detector
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      zh: { translation: zh },
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'zh'],
    interpolation: { escapeValue: false },
    detection: {
      // Persist selection and honor browser language; localStorage key below
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'devui:i18n-lang',
    },
  })

// Keep <html lang="..."> in sync with current language
i18n.on('languageChanged', (lng) => {
  const code = (lng || 'en').startsWith('zh') ? 'zh-CN' : 'en'
  document.documentElement.setAttribute('lang', code)
})

// Set initial lang attribute
const initCode = (i18n.language || 'en').startsWith('zh') ? 'zh-CN' : 'en'
document.documentElement.setAttribute('lang', initCode)

export default i18n
