/** Human-readable agent name for dashboard labels. */
export function agentLabel(name: string): string {
  const cleaned = name
    .replace(/-graph$/i, "")
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .trim();
  // Slug-style ids → Title Case (e.g. "agreement analysis" → "Agreement Analysis")
  if (/^[a-z0-9\s]+$/.test(cleaned)) {
    return cleaned.replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return cleaned;
}
