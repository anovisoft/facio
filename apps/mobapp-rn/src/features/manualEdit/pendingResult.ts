import type { ProjectDetail } from '@/api/types';

/** One-shot handoff after Manual save on Create → Plan Feed card refresh. */
export type PendingCreateManualEdit = {
  projectId: string;
  planIndex?: number;
  detail: ProjectDetail;
};

let pendingCreate: PendingCreateManualEdit | null = null;

export function setPendingCreateManualEdit(
  value: PendingCreateManualEdit,
): void {
  pendingCreate = value;
}

export function takePendingCreateManualEdit(
  projectId: string,
): PendingCreateManualEdit | null {
  if (!pendingCreate || pendingCreate.projectId !== projectId) return null;
  const value = pendingCreate;
  pendingCreate = null;
  return value;
}
