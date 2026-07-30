import React, {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { StyleSheet, Text } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { toggleChecklistItem } from '@/api/actions';
import { getProject } from '@/api/projects';
import { ApiError, type ProjectDetail } from '@/api/types';
import type { RootScreenProps } from '@/navigation/types';
import { trackPathOpened } from '@/services/beacons';
import { AsyncState } from '@/shared/ui/AsyncState';
import { PathList } from '@/shared/ui/PathList';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

export function PathScreen({ navigation, route }: RootScreenProps<'Path'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { projectId } = route.params;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const trackedRef = useRef(false);

  useLayoutEffect(() => {
    navigation.setOptions({ title: t('path.title') });
  }, [navigation, t]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const detail = await getProject(projectId);
      setProject(detail);
      if (!trackedRef.current) {
        trackedRef.current = true;
        trackPathOpened(projectId);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('path.error'));
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const onToggleChecklist = async (itemId: string, nextDone: boolean) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await toggleChecklistItem(itemId, nextDone);
      setProject((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          actions: prev.actions.map((action) => ({
            ...action,
            checklist_items: action.checklist_items.map((item) =>
              item.id === itemId ? { ...item, done: nextDone } : item,
            ),
          })),
          next_action:
            prev.next_action == null
              ? prev.next_action
              : {
                  ...prev.next_action,
                  checklist_items: prev.next_action.checklist_items.map(
                    (item) =>
                      item.id === itemId
                        ? { ...item, done: nextDone }
                        : item,
                  ),
                },
        };
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('path.error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeScreen scroll={Boolean(project) && !loading}>
      <AsyncState
        loading={loading && !project}
        error={!project ? error : null}
        empty={Boolean(project && project.actions.length === 0)}
        emptyMessage={t('path.empty')}
        loadingMessage={t('path.loading')}
        retryLabel={t('projects.retry')}
        onRetry={() => void load()}
      >
        {project ? (
          <>
            {error ? (
              <Text style={[styles.error, { color: colors.error }]}>
                {error}
              </Text>
            ) : null}
            <PathList
              groups={project.groups}
              actions={project.actions}
              expandable
              checklistDisabled={busy}
              onToggleChecklist={(item, done) =>
                void onToggleChecklist(item.id, done)
              }
            />
          </>
        ) : null}
      </AsyncState>
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  error: {
    ...typography.caption,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
});
