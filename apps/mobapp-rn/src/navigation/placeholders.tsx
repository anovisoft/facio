import React from 'react';
import { useTranslation } from 'react-i18next';

import type { RootScreenProps } from '@/navigation/types';
import { PlaceholderScreen } from '@/shared/ui/PlaceholderScreen';

type ProjectIdRoute = 'DraftStudio' | 'Accept' | 'ProjectHome' | 'Path';

/** Temporary S2/S3 shells — feature folders land when screens own real logic. */
export function placeholderScreen(titleKey: string) {
  return function PlaceholderRoute() {
    const { t } = useTranslation();
    return <PlaceholderScreen title={t(titleKey)} />;
  };
}

export function projectPlaceholderScreen(titleKey: string) {
  return function PlaceholderRoute({ route }: RootScreenProps<ProjectIdRoute>) {
    const { t } = useTranslation();
    return (
      <PlaceholderScreen
        title={t(titleKey)}
        subtitle={`projectId: ${route.params.projectId}`}
      />
    );
  };
}
