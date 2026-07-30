import React from 'react';
import { useTranslation } from 'react-i18next';

import type { RootScreenProps } from '@/navigation/types';
import { PlaceholderScreen } from '@/shared/ui/PlaceholderScreen';

export function IntentScreen(_props: RootScreenProps<'Intent'>) {
  const { t } = useTranslation();
  return <PlaceholderScreen title={t('intent.title')} />;
}
