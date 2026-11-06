"use client";

import { Megaphone } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui";
import { getNews, markNewsSeen, type News } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const t = cs.news;
const SHOWN = 3;

/** A quiet line on the dashboard when there is something new; gone once seen or dismissed. */
export function NewsBanner({ profileId, language }: { profileId: string; language: string }) {
  const [news, setNews] = useState<News | null>(null);

  useEffect(() => {
    let cancelled = false;
    getNews()
      .then((n) => !cancelled && setNews(n))
      .catch(() => undefined); // optional: without it the dashboard is complete
    return () => {
      cancelled = true;
    };
  }, [profileId, language]);

  if (!news || news.unseen === 0) return null;
  const fresh = news.entries.filter((e) => e.new);
  const rest = fresh.length - SHOWN;

  async function dismiss() {
    setNews((n) => (n ? { ...n, unseen: 0 } : n));
    try {
      await markNewsSeen();
    } catch {
      // Shown again next time; nothing is lost.
    }
  }

  return (
    <section
      className="flex flex-col gap-3 rounded-2xl border border-brand-500/30 bg-brand-500/5 p-4 sm:flex-row sm:items-center lg:col-span-3"
      aria-labelledby="news-banner"
    >
      <Megaphone className="hidden size-6 shrink-0 text-brand-500 sm:block" aria-hidden />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <p id="news-banner" className="font-semibold">
          {t.banner(news.unseen)}
        </p>
        <p className="truncate text-sm text-slate-600 dark:text-slate-300">
          {fresh
            .slice(0, SHOWN)
            .map((e) => e.title)
            .join(" · ")}
          {rest > 0 && ` ${t.more(rest)}`}
        </p>
      </div>
      <div className="flex shrink-0 gap-2">
        <Link
          href="/news"
          className="rounded-xl bg-brand-500 px-4 py-2 text-center font-medium text-white hover:bg-brand-600"
        >
          {t.show}
        </Link>
        <Button variant="secondary" onClick={() => void dismiss()}>
          {t.dismiss}
        </Button>
      </div>
    </section>
  );
}
