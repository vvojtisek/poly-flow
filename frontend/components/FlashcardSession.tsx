"use client";

import { ArrowLeft, Layers, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import { PlayButton } from "@/components/PlayButton";
import { SessionProgress } from "@/components/SessionProgress";
import { Button, Notice } from "@/components/ui";
import { getWordDeck, myWordAudioUrl, type Deck, type DeckCard, type DeckScope, type Language } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";
import { useHotkeys } from "@/lib/keyboard";

const t = cs.flashcards;
type Direction = "toCzech" | "fromCzech";

function Lemma({ card }: { card: DeckCard }) {
  return (
    <>
      {card.gender && card.gender.length > 1 ? `${card.gender} ` : ""}
      {card.lemma}
    </>
  );
}

/**
 * Flashcards from the learner's own words in one level or topic. Practice only: "again" puts the
 * card back at the end of this session's deck, "known" moves on; nothing is sent to the server, so
 * self-assessment never becomes graded evidence of passive or active knowledge.
 */
export function FlashcardSession({
  language,
  scope,
  onClose,
  closeLabel = t.close,
}: {
  language: Language;
  scope: DeckScope;
  onClose: () => void;
  closeLabel?: string;
}) {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [failed, setFailed] = useState(false);
  const [order, setOrder] = useState<number[]>([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [direction, setDirection] = useState<Direction>("toCzech");
  const [firstTry, setFirstTry] = useState(0);
  const [again, setAgain] = useState(0);
  const [missed, setMissed] = useState<Set<number>>(new Set());
  useHotkeys();

  useEffect(() => {
    const ctrl = new AbortController();
    getWordDeck(language, scope, ctrl.signal)
      .then((d) => {
        setDeck(d);
        setOrder(d.items.map((_, i) => i));
      })
      .catch((e) => e?.name !== "AbortError" && setFailed(true));
    return () => ctrl.abort();
  }, [language, scope]);

  function restart() {
    if (!deck) return;
    setOrder(deck.items.map((_, i) => i));
    setIndex(0);
    setFlipped(false);
    setFirstTry(0);
    setAgain(0);
    setMissed(new Set());
  }

  // Second round with only the cards marked "again" in this round.
  function restartMissed() {
    if (!missed.size) return;
    setOrder([...missed]);
    setIndex(0);
    setFlipped(false);
    setFirstTry(0);
    setAgain(0);
    setMissed(new Set());
  }

  function mark(known: boolean) {
    const cardIndex = order[index]!;
    if (known) {
      if (!missed.has(cardIndex)) setFirstTry((n) => n + 1);
    } else {
      setAgain((n) => n + 1);
      setMissed((m) => new Set(m).add(cardIndex));
      setOrder((o) => [...o, cardIndex]);
    }
    setFlipped(false);
    setIndex((i) => i + 1);
  }

  const header = (
    <header className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <Layers className="size-5 text-brand-500" aria-hidden /> {t.title(scope.label)}
      </h2>
      <Button variant="ghost" className="!px-2 !py-1 text-sm" onClick={onClose}>
        <ArrowLeft className="size-4" aria-hidden /> {closeLabel}
      </Button>
    </header>
  );

  const frame = (children: React.ReactNode) => (
    <section aria-label={t.title(scope.label)} className="mx-auto flex w-full max-w-xl flex-col gap-4">
      {header}
      {children}
    </section>
  );

  if (failed) return frame(<Notice tone="error">{cs.common.error}</Notice>);
  if (!deck) return frame(<p className="text-sm text-slate-500">{t.loading}</p>);
  if (deck.items.length === 0) return frame(<Notice>{t.empty}</Notice>);

  const card = deck.items[order[index] ?? -1];
  if (!card) {
    return frame(
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-brand-500/30 bg-brand-500/5 p-6 text-center">
        <SessionProgress current={order.length} done={order.length} total={order.length} label={cs.sessionProgress.card(order.length, order.length)} />
        <h3 className="text-lg font-bold">{t.doneTitle}</h3>
        <p className="text-sm text-slate-600 dark:text-slate-300">{t.doneSummary(firstTry, again)}</p>
        <div className="flex flex-wrap justify-center gap-2">
          {missed.size > 0 && (
            <Button onClick={restartMissed} autoFocus>
              <RotateCcw className="size-4" aria-hidden /> {t.restartMissed(missed.size)}
            </Button>
          )}
          <Button variant="secondary" onClick={restart}>
            <RotateCcw className="size-4" aria-hidden /> {t.restart}
          </Button>
          <Button variant={missed.size > 0 ? "secondary" : "primary"} onClick={onClose}>
            {closeLabel}
          </Button>
        </div>
      </div>,
    );
  }

  const target = (
    <span lang={language} className="text-3xl font-bold">
      <Lemma card={card} />
    </span>
  );
  const czech = (
    <span lang="cs" className="text-2xl font-semibold">
      {card.translation}
    </span>
  );
  const front = direction === "toCzech" ? target : czech;
  const back = direction === "toCzech" ? czech : target;
  const face = "absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-2xl border p-6 text-center backface-hidden";

  return frame(
    <>
      <SessionProgress current={index + 1} total={order.length} label={cs.sessionProgress.card(index + 1, order.length)} />
      {deck.total > deck.items.length && <p className="text-xs text-slate-500">{t.capped(deck.items.length, deck.total)}</p>}
      <div className="flex flex-wrap items-center gap-2 text-sm" role="group" aria-label={t.direction}>
        <span className="text-slate-500">{t.direction}:</span>
        {(["toCzech", "fromCzech"] as Direction[]).map((d) => (
          <button
            key={d}
            type="button"
            aria-pressed={direction === d}
            onClick={() => {
              setDirection(d);
              setFlipped(false);
            }}
            className={`rounded-full px-3 py-1 font-medium ${direction === d ? "bg-brand-500 text-white" : "bg-slate-100 dark:bg-slate-800"}`}
          >
            {t[d]}
          </button>
        ))}
      </div>

      <button
        type="button"
        data-hotkey={flipped ? undefined : "enter"}
        onClick={() => setFlipped((f) => !f)}
        aria-label={flipped ? undefined : t.flip}
        className="group relative h-64 w-full rounded-2xl outline-none perspective-[1200px] focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        <span
          className={`relative block size-full transition-transform duration-500 ease-out transform-3d motion-reduce:transition-none ${flipped ? "rotate-y-180" : ""}`}
        >
          <span className={`${face} border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900`} aria-hidden={flipped}>
            {card.due && (
              <span className="absolute top-3 right-3 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-950 dark:text-amber-200">
                {t.due}
              </span>
            )}
            {front}
            <span className="text-xs text-slate-400">{t.flipHint}</span>
          </span>
          <span
            className={`${face} rotate-y-180 border-brand-500/40 bg-brand-500/5 dark:bg-slate-900`}
            aria-hidden={!flipped}
            aria-live="polite"
          >
            {flipped && back}
            {flipped && card.example && (
              <span lang={language} className="text-sm italic text-slate-600 dark:text-slate-300">
                {card.example}
              </span>
            )}
          </span>
        </span>
      </button>

      <div className="flex min-h-12 flex-wrap items-center justify-between gap-2">
        <PlayButton url={myWordAudioUrl(card.id)} hotkey />
        {flipped ? (
          <div className="flex gap-2">
            <Button variant="secondary" data-hotkey="1" onClick={() => mark(false)}>
              {t.again}
            </Button>
            <Button data-hotkey="2" onClick={() => mark(true)} autoFocus>
              {t.known}
            </Button>
          </div>
        ) : (
          <span className="hidden text-xs text-slate-400 sm:inline">{t.keys}</span>
        )}
      </div>
      <p className="text-xs text-slate-500">{t.note}</p>
    </>,
  );
}
