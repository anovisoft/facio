import { useCallback, useEffect, useRef, useState } from 'react';

import {
  repairProject,
  repairProjectPreview,
} from '@/api/projects';
import {
  ApiError,
  type ClarifyQuestion,
  type ProjectDetail,
  type RepairIntent,
} from '@/api/types';
import {
  proposalFromPreview,
  questionsFromProposedState,
  type AiFeedItem,
  type AiFeedProposal,
} from '@/features/aiFeed/types';

let feedIdSeq = 0;
function nextId(prefix: string): string {
  feedIdSeq += 1;
  return `${prefix}-${feedIdSeq}`;
}

function questionRoundKey(questions: ClarifyQuestion[]): string {
  return questions.map((q) => q.id).join('|');
}

type RunPreviewArgs = {
  reason: string;
  intent?: RepairIntent | null;
  /** When false, caller already appended the user turn. */
  appendUser?: boolean;
  userText?: string;
};

/**
 * Append-only Active AI Feed: intents / freeform → preview proposals → apply.
 * Reuses Slice E repair/preview + repair; never expands Anthropic schemas.
 */
export function useActiveAiFeed(projectId: string) {
  const [items, setItems] = useState<AiFeedItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const proposalCountRef = useRef(0);
  const lastQuestionsKeyRef = useRef('');
  const abortRef = useRef<AbortController | null>(null);
  const seededRef = useRef(false);

  useEffect(() => {
    setItems([]);
    proposalCountRef.current = 0;
    lastQuestionsKeyRef.current = '';
    seededRef.current = false;
    setError(null);
    abortRef.current?.abort();
  }, [projectId]);

  const appendSystemNote = useCallback((text: string) => {
    setItems((prev) => [
      ...prev,
      { id: nextId('note'), kind: 'system_note', text },
    ]);
  }, []);

  const runPreview = useCallback(
    async ({
      reason,
      intent,
      appendUser = true,
      userText,
    }: RunPreviewArgs): Promise<AiFeedProposal | null> => {
      const trimmed = reason.trim();
      if (!trimmed && !intent) return null;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setBusy(true);
      setError(null);

      if (appendUser) {
        const text = (userText ?? trimmed).trim();
        if (text) {
          setItems((prev) => [
            ...prev,
            { id: nextId('user'), kind: 'user_turn', text },
          ]);
        }
      }

      try {
        const preview = await repairProjectPreview(
          projectId,
          {
            intent: intent ?? undefined,
            reason: trimmed || undefined,
          },
          controller.signal,
        );
        if (controller.signal.aborted) return null;

        const proposal = proposalFromPreview(preview, trimmed, intent);
        const questions = questionsFromProposedState(preview.proposed_state);
        const hasDiff = proposal.diff.length > 0;
        const qKey = questionRoundKey(questions);

        setItems((prev) => {
          let next = prev;
          if (preview.summary?.trim()) {
            next = [
              ...next,
              {
                id: nextId('sense'),
                kind: 'sense',
                text: preview.summary.trim(),
              },
            ];
          }

          if (hasDiff) {
            proposalCountRef.current += 1;
            next = [
              ...next,
              {
                id: nextId('proposal'),
                kind: 'proposal_card',
                proposalIndex: proposalCountRef.current,
                proposal,
              },
            ];
          }

          if (questions.length > 0 && qKey !== lastQuestionsKeyRef.current) {
            lastQuestionsKeyRef.current = qKey;
            next = [
              ...next,
              {
                id: nextId('questions'),
                kind: 'questions',
                questions,
                roundKey: qKey,
              },
            ];
          }

          if (!hasDiff && questions.length === 0) {
            next = [
              ...next,
              {
                id: nextId('note'),
                kind: 'system_note',
                text: 'no_changes',
              },
            ];
          }

          return next;
        });

        return hasDiff ? proposal : null;
      } catch (e) {
        if (controller.signal.aborted) return null;
        const message =
          e instanceof ApiError ? e.message : 'preview_failed';
        setError(message);
        appendSystemNote(message);
        return null;
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    },
    [appendSystemNote, projectId],
  );

  const applyProposal = useCallback(
    async (
      proposal: AiFeedProposal,
      proposalItemId: string,
    ): Promise<{ detail: ProjectDetail; undoVersion: number } | null> => {
      setBusy(true);
      setError(null);
      try {
        const detail = await repairProject(projectId, {
          intent: proposal.intent ?? undefined,
          reason: proposal.reason || undefined,
          proposed_state: proposal.proposedState,
          before_version: proposal.beforeVersion,
        });
        const undoVersion =
          detail.undo_version ?? proposal.beforeVersion;
        setItems((prev) =>
          prev.map((item) =>
            item.id === proposalItemId && item.kind === 'proposal_card'
              ? { ...item, applied: true }
              : item,
          ),
        );
        return { detail, undoVersion };
      } catch (e) {
        const message = e instanceof ApiError ? e.message : 'apply_failed';
        setError(message);
        return null;
      } finally {
        setBusy(false);
      }
    },
    [projectId],
  );

  const markSeeded = useCallback(() => {
    seededRef.current = true;
  }, []);

  const wasSeeded = useCallback(() => seededRef.current, []);

  return {
    items,
    busy,
    error,
    setError,
    runPreview,
    applyProposal,
    appendSystemNote,
    markSeeded,
    wasSeeded,
  };
}
