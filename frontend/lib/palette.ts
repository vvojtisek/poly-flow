// Command palette matching: diacritics- and case-insensitive, words in any order, prefix and
// initial-letter matches rank first. Pure functions so they are easy to reason about.

export function fold(s: string): string {
  return s
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase();
}

/** Score of `query` against `text` (+ keywords); 0 = no match. Higher is better. */
export function score(query: string, text: string, keywords: string[] = []): number {
  const q = fold(query).trim();
  if (!q) return 1;
  const hay = fold([text, ...keywords].join(" "));
  const words = hay.split(/[^\p{L}\p{N}+]+/u).filter(Boolean);
  let total = 0;
  for (const part of q.split(/\s+/)) {
    if (words.some((w) => w === part)) total += 6;
    else if (words.some((w) => w.startsWith(part))) total += 4;
    else if (hay.includes(part)) total += 2;
    else if (part.length >= 3 && words.some((w) => isSubsequence(part, w))) total += 1;
    else return 0;
  }
  if (fold(text).startsWith(q)) total += 3;
  return total;
}

function isSubsequence(needle: string, hay: string): boolean {
  let i = 0;
  for (const ch of hay) if (ch === needle[i] && ++i === needle.length) return true;
  return needle.length === 0;
}

export function rank<T extends { label: string; keywords?: string[] }>(query: string, items: T[], limit = 9): T[] {
  return items
    .map((item, i) => ({ item, i, s: score(query, item.label, item.keywords) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s || a.i - b.i)
    .slice(0, limit)
    .map((x) => x.item);
}
