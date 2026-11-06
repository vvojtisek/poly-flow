"use client";

import { Headphones, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { Button, Notice } from "@/components/ui";
import { myWordAudioUrl, type WordCollectionDetail } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const t = cs.collections;

export function WordCollectionPractice({
  collection,
  onClose,
}: {
  collection: WordCollectionDetail;
  onClose: () => void;
}) {
  const examples = collection.items.filter((item) => item.example?.trim());
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [finished, setFinished] = useState(false);
  const current = examples[index];

  useEffect(() => {
    setIndex(0);
    setRevealed(false);
    setFinished(false);
  }, [collection.id]);

  if (examples.length === 0) return <Notice>{t.noSentences}</Notice>;

  function next() {
    setRevealed(false);
    if (index + 1 === examples.length) setFinished(true);
    else setIndex(index + 1);
  }

  if (finished) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-brand-500/30 bg-brand-500/5 p-6 text-center">
        <h3 className="text-lg font-bold">{t.finishSentences}</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">{t.practiceNote}</p>
        <div className="flex flex-wrap justify-center gap-2">
          <Button variant="secondary" onClick={() => { setIndex(0); setFinished(false); }}>
            <RotateCcw className="size-4" aria-hidden /> {t.repeatSentences}
          </Button>
          <Button onClick={onClose}>{cs.common.close}</Button>
        </div>
      </div>
    );
  }

  if (!current) return null;
  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-brand-500/30 bg-brand-500/5 p-4 sm:p-6">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="flex items-center gap-2 text-lg font-bold">
            <Headphones className="size-5 text-brand-500" aria-hidden /> {t.sentenceTitle}
          </h3>
          <p className="text-sm text-slate-600 dark:text-slate-300">{t.sentencePrompt}</p>
        </div>
        <span className="text-sm tabular-nums text-slate-500">{t.position(index + 1, examples.length)}</span>
      </header>

      <div className="flex flex-col gap-3 rounded-xl bg-white p-4 dark:bg-slate-900">
        <div className="flex items-center gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t.target}</p>
          <p className="font-semibold" lang={collection.language}>{current.lemma}</p>
          <PlayButton url={myWordAudioUrl(current.id, "example")} label={cs.audio.playSentence} />
          <SlowToggle />
        </div>
        <p className="text-xl leading-relaxed" lang={collection.language}>{current.example}</p>
        {revealed ? (
          <p role="status" className="rounded-lg bg-brand-500/10 p-3 text-lg font-semibold">
            {current.lemma} · {current.translation}
          </p>
        ) : (
          <Button variant="secondary" className="self-start" onClick={() => setRevealed(true)}>
            {t.revealMeaning}
          </Button>
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-500">{t.practiceNote}</p>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            disabled={index === 0}
            onClick={() => { setIndex(index - 1); setRevealed(false); }}
          >
            {t.previousSentence}
          </Button>
          <Button onClick={next}>{index + 1 === examples.length ? t.finishSentences : t.nextSentence}</Button>
        </div>
      </footer>
    </section>
  );
}
