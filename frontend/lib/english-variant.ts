/** Curated spelling differences only; vocabulary and expressions need authored content. */
const UK_TO_US: ReadonlyArray<readonly [string, string]> = [
  ["colour", "color"], ["favourite", "favorite"], ["centre", "center"],
  ["theatre", "theater"], ["neighbour", "neighbor"], ["organise", "organize"],
  ["realise", "realize"], ["travelling", "traveling"], ["travelled", "traveled"],
  ["defence", "defense"], ["licence", "license"],
  ["lorry", "truck"], ["petrol", "gasoline"], ["mobile phone", "cell phone"],
  ["postcode", "zip code"],
];

export function englishVariantText(text: string, variant: "uk" | "us"): string {
  if (variant === "uk") return text;
  return UK_TO_US.reduce((result, [uk, us]) => result.replace(new RegExp(`\\b${uk}\\b`, "gi"), (match) => {
    if (match === match.toUpperCase()) return us.toUpperCase();
    if (match[0] === match[0]?.toUpperCase()) return us[0]!.toUpperCase() + us.slice(1);
    return us;
  }), text);
}
