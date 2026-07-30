export default {
  appName: 'Facio',
  projects: {
    title: 'Проекты',
    empty: 'Пока нет целей. Начните с первой.',
    newGoal: 'Новая цель',
    history: 'Архив',
    draft: 'Черновик',
    loading: 'Загрузка…',
    error: 'Не удалось загрузить проекты',
    retry: 'Повторить',
    apiBase: 'API',
  },
  intent: {
    title: 'Что вы хотите сделать?',
    placeholder: 'Например: приготовить карбонару',
    submit: 'Дальше',
    examplesLabel: 'Примеры',
  },
  instantAnswer: {
    cta: 'Хотите поставить цель вместо вопроса?',
  },
  draft: {
    title: 'Черновик пути',
    back: 'Назад',
    refine: 'Обновить путь',
    toAccept: 'К принятию',
  },
  accept: {
    title: 'Принять путь',
    commit: 'Принять путь',
    moreClarify: 'Ещё уточнить',
    success: 'Успех',
    horizon: 'Горизонт',
  },
  home: {
    today: 'Сегодня',
    whyNow: 'Почему сейчас',
    done: 'Сделано',
    skip: 'Пропустить',
    fullPath: 'Весь путь',
    repair: 'Не могу / сдвинуть',
  },
  path: {
    title: 'Весь путь',
  },
  history: {
    title: 'Архив',
    empty: 'Архив пуст',
  },
  theme: {
    system: 'Авто',
    light: 'Светлая',
    dark: 'Тёмная',
  },
  common: {
    placeholder: 'Экран будет в S2/S3',
    minutes: '{{count}} мин',
  },
} as const;
