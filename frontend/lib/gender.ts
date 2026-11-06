// Colour per grammatical gender, used wherever an article or gender is shown: a visual
// mnemonic (der blue, die red, das green; French/Italian m blue, f red).

const COLORS: Record<string, string> = {
  der: "text-sky-700 dark:text-sky-300",
  die: "text-rose-700 dark:text-rose-300",
  das: "text-emerald-700 dark:text-emerald-300",
  m: "text-sky-700 dark:text-sky-300",
  f: "text-rose-700 dark:text-rose-300",
};

export function genderClass(gender: string | null | undefined): string {
  return (gender && COLORS[gender.toLowerCase()]) || "";
}
