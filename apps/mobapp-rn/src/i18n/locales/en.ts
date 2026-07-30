export default {
  appName: 'Facio',
  projects: {
    title: 'Projects',
    empty: 'No goals yet. Start with your first one.',
    newGoal: 'New goal',
    history: 'Archive',
    draft: 'Draft',
    loading: 'Loading…',
    error: 'Could not load projects',
    retry: 'Retry',
  },
  intent: {
    title: 'What do you want to do?',
    placeholder: 'e.g. cook carbonara',
    submit: 'Continue',
    examplesLabel: 'Examples',
  },
  instantAnswer: {
    cta: 'Want to set a goal instead?',
  },
  draft: {
    title: 'Path draft',
    back: 'Back',
    refine: 'Update path',
    toAccept: 'Review & accept',
  },
  accept: {
    title: 'Accept path',
    commit: 'Accept path',
    moreClarify: 'Clarify more',
    success: 'Success',
    horizon: 'Horizon',
  },
  home: {
    today: 'Today',
    whyNow: 'Why now',
    done: 'Done',
    skip: 'Skip',
    fullPath: 'Full path',
    repair: 'Cannot / reschedule',
  },
  path: {
    title: 'Full path',
  },
  history: {
    title: 'Archive',
    empty: 'Archive is empty',
  },
  theme: {
    system: 'Auto',
    light: 'Light',
    dark: 'Dark',
  },
  common: {
    placeholder: 'Screen lands in S2/S3',
    minutes: '{{count}} min',
  },
} as const;
