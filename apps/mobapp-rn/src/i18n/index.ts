import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import * as Localization from 'expo-localization';

import en from '@/i18n/locales/en';
import ru from '@/i18n/locales/ru';

/** English first; Russian when the device language is Russian. */
const deviceLang = Localization.getLocales()[0]?.languageCode ?? 'en';
const lng = deviceLang === 'ru' ? 'ru' : 'en';

void i18n.use(initReactI18next).init({
  compatibilityJSON: 'v4',
  resources: {
    en: { translation: en },
    ru: { translation: ru },
  },
  lng,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export default i18n;
