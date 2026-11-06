"use client";

import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { LanguagePicker } from "@/components/AppShell";
import { RankEmblem } from "@/components/RankEmblem";
import { Button } from "@/components/ui";
import { markNewsSeen, updateOwnProfile, type Me, type ProfileSettings, type RankPath, type TextSize } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { PATH_NAMES, rankName } from "@/lib/ranks";

const t = cs.welcome;
const GOALS = [5, 10, 15, 20, 30];
const PATHS: RankPath[] = ["hockey", "royal", "off"];
const SIZES: TextSize[] = ["s", "m", "l", "xl"];
const STEPS = 5;

function choice(active: boolean) {
  return `rounded-xl px-3 py-3 font-semibold transition-colors ${
    active ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
  }`;
}

/** First-run welcome for a profile that has not learned anything yet. Every choice saves at once. */
export function Welcome({ me }: { me: Me }) {
  const { setMe } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(1);
  const s = me.acting.settings;

  const [failed, setFailed] = useState(false);

  async function save(patch: Partial<ProfileSettings>) {
    try {
      const acting = await updateOwnProfile({ settings: patch });
      setFailed(false);
      setMe({ ...me, acting, principal: me.principal.id === acting.id ? acting : me.principal });
    } catch {
      setFailed(true);
    }
  }

  async function finish(to?: string) {
    // A fresh profile starts with everything in "Co je nového" already counted as seen.
    await markNewsSeen().catch(() => undefined);
    await save({ onboarded: true });
    if (to) router.push(to);
  }

  return (
    <div className="fixed inset-0 z-40 grid place-items-center overflow-y-auto bg-slate-900/50 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="welcome-title">
      <section className="flex w-full max-w-lg flex-col gap-5 rounded-3xl bg-white p-6 shadow-2xl motion-safe:animate-pop-in dark:bg-slate-900">
        <header className="flex flex-col gap-1">
          <p className="flex items-center justify-between text-xs font-medium text-slate-500">
            <span>{t.step(step, STEPS)}</span>
            <button type="button" className="underline-offset-2 hover:underline" onClick={() => void finish()}>
              {t.skip}
            </button>
          </p>
          <div className="flex gap-1" aria-hidden>
            {Array.from({ length: STEPS }, (_, i) => (
              <span key={i} className={`h-1.5 flex-1 rounded-full ${i < step ? "bg-brand-500" : "bg-slate-200 dark:bg-slate-700"}`} />
            ))}
          </div>
        </header>
        {failed && (
          <p className="text-sm text-rose-600" role="alert">
            {cs.common.error}
          </p>
        )}

        {step === 1 && (
          <div className="flex flex-col gap-3">
            <h2 id="welcome-title" className="flex items-center gap-2 text-2xl font-bold">
              <Sparkles className="size-6 text-amber-500" aria-hidden /> {t.title(me.acting.display_name)}
            </h2>
            <p className="text-slate-600 dark:text-slate-300">{t.intro}</p>
            <h3 className="font-semibold">{t.language}</h3>
            <LanguagePicker me={me} />
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-col gap-3">
            <h2 id="welcome-title" className="text-xl font-bold">{t.goal}</h2>
            <div role="radiogroup" aria-label={t.goal} className="grid grid-cols-5 gap-2">
              {GOALS.map((g) => (
                <button key={g} type="button" role="radio" aria-checked={s.daily_goal_minutes === g} className={choice(s.daily_goal_minutes === g)} onClick={() => void save({ daily_goal_minutes: g })}>
                  {t.minutes(g)}
                </button>
              ))}
            </div>
            <p className="text-sm text-slate-500">{t.goalHelp}</p>
          </div>
        )}

        {step === 3 && (
          <div className="flex flex-col gap-3">
            <h2 id="welcome-title" className="text-xl font-bold">{t.path}</h2>
            <div role="radiogroup" aria-label={t.path} className="grid gap-2">
              {PATHS.map((p) => (
                <button
                  key={p}
                  type="button"
                  role="radio"
                  aria-checked={s.rank_path === p}
                  onClick={() => void save({ rank_path: p })}
                  className={`flex items-center gap-3 text-left ${choice(s.rank_path === p)}`}
                >
                  {p !== "off" ? (
                    <span className="flex -space-x-2">
                      <RankEmblem path={p} rank={1} tier="bronze" size="sm" />
                      <RankEmblem path={p} rank={5} tier="silver" size="sm" />
                      <RankEmblem path={p} rank={10} tier="diamond" size="sm" />
                    </span>
                  ) : (
                    <span className="size-8" aria-hidden />
                  )}
                  <span className="flex flex-col">
                    {PATH_NAMES[p]}
                    {p !== "off" && (
                      <span className="text-xs font-normal opacity-80">
                        {rankName(p, 1)} → {rankName(p, 10)}
                      </span>
                    )}
                  </span>
                </button>
              ))}
            </div>
            <p className="text-sm text-slate-500">{t.pathHelp}</p>
          </div>
        )}

        {step === 4 && (
          <div className="flex flex-col gap-3">
            <h2 id="welcome-title" className="text-xl font-bold">{t.comfort}</h2>
            <div role="radiogroup" aria-label={t.comfort} className="grid grid-cols-4 gap-2">
              {SIZES.map((size, i) => (
                <button key={size} type="button" role="radio" aria-checked={s.text_size === size} className={`flex flex-col items-center ${choice(s.text_size === size)}`} onClick={() => void save({ text_size: size })}>
                  <span style={{ fontSize: `${0.9 + i * 0.25}rem` }} aria-hidden>
                    Aa
                  </span>
                  <span className="text-xs font-normal">{cs.settings.textSizes[size]}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 5 && (
          <div className="flex flex-col gap-3">
            <h2 id="welcome-title" className="text-xl font-bold">{t.done}</h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">{t.doneHelp}</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <Button className="!py-4" onClick={() => void finish("/placement")}>
                {t.placement}
              </Button>
              <Button variant="secondary" className="!py-4" onClick={() => void finish("/lesson")}>
                {t.firstLesson}
              </Button>
            </div>
          </div>
        )}

        {step < STEPS && (
          <footer className="flex justify-between gap-2">
            <Button variant="ghost" disabled={step === 1} onClick={() => setStep(step - 1)}>
              {t.back}
            </Button>
            <Button autoFocus onClick={() => setStep(step + 1)}>
              {t.next}
            </Button>
          </footer>
        )}
      </section>
    </div>
  );
}
