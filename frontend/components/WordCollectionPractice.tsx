"use client";

import { Brain, Headphones, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import { PlayButton, SlowToggle } from "@/components/PlayButton";
import { SessionProgress } from "@/components/SessionProgress";
import { Button, Notice } from "@/components/ui";
import { myWordAudioUrl, type WordCollectionDetail } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const t = cs.collections;

function shuffle<T,>(items: T[]): T[] {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j]!, result[i]!];
  }
  return result;
}

function RecallCards({ collection, onClose }: { collection: WordCollectionDetail; onClose: () => void }) {
  const [deck, setDeck] = useState(() => shuffle(collection.items.map((item) => item.id)));
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const currentId = deck[index];
  const current = collection.items.find((item) => item.id === currentId);

  function next() {
    setRevealed(false);
    setIndex((position) => position + 1);
  }

  if (!current) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-brand-500/30 bg-brand-500/5 p-6 text-center">
        <h3 className="text-lg font-bold">{t.finishRecall}</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">{t.practiceNote}</p>
        <div className="flex flex-wrap justify-center gap-2">
          <Button variant="secondary" onClick={() => { setDeck(shuffle(collection.items.map((item) => item.id))); setIndex(0); setRevealed(false); }}>
            <RotateCcw className="size-4" aria-hidden /> {t.repeatSentences}
          </Button>
          <Button onClick={onClose}>{cs.common.close}</Button>
        </div>
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-brand-500/30 bg-brand-500/5 p-4 sm:p-6">
      <header className="flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-lg font-bold"><Brain className="size-5 text-brand-500" aria-hidden /> {t.recallTitle}</h3>
      </header>
      <SessionProgress current={index + 1} total={deck.length} label={cs.sessionProgress.card(index + 1, deck.length)} />
      <div className="flex min-h-56 flex-col items-center justify-center gap-5 rounded-xl bg-white p-6 text-center dark:bg-slate-900">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t.recallPrompt}</p>
        <p lang="cs" className="text-2xl font-semibold">{current.translation}</p>
        {revealed ? (
          <div className="flex flex-col items-center gap-2" role="status">
            <p lang={collection.language} className="text-3xl font-bold">{current.gender && current.gender.length > 1 ? `${current.gender} ` : ""}{current.lemma}</p>
            <PlayButton url={myWordAudioUrl(current.id)} />
          </div>
        ) : (
          <Button variant="secondary" onClick={() => setRevealed(true)}>{t.revealRecall}</Button>
        )}
      </div>
      <footer className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-500">{t.practiceNote}</p>
        {revealed && <div className="flex gap-2">
          <Button variant="secondary" onClick={() => { setDeck((items) => [...items, current.id]); next(); }}>{t.recallAgain}</Button>
          <Button onClick={next}>{t.recallNext}</Button>
        </div>}
      </footer>
    </section>
  );
}

export function WordCollectionPractice({
  collection,
  onClose,
}: {
  collection: WordCollectionDetail;
  onClose: () => void;
}) {
  const examples = collection.items.filter((item) => item.example?.trim());
  const [mode, setMode] = useState<"sentences" | "recall">("sentences");
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [finished, setFinished] = useState(false);
  const current = examples[index] ?? examples[0] ?? null;

  useEffect(() => {
    setIndex(0);
    setRevealed(false);
    setFinished(false);
  }, [collection.id]);

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

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2" role="group" aria-label={t.practiceModes}>
        <Button variant="secondary" aria-pressed={mode === "sentences"} disabled={examples.length === 0} onClick={() => setMode("sentences")}>{t.sentenceTitle}</Button>
        <Button variant="secondary" aria-pressed={mode === "recall"} onClick={() => setMode("recall")}><Brain className="size-4" aria-hidden /> {t.recallTitle}</Button>
      </div>
      {mode === "recall" ? <RecallCards collection={collection} onClose={onClose} /> : examples.length === 0 ? <Notice>{t.noSentences}</Notice> : !current ? null : <section className="flex flex-col gap-4 rounded-2xl border border-brand-500/30 bg-brand-500/5 p-4 sm:p-6">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="flex items-center gap-2 text-lg font-bold">
            <Headphones className="size-5 text-brand-500" aria-hidden /> {t.sentenceTitle}
          </h3>
          <p className="text-sm text-slate-600 dark:text-slate-300">{t.sentencePrompt}</p>
        </div>
      </header>
      <SessionProgress current={index + 1} total={examples.length} />

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
      </section>}
    </div>
  );
}
