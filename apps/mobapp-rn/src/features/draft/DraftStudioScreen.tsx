import React from 'react';
import { useTranslation } from 'react-i18next';

import type { RootScreenProps } from '@/navigation/types';
import { PlaceholderScreen } from '@/shared/ui/PlaceholderScreen';

export function DraftStudioScreen({ route }: RootScreenProps<'DraftStudio'>) {
  const { t } = useTranslation();
  return (
    <PlaceholderScreen
      title={t('draft.title')}
      subtitle={`projectId: ${route.params.projectId}`}
    />
  );
}
