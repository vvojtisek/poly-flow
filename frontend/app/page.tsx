import { Activity, BookOpen, Flame, Map as MapIcon, Play, TrendingDown } from "lucide-react";

import { Panel } from "@/components/Panel";
import { ProgressionPath } from "@/components/ProgressionPath";
import { ServerStatus } from "@/components/ServerStatus";
import { cs } from "@/lib/i18n/cs";

// Phase-1 shell: mobile = single drill CTA column; lg+ = dense multi-panel dashboard.
export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-full max-w-7xl flex-col gap-4 p-4 lg:p-8">
      <header>
        <h1 className="text-2xl font-bold text-brand-600">{cs.appName}</h1>
        <p className="text-sm text-slate-500">{cs.tagline}</p>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title={cs.todayPractice} icon={BookOpen} className="lg:col-span-1">
          <button
            type="button"
            disabled
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-500 px-4 py-4 text-lg font-semibold text-white disabled:opacity-60"
          >
            <Play className="size-5" aria-hidden /> {cs.startDrill}
          </button>
          <p className="mt-2 text-center text-xs text-slate-500">{cs.comingSoon}</p>
        </Panel>

        <Panel title={cs.dashboard.vocabularyCoverage} icon={Activity} className="hidden lg:block">
          <p className="text-sm text-slate-500">{cs.comingSoon}</p>
        </Panel>

        <Panel title={cs.dashboard.serverHealth} icon={Activity}>
          <ServerStatus />
        </Panel>

        <Panel title={cs.dashboard.retention} icon={TrendingDown} className="hidden lg:col-span-2 lg:block">
          <p className="text-sm text-slate-500">{cs.comingSoon}</p>
        </Panel>

        <Panel title={cs.progression.title} icon={MapIcon} className="lg:col-span-1">
          <ProgressionPath />
        </Panel>

        <Panel title={cs.dashboard.streak} icon={Flame}>
          <p className="text-sm text-slate-500">{cs.comingSoon}</p>
        </Panel>
      </div>
    </main>
  );
}
