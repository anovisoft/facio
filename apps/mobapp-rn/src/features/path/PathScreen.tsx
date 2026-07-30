import React from 'react';
import { useTranslation } from 'react-i18next';

import type { RootScreenProps } from '@/navigation/types';
import { PlaceholderScreen } from '@/shared/ui/PlaceholderScreen';

export function PathScreen({ route }: RootScreenProps<'Path'>) {
  const { t } = useTranslation();
  return (
    <PlaceholderScreen
      title={t('path.title')}
      subtitle={`projectId: ${route.params.projectId}`}
    />
  );
}
