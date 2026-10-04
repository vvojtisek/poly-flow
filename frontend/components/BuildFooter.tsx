import { buildInfo } from "@/lib/buildInfo";
import { cs } from "@/lib/i18n/cs";

// Release builds show "PolyFlow 1.0.0 · abc1234"; anything else also names its branch and is badged,
// so a development or pre-release build is never mistaken for the released app.
export function BuildFooter() {
  const { version, prerelease, commit, branch, builtAt, devServer } = buildInfo;
  const parts = [`${cs.appName} ${version}`, ...(prerelease || devServer ? [branch] : []), commit];

  return (
    <footer
      className="flex flex-wrap items-center justify-center gap-2 px-4 pb-4 text-xs text-slate-400 dark:text-slate-500"
      title={builtAt ? cs.build.builtAt(builtAt) : undefined}
      data-testid="build-info"
    >
      <span className="text-center font-mono">{parts.join(" · ")}</span>
      {devServer && (
        <span className="rounded bg-amber-100 px-1.5 py-0.5 font-semibold text-amber-800 dark:bg-amber-950 dark:text-amber-200">
          {cs.build.development}
        </span>
      )}
      {prerelease && (
        <span className="rounded bg-slate-200 px-1.5 py-0.5 font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
          {cs.build.prerelease}
        </span>
      )}
    </footer>
  );
}
