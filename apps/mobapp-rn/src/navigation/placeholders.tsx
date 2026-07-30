import React from 'react';
import { useTranslation } from 'react-i18next';

import type { RootScreenProps } from '@/navigation/types';
import { PlaceholderScreen } from '@/shared/ui/PlaceholderScreen';

type ProjectIdRoute = 'ProjectHome' | 'Path';

/** Temporary S3 shells — Home/Path land in the daily-loop session. */
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
