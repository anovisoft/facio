import { useCallback, useEffect, useRef, useState } from 'react';

import type { ClarifyQuestion, ProjectDetail } from '@/api/types';
import {
  capturePlanSnapshot,
  isPathReady,
  planContentFingerprint,
  senseText,
} from '@/features/guide/planFeed/snapshot';
import type {
  PlanFeedItem,
  PlanSnapshot,
} from '@/features/guide/planFeed/types';
import { useSessionStore } from '@/store';

let feedIdSeq = 0;
function nextId(prefix: string): string {
  feedIdSeq += 1;
  return `${prefix}-${feedIdSeq}`;
}

function questionRoundKey(questions: ClarifyQuestion[]): string {
  return questions.map((q) => q.id).join('|');
}

/**
 * Append-only Plan Feed state for Create/Explore (Slice E2a).
 * Snapshots plan cards client-side; prior cards stay after refine.
 * Hydrates from session store so reopen keeps feed history.
 */
export function usePlanFeed(projectId: string) {
  const [items, setItems] = useState<PlanFeedItem[]>([]);
  const seededProjectRef = useRef<string | null>(null);
  const lastPlanFpRef = useRef<string | null>(null);
  const lastQuestionsKeyRef = useRef<string>('');
  const planCountRef = useRef(0);
  const pendingLoadingCardIdRef = useRef<string | null>(null);
  const setPlanFeed = useSessionStore((s) => s.setPlanFeed);
  const clearPlanFeedStore = useSessionStore((s) => s.clearPlanFeed);

  const persistFeed = useCallback(
    (nextItems: PlanFeedItem[]) => {
      if (!projectId || nextItems.length === 0) return;
      setPlanFeed(projectId, {
        items: nextItems,
        lastPlanFp: lastPlanFpRef.current,
        lastQuestionsKey: lastQuestionsKeyRef.current,
        planCount: planCountRef.current,
      });
    },
    [projectId, setPlanFeed],
  );

  const reset = useCallback(() => {
    setItems([]);
    seededProjectRef.current = null;
    lastPlanFpRef.current = null;
    lastQuestionsKeyRef.current = '';
    planCountRef.current = 0;
    pendingLoadingCardIdRef.current = null;
  }, []);

  const clear = useCallback(() => {
    reset();
    if (projectId) clearPlanFeedStore(projectId);
  }, [clearPlanFeedStore, projectId, reset]);

  // Project switch: drop in-memory feed; next sync will hydrate or seed.
  useEffect(() => {
    reset();
  }, [projectId, reset]);

  const appendUserTurn = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      setItems((prev) => {
        const next: PlanFeedItem[] = [
          ...prev,
          { id: nextId('user'), kind: 'user_turn', text: trimmed },
        ];
        persistFeed(next);
        return next;
      });
    },
    [persistFeed],
  );

  const syncFromProject = useCallback(
    (project: ProjectDetail) => {
      if (project.status !== 'draft') return;

      setItems((prev) => {
        let next = prev;
        const ensure = (mutate: (list: PlanFeedItem[]) => PlanFeedItem[]) => {
          next = mutate(next);
        };

        // Seed once per project: hydrate from store, or intent + sense.
        if (seededProjectRef.current !== project.id) {
          seededProjectRef.current = project.id;
          pendingLoadingCardIdRef.current = null;

          const stored =
            useSessionStore.getState().planFeedByProjectId[project.id];
          if (stored && stored.items.length > 0) {
            lastPlanFpRef.current = stored.lastPlanFp;
            lastQuestionsKeyRef.current = stored.lastQuestionsKey;
            planCountRef.current = stored.planCount;
            next = stored.items;
          } else {
            lastPlanFpRef.current = null;
            lastQuestionsKeyRef.current = '';
            planCountRef.current = 0;
            next = [];

            const intent = project.raw_intent?.trim();
            if (intent) {
              next = [
                ...next,
                { id: nextId('user'), kind: 'user_turn', text: intent },
              ];
            }
            const sense = senseText(project);
            if (sense) {
              next = [
                ...next,
                { id: nextId('sense'), kind: 'sense', text: sense },
              ];
            }
          }
        } else {
          // Sense may arrive after soft-start gate.
          const sense = senseText(project);
          if (sense && !next.some((i) => i.kind === 'sense')) {
            const firstPlanIdx = next.findIndex((i) => i.kind === 'plan_card');
            const senseItem: PlanFeedItem = {
              id: nextId('sense'),
              kind: 'sense',
              text: sense,
            };
            if (firstPlanIdx === -1) {
              next = [...next, senseItem];
            } else {
              next = [
                ...next.slice(0, firstPlanIdx),
                senseItem,
                ...next.slice(firstPlanIdx),
              ];
            }
          }
        }

        const ready = isPathReady(project);
        const pathError = project.path_error ?? null;

        if (ready || pathError) {
          const snapshot = capturePlanSnapshot(project);
          const fp = planContentFingerprint(snapshot);
          const loadingId = pendingLoadingCardIdRef.current;
          const existingVersionId =
            snapshot.stateVersion != null
              ? next.find(
                  (i) =>
                    i.kind === 'plan_card' &&
                    i.snapshot.stateVersion === snapshot.stateVersion,
                )
              : undefined;

          if (loadingId) {
            // Upgrade in-flight loading card in place (same version, not a new revision).
            ensure((list) =>
              list.map((item) =>
                item.id === loadingId && item.kind === 'plan_card'
                  ? { ...item, snapshot }
                  : item,
              ),
            );
            pendingLoadingCardIdRef.current = null;
            lastPlanFpRef.current = fp;
          } else if (existingVersionId && existingVersionId.kind === 'plan_card') {
            // Already snapshotted this state_version (e.g. restore-before-commit).
            ensure((list) =>
              list.map((item) =>
                item.id === existingVersionId.id
                  ? { ...item, snapshot }
                  : item,
              ),
            );
          } else if (lastPlanFpRef.current !== fp) {
            planCountRef.current += 1;
            const planIndex = planCountRef.current;
            ensure((list) => [
              ...list,
              {
                id: nextId('plan'),
                kind: 'plan_card',
                planIndex,
                snapshot,
              },
            ]);
            lastPlanFpRef.current = fp;
          } else {
            // Same plan content — refresh latest matching card snapshot (version id).
            ensure((list) => {
              const lastPlan = [...list]
                .reverse()
                .find((i) => i.kind === 'plan_card');
              if (!lastPlan || lastPlan.kind !== 'plan_card') return list;
              return list.map((item) =>
                item.id === lastPlan.id
                  ? { ...item, snapshot: { ...snapshot } }
                  : item,
              );
            });
          }
        } else if (
          !ready &&
          !pathError &&
          planCountRef.current === 0 &&
          !pendingLoadingCardIdRef.current
        ) {
          // Soft-start: show outline card while #2 Path builds.
          planCountRef.current = 1;
          const loadingId = nextId('plan');
          pendingLoadingCardIdRef.current = loadingId;
          ensure((list) => [
            ...list,
            {
              id: loadingId,
              kind: 'plan_card',
              planIndex: 1,
              snapshot: capturePlanSnapshot(project),
            },
          ]);
        } else if (pendingLoadingCardIdRef.current) {
          // Keep outline days fresh while polling.
          const loadingId = pendingLoadingCardIdRef.current;
          const snapshot = capturePlanSnapshot(project);
          ensure((list) =>
            list.map((item) =>
              item.id === loadingId && item.kind === 'plan_card'
                ? { ...item, snapshot }
                : item,
            ),
          );
        }

        const questions = project.questions ?? [];

        // Clarify can appear during soft-start (#1) before Path v1 is ready —
        // do not gate chips on pathReady (PO dogfood). Notes-only block waits
        // until a plan card exists. Refine still waits for path in Explore.
        // Always place questions after the latest plan card (end of that step).
        // Soft-start may show questions while path loads; once a new plan
        // appends, re-append questions below it even if roundKey is unchanged.
        const upsertQuestionsItem = (
          qKey: string,
          qs: ClarifyQuestion[],
        ) => {
          const keyChanged = qKey !== lastQuestionsKeyRef.current;
          lastQuestionsKeyRef.current = qKey;
          ensure((list) => {
            const existing = list.find(
              (i) => i.kind === 'questions' && i.roundKey === qKey,
            );
            const withoutActive = list.filter((i) => i.kind !== 'questions');
            return [
              ...withoutActive,
              {
                id:
                  !keyChanged && existing
                    ? existing.id
                    : nextId('questions'),
                kind: 'questions' as const,
                questions: qs,
                roundKey: qKey,
              },
            ];
          });
        };

        if (questions.length > 0) {
          upsertQuestionsItem(questionRoundKey(questions), questions);
        } else if (ready || pathError) {
          upsertQuestionsItem('notes-only', []);
        } else if (lastQuestionsKeyRef.current === 'notes-only') {
          ensure((list) => list.filter((i) => i.kind !== 'questions'));
          lastQuestionsKeyRef.current = '';
        }

        persistFeed(next);
        return next;
      });
    },
    [persistFeed],
  );

  const updatePlanCard = useCallback(
    (planIndex: number, snapshot: PlanSnapshot) => {
      setItems((prev) => {
        const next = prev.map((item) =>
          item.kind === 'plan_card' && item.planIndex === planIndex
            ? { ...item, snapshot }
            : item,
        );
        // Keep fingerprint aligned so sync won't append a twin card.
        lastPlanFpRef.current = planContentFingerprint(snapshot);
        persistFeed(next);
        return next;
      });
    },
    [persistFeed],
  );

  return {
    items,
    appendUserTurn,
    syncFromProject,
    updatePlanCard,
    reset,
    clear,
  };
}
