import React from 'react';
import { useTranslation } from 'react-i18next';

import type { RootScreenProps } from '@/navigation/types';
import { PlaceholderScreen } from '@/shared/ui/PlaceholderScreen';

export function ProjectHomeScreen({ route }: RootScreenProps<'ProjectHome'>) {
  const { t } = useTranslation();
  return (
    <PlaceholderScreen
      title={t('home.today')}
      subtitle={`projectId: ${route.params.projectId}`}
    />
  );
}
