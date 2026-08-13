import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import Animated, { useAnimatedRef } from 'react-native-reanimated';

import {
  getPathState,
  manualEditProject,
  restoreState,
} from '@/api/projects';
import { ApiError, type RepairIntent } from '@/api/types';
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
import { radii, spacing, typography } from '@/theme';

const INTENTS: RepairIntent[] = ['shift', 'lighten', 'rest'];

function intentLabelKey(intent: RepairIntent): string {
  switch (intent) {
    case 'shift':
      return 'home.repairShift';
    case 'lighten':
      return 'home.repairLighten';
    case 'rest':
      return 'home.repairRest';
    default: {
      const _exhaustive: never = intent;
      return _exhaustive;
    }
  }
}

/**
 * Manual editor screen — Create (plan card version) and Active (Session).
 * Loads PathState, edits closed UI Block tools, applies as user_edit + Undo.
 * Active: intent chips + «Rebuild with AI» open Active AI Feed (E2c).
 */
export function ManualEditScreen({
  navigation,
  route,
}: RootScreenProps<'ManualEdit'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { projectId, stateVersion, planIndex, actionKey, mode } = route.params;
  const scrollRef = useAnimatedRef<Animated.ScrollView>();

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

  const persistActiveEdits = async (): Promise<number | null> => {
    if (baseState == null || tipVersion == null) return null;
    const emptyTitles = edits.some((a) =>
      a.checklistItems.some((c) => !c.title.trim()),
    );
    if (emptyTitles) {
      setError(t('manualEdit.emptyItemError'));
      return null;
    }
    const proposed = applyEditableActionsToState(baseState, edits);
    let beforeVersion = tipVersion;

    if (
      mode === 'create' &&
      stateVersion != null &&
      stateVersion !== tipVersion
    ) {
      await restoreState(projectId, stateVersion);
      const tipAfter = await getPathState(projectId);
      beforeVersion = tipAfter.version;
    }

    const detail = await manualEditProject(projectId, {
      beforeVersion,
      proposedState: proposed,
    });
    return detail.undo_version ?? beforeVersion;
  };

  const onSave = async () => {
    if (saving || baseState == null || tipVersion == null) return;
    setSaving(true);
    setError(null);
    try {
      if (mode === 'create') {
        const emptyTitles = edits.some((a) =>
          a.checklistItems.some((c) => !c.title.trim()),
        );
        if (emptyTitles) {
          setError(t('manualEdit.emptyItemError'));
          return;
        }
        const proposed = applyEditableActionsToState(baseState, edits);
        let beforeVersion = tipVersion;
        if (stateVersion != null && stateVersion !== tipVersion) {
          await restoreState(projectId, stateVersion);
          const tipAfter = await getPathState(projectId);
          beforeVersion = tipAfter.version;
        }
        const detail = await manualEditProject(projectId, {
          beforeVersion,
          proposedState: proposed,
        });
        setPendingCreateManualEdit({
          projectId,
          planIndex,
          detail,
        });
        navigation.goBack();
        return;
      }

      const undoVersion = await persistActiveEdits();
      if (undoVersion == null) return;
      navigation.navigate({
        name: 'Session',
        params: {
          projectId,
          undoVersion,
          undoMessage: t('manualEdit.applied'),
        },
        merge: true,
      });
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : t('manualEdit.saveError'),
      );
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

  const openAiFeed = (opts?: {
    intent?: RepairIntent | null;
    seedReason?: string | null;
    saveFirst?: boolean;
  }) => {
    void (async () => {
      if (saving) return;
      setSaving(true);
      setError(null);
      try {
        if (opts?.saveFirst) {
          const undoVersion = await persistActiveEdits();
          if (undoVersion == null) return;
          // Refresh tip so feed previews against post-Manual state.
          const tip = await getPathState(projectId);
          setTipVersion(tip.version);
          setBaseState(tip.state as PathStateJson);
          setEdits(
            extractEditableActions(
              tip.state as PathStateJson,
              actionKey ?? null,
            ),
          );
        }
        navigation.navigate('ActiveAiFeed', {
          projectId,
          initialIntent: opts?.intent ?? null,
          seedReason: opts?.seedReason ?? null,
          openManual: false,
        });
      } catch (e) {
        setError(
          e instanceof ApiError ? e.message : t('manualEdit.saveError'),
        );
        try {
          const tip = await getPathState(projectId);
          setTipVersion(tip.version);
        } catch {
          // Keep prior error.
        }
      } finally {
        setSaving(false);
      }
    })();
  };

  const footer =
    mode === 'create' ? (
      <View style={styles.footer}>
        <PrimaryButton
          label={t('manualEdit.save')}
          loading={saving}
          disabled={loading || saving || edits.length === 0}
          onPress={() => void onSave()}
        />
      </View>
    ) : (
      <View style={styles.footer}>
        <PrimaryButton
          label={t('manualEdit.save')}
          loading={saving}
          disabled={loading || saving || edits.length === 0}
          onPress={() => void onSave()}
        />
        <PrimaryButton
          variant="secondary"
          label={t('manualEdit.saveWithAi')}
          disabled={loading || saving}
          onPress={() =>
            openAiFeed({
              saveFirst: edits.length > 0,
              seedReason: t('aiFeed.seedManualRebuild'),
            })
          }
        />
      </View>
    );

  return (
    <SafeScreen scroll scrollRef={scrollRef} footer={footer}>
      <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
        {mode === 'create'
          ? t('manualEdit.subtitleCreate')
          : t('manualEdit.subtitleActive')}
      </Text>

      {mode === 'active' ? (
        <View style={styles.aiSection}>
          <Text style={[styles.aiLabel, { color: colors.text }]}>
            {t('manualEdit.aiSection')}
          </Text>
          <View style={styles.chips}>
            {INTENTS.map((intent) => (
              <Pressable
                key={intent}
                disabled={loading || saving}
                onPress={() => openAiFeed({ intent })}
                style={[
                  styles.chip,
                  {
                    borderColor: colors.border,
                    backgroundColor: colors.surface,
                    opacity: loading || saving ? 0.5 : 1,
                  },
                ]}
              >
                <Text style={[styles.chipText, { color: colors.text }]}>
                  {t(intentLabelKey(intent))}
                </Text>
              </Pressable>
            ))}
          </View>
          <PrimaryButton
            variant="ghost"
            label={t('manualEdit.openAiFeed')}
            disabled={loading || saving}
            onPress={() => openAiFeed()}
          />
        </View>
      ) : null}

      {loading ? (
        <Text style={[styles.muted, { color: colors.textMuted }]}>
          {t('manualEdit.loading')}
        </Text>
      ) : (
        <ManualBlockEditor
          actions={edits}
          onChange={setEdits}
          disabled={saving}
          scrollableRef={scrollRef}
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
  aiSection: {
    marginBottom: spacing.lg,
    gap: spacing.sm,
  },
  aiLabel: {
    ...typography.body,
    fontWeight: '600',
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  chip: {
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  chipText: {
    ...typography.caption,
    fontWeight: '600',
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
    gap: spacing.sm,
  },
});
