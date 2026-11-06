"use client";

import { ArrowRight, Megaphone } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { Notice } from "@/components/ui";
import { getNews, markNewsSeen, type News } from "@/lib/api";
import { useAuth, useRequireMe } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";

const t = cs.news;

export default function NewsPage() {
  const me = useRequireMe();
  const { state } = useAuth();
  const [news, setNews] = useState<News | null>(null);
  const [failed, setFailed] = useState(false);

  const profileId = me?.acting.id;
  const language = me?.acting.active_language;

  useEffect(() => {
    if (!profileId) return;
    let cancelled = false;
    getNews()
      .then((n) => {
        if (cancelled) return;
        setNews(n); // keeps the "Nové" marks for this visit
        if (n.unseen > 0) void markNewsSeen().catch(() => undefined);
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [profileId, language]);

  if (state.kind === "error") return <FullPageStatus text={cs.common.offline} />;
  if (!me) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
        <header className="flex flex-col gap-2">
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Megaphone className="size-6 text-brand-500" aria-hidden />
            {t.title}
          </h1>
          <p className="text-slate-600 dark:text-slate-300">{t.intro}</p>
        </header>
        {failed ? (
          <Notice tone="error">{cs.common.error}</Notice>
        ) : !news ? (
          <p className="text-sm text-slate-500">{cs.common.loading}</p>
        ) : news.entries.length === 0 ? (
          <Notice>{t.empty}</Notice>
        ) : (
          <ol className="flex flex-col gap-2">
            {news.entries.map((e) => {
              const body = (
                <>
                  <span className="flex flex-1 flex-col gap-0.5">
                    <span className="flex items-center gap-2 font-semibold">
                      {e.title}
                      {e.new && (
                        <span className="rounded-full bg-brand-500 px-2 py-0.5 text-xs font-medium text-white">{t.fresh}</span>
                      )}
                    </span>
                    <span className="text-sm text-slate-600 dark:text-slate-300">{e.blurb}</span>
                  </span>
                  {e.href && <ArrowRight className="size-5 shrink-0 text-slate-400" aria-hidden />}
                </>
              );
              const cls = `flex items-center gap-3 rounded-2xl border p-4 ${
                e.new ? "border-brand-500/40 bg-brand-500/5" : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
              }`;
              return (
                <li key={e.n}>
                  {e.href ? (
                    <Link href={e.href} className={`${cls} hover:border-brand-500`} aria-label={`${e.title}: ${t.open}`}>
                      {body}
                    </Link>
                  ) : (
                    <div className={cls}>{body}</div>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </AppShell>
  );
}
