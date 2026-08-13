/**
 * Soft-start paraphrase may already include the UI prefix from API/seed
 * (e.g. "Ок — ведём к: …" / "Ok — heading toward: …").
 * Never wrap again — show once.
 */
const SOFT_START_PREFIX =
  /^(?:ок\s*[—–-]\s*ведём к:\s*|ok\s*[—–-]\s*heading toward:\s*)/i;

export function alreadyHasSoftStartPrefix(text: string): boolean {
  return SOFT_START_PREFIX.test(text.trim());
}

/**
 * Display line for soft-start: wrap with i18n template only when paraphrase
 * does not already carry the known prefix.
 */
export function softStartDisplayLine(
  paraphrase: string,
  wrap: (bare: string) => string,
): string {
  const trimmed = paraphrase.trim();
  if (!trimmed) return '';
  if (alreadyHasSoftStartPrefix(trimmed)) return trimmed;
  return wrap(trimmed);
}
