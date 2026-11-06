"use client";

import { Dumbbell } from "lucide-react";
import Link from "next/link";

import { AppShell, FullPageStatus, LanguagePicker } from "@/components/AppShell";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { modesFor } from "@/lib/practice";

const t = cs.practice;
const TINT = [
  "from-sky-500/15 to-sky-500/0",
  "from-violet-500/15 to-violet-500/0",
  "from-emerald-500/15 to-emerald-500/0",
  "from-amber-500/15 to-amber-500/0",
  "from-rose-500/15 to-rose-500/0",
  "from-brand-500/15 to-brand-500/0",
];

export default function PracticePage() {
  const me = useRequireMe();
  const { state } = useAuth();
  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  const modes = modesFor(me.acting.active_language);
  return (
    <AppShell me={me}>
      <section className="flex flex-col gap-4">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Dumbbell className="size-6 text-brand-500" aria-hidden />
          {t.title}
        </h1>
        <p className="max-w-2xl text-slate-600 dark:text-slate-300">{t.intro}</p>
        <LanguagePicker me={me} />
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {modes.map((m, i) => {
            const copy = t.mode[m.id]!;
            return (
              <li key={m.id}>
                <Link
                  href={m.href}
                  className={`group flex h-full flex-col gap-3 rounded-3xl border border-slate-200 bg-gradient-to-br ${TINT[i % TINT.length]} p-5 transition-transform hover:-translate-y-0.5 hover:border-brand-500 motion-reduce:transition-none dark:border-slate-800`}
                >
                  <span className="flex items-center gap-3">
                    <span className="grid size-11 place-items-center rounded-2xl bg-white shadow-sm dark:bg-slate-900">
                      <m.icon className="size-6 text-brand-600 dark:text-brand-50" aria-hidden />
                    </span>
                    <span className="text-lg font-bold">{copy.title}</span>
                  </span>
                  <span className="text-sm text-slate-600 dark:text-slate-300">{copy.blurb}</span>
                  <span className="mt-auto flex flex-wrap gap-1">
                    {m.skills.map((s) => (
                      <span key={s} className="rounded-full bg-white/70 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-900/70 dark:text-slate-300">
                        {t.skill[s]}
                      </span>
                    ))}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </section>
    </AppShell>
  );
}
