import type {
  ClarifyQuestion,
  RepairDiffLine,
  RepairIntent,
  RepairPreviewResponse,
} from '@/api/types';

/** Closed Active AI Feed item kinds (Facio 0.1 Slice E2c / edit surfaces). */
export type AiFeedItemKind =
  | 'user_turn'
  | 'sense'
  | 'proposal_card'
  | 'questions'
  | 'system_note';

export type AiFeedProposal = {
  beforeVersion: number;
  summary?: string | null;
  diff: RepairDiffLine[];
  proposedState: Record<string, unknown>;
  intent?: RepairIntent | null;
  reason: string;
};

export type AiFeedItem =
  | { id: string; kind: 'user_turn'; text: string }
  | { id: string; kind: 'sense'; text: string }
  | {
      id: string;
      kind: 'proposal_card';
      proposalIndex: number;
      proposal: AiFeedProposal;
      /** True after apply — card stays in lenta, CTA disabled. */
      applied?: boolean;
    }
  | {
      id: string;
      kind: 'questions';
      questions: ClarifyQuestion[];
      roundKey: string;
    }
  | { id: string; kind: 'system_note'; text: string };

export function proposalFromPreview(
  preview: RepairPreviewResponse,
  reason: string,
  intent?: RepairIntent | null,
): AiFeedProposal {
  return {
    beforeVersion: preview.before_version,
    summary: preview.summary,
    diff: preview.diff ?? [],
    proposedState: preview.proposed_state,
    intent: intent ?? null,
    reason,
  };
}

export function questionsFromProposedState(
  proposedState: Record<string, unknown>,
): ClarifyQuestion[] {
  const raw = proposedState.questions;
  if (!Array.isArray(raw)) return [];
  const out: ClarifyQuestion[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue;
    const q = item as Record<string, unknown>;
    const id = typeof q.id === 'string' ? q.id.trim() : '';
    const prompt = typeof q.prompt === 'string' ? q.prompt.trim() : '';
    if (!id || !prompt) continue;
    const options = Array.isArray(q.options)
      ? q.options.filter((o): o is string => typeof o === 'string' && !!o.trim())
      : [];
    const selection =
      q.selection === 'multi' || q.selection === 'single'
        ? q.selection
        : undefined;
    out.push({ id, prompt, options, selection });
  }
  return out;
}
