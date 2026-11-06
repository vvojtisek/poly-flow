import type { RankPath, RankTier } from "@/lib/api";
import { TIER_STYLE, rankIcon, rankName } from "@/lib/ranks";

const SIZES = {
  sm: { box: "size-8", pad: "p-[2px]", icon: "size-4", num: "hidden" },
  md: { box: "size-14", pad: "p-[3px]", icon: "size-7", num: "text-[0.6rem] -bottom-1 px-1" },
  lg: { box: "size-28", pad: "p-1", icon: "size-14", num: "text-xs -bottom-2 px-2 py-0.5" },
};

/** The rank's emblem: a tier-coloured ring (bronze to diamond) around the theme's icon. */
export function RankEmblem({
  path,
  rank,
  tier,
  size = "md",
  locked = false,
  className = "",
}: {
  path: RankPath;
  rank: number;
  tier: RankTier;
  size?: keyof typeof SIZES;
  locked?: boolean;
  className?: string;
}) {
  const Icon = rankIcon(path, rank);
  const s = SIZES[size];
  const t = TIER_STYLE[tier];
  return (
    <span
      className={`relative inline-flex shrink-0 rounded-full bg-gradient-to-br ${s.box} ${s.pad} ${
        locked ? "from-slate-300 to-slate-200 opacity-60 grayscale dark:from-slate-700 dark:to-slate-800" : t.ring
      } ${className}`}
      role="img"
      aria-label={rankName(path, rank)}
    >
      <span className="flex size-full items-center justify-center rounded-full bg-white dark:bg-slate-900">
        <Icon className={`${s.icon} ${locked ? "text-slate-400" : t.icon}`} aria-hidden />
      </span>
      <span
        className={`absolute left-1/2 -translate-x-1/2 rounded-full bg-slate-900 font-bold text-white dark:bg-white dark:text-slate-900 ${s.num}`}
        aria-hidden
      >
        {rank}
      </span>
    </span>
  );
}
