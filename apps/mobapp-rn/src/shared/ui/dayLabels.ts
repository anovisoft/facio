import type { DayKind } from '@/api/types';

export function capitalizeLabel(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function dayKindLabel(
  kind: DayKind,
  t: (key: string) => string,
): string {
  switch (kind) {
    case 'train':
      return t('dayKind.train');
    case 'rest':
      return t('dayKind.rest');
    case 'cook_session':
      return t('dayKind.cook_session');
    case 'other':
      return t('dayKind.other');
    default: {
      const _exhaustive: never = kind;
      return _exhaustive;
    }
  }
}
