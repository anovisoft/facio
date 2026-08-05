import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import {
  getPathState,
  manualEditProject,
  restoreState,
} from '@/api/projects';
import { ApiError } from '@/api/types';
import { ManualBlockEditor } from '@/features/manualEdit/ManualBlockEditor';
import { setPendingCreateManualEdit } from '@/features/manualEdit/pendingResult';
import {
  applyEditableActionsToState,
  extractEditableActions,
  type EditableActionTools,
  type PathStateJson,
} from '@/features/manualEdit/pathStateTools';
import type { RootScreenProps } from '@/navigation/types';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

/**
 * Manual editor screen — Create (plan card version) and Active (Session).
 * Loads PathState, edits closed UI Block tools, applies as user_edit + Undo.
 */
export function ManualEditScreen({
  navigation,
  route,
}: RootScreenProps<'ManualEdit'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { projectId, stateVersion, planIndex, actionKey, mode } = route.params;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** Tip version at open (Active) — Create uses card version only for load. */
  const [tipVersion, setTipVersion] = useState<number | null>(null);
  const [baseState, setBaseState] = useState<PathStateJson | null>(null);
  const [edits, setEdits] = useState<EditableActionTools[]>([]);

  useLayoutEffect(() => {
    navigation.setOptions({
      title:
        mode === 'create'
          ? t('manualEdit.titleCreate')
          : t('manualEdit.titleActive'),
    });
  }, [mode, navigation, t]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Create: load the card's version read-only (no restore until Save).
      // Active: always edit the live tip.
      const loadVersion =
        mode === 'create' && stateVersion != null ? stateVersion : null;
      const path = await getPathState(projectId, loadVersion);
      const tip = await getPathState(projectId);
      setTipVersion(tip.version);
      setBaseState(path.state as PathStateJson);
      setEdits(
        extractEditableActions(path.state as PathStateJson, actionKey ?? null),
      );
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : t('manualEdit.loadError'),
      );
    } finally {
      setLoading(false);
    }
  }, [actionKey, mode, projectId, stateVersion, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const onSave = async () => {
    if (saving || baseState == null || tipVersion == null) return;
    const emptyTitles = edits.some((a) =>
      a.checklistItems.some((c) => !c.title.trim()),
    );
    if (emptyTitles) {
      setError(t('manualEdit.emptyItemError'));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const proposed = applyEditableActionsToState(baseState, edits);
      let beforeVersion = tipVersion;

      // Create on an older card: restore that snapshot to tip, then apply.
      if (
        mode === 'create' &&
        stateVersion != null &&
        stateVersion !== tipVersion
      ) {
        // Restore card snapshot to tip, then apply Manual on the new tip.
        await restoreState(projectId, stateVersion);
        const tipAfter = await getPathState(projectId);
        beforeVersion = tipAfter.version;
      }

      const detail = await manualEditProject(projectId, {
        beforeVersion,
        proposedState: proposed,
      });
      if (mode === 'create') {
        setPendingCreateManualEdit({
          projectId,
          planIndex,
          detail,
        });
        navigation.goBack();
        return;
      }
      navigation.navigate({
        name: 'Session',
        params: {
          projectId,
          undoVersion: detail.undo_version ?? beforeVersion,
          undoMessage: t('manualEdit.applied'),
        },
        merge: true,
      });
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : t('manualEdit.saveError'),
      );
      // Tip may have moved (restore) — refresh tipVersion for retry.
      try {
        const tip = await getPathState(projectId);
        setTipVersion(tip.version);
      } catch {
        // Keep prior error.
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeScreen
      scroll
      footer={
        <View style={styles.footer}>
          <PrimaryButton
            label={t('manualEdit.save')}
            loading={saving}
            disabled={loading || saving || edits.length === 0}
            onPress={() => void onSave()}
          />
        </View>
      }
    >
      <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
        {mode === 'create'
          ? t('manualEdit.subtitleCreate')
          : t('manualEdit.subtitleActive')}
      </Text>

      {loading ? (
        <Text style={[styles.muted, { color: colors.textMuted }]}>
          {t('manualEdit.loading')}
        </Text>
      ) : (
        <ManualBlockEditor
          actions={edits}
          onChange={setEdits}
          disabled={saving}
        />
      )}

      {error ? (
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
      ) : null}
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  subtitle: {
    ...typography.body,
    marginBottom: spacing.md,
  },
  muted: {
    ...typography.caption,
  },
  error: {
    ...typography.caption,
    marginTop: spacing.sm,
  },
  footer: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
});
