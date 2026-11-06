"use client";

import { ArrowLeft, FolderOpen, Headphones, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell, FullPageStatus } from "@/components/AppShell";
import { Button, Notice } from "@/components/ui";
import { WordCollectionPractice } from "@/components/WordCollectionPractice";
import {
  createWordCollection,
  deleteWordCollection,
  getWordCollection,
  listWordCollections,
  removeWordFromCollection,
  type WordCollection,
  type WordCollectionDetail,
} from "@/lib/api";
import { useRequireMe } from "@/lib/auth";
import { genderClass } from "@/lib/gender";
import { cs } from "@/lib/i18n/cs";

const t = cs.collections;

export default function CollectionsPage() {
  const me = useRequireMe();
  const language = me?.acting.active_language;
  const [rows, setRows] = useState<WordCollection[]>([]);
  const [selected, setSelected] = useState("");
  const [detail, setDetail] = useState<WordCollectionDetail | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [practicing, setPracticing] = useState(false);

  const refresh = useCallback(async (preferred?: string) => {
    if (!language) return;
    const next = await listWordCollections(language);
    setRows(next);
    const id = preferred && next.some((item) => item.id === preferred)
      ? preferred
      : next.some((item) => item.id === selected)
        ? selected
        : next[0]?.id ?? "";
    setSelected(id);
    if (id) setDetail(await getWordCollection(id));
    else setDetail(null);
    setFailed(false);
  }, [language, selected]);

  useEffect(() => {
    let active = true;
    if (!language) return;
    listWordCollections(language)
      .then(async (next) => {
        if (!active) return;
        setRows(next);
        const id = next[0]?.id ?? "";
        setSelected(id);
        if (id) setDetail(await getWordCollection(id));
      })
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, [language, me?.acting.id]);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (!language || !name.trim()) return;
    setBusy(true);
    try {
      const created = await createWordCollection(language, name);
      setName("");
      await refresh(created.id);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  async function removeWord(id: string) {
    if (!selected) return;
    setBusy(true);
    try {
      await removeWordFromCollection(selected, id);
      await refresh(selected);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  async function removeCollection() {
    if (!selected) return;
    setBusy(true);
    try {
      await deleteWordCollection(selected);
      await refresh();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  if (!me) return <FullPageStatus text={cs.common.loading} />;
  return (
    <AppShell me={me}>
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <Link href="/words" className="mb-2 inline-flex items-center gap-1 text-sm text-brand-600 hover:underline dark:text-brand-50">
              <ArrowLeft className="size-4" aria-hidden /> {cs.words.title}
            </Link>
            <h1 className="flex items-center gap-2 text-2xl font-bold">
              <FolderOpen className="size-6 text-brand-500" aria-hidden /> {t.title}
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-300">{t.intro}</p>
          </div>
        </header>

        <form onSubmit={(event) => void create(event)} className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
          <label className="sr-only" htmlFor="collection-name">{t.name}</label>
          <input
            id="collection-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={60}
            placeholder={t.name}
            className="min-w-48 flex-1 rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
          />
          <Button disabled={busy || !name.trim()}><Plus className="size-4" aria-hidden /> {t.createAction}</Button>
        </form>

        {failed && <Notice tone="error">{t.failed}</Notice>}
        {rows.length === 0 ? (
          <Notice>{t.empty}</Notice>
        ) : (
          <div className="grid gap-4 lg:grid-cols-[15rem_1fr]">
            <nav aria-label={t.title} className="flex gap-2 overflow-x-auto lg:flex-col">
              {rows.map((collection) => (
                <button
                  key={collection.id}
                  type="button"
                  aria-pressed={selected === collection.id}
                  onClick={() => {
                    setSelected(collection.id);
                    setPracticing(false);
                    getWordCollection(collection.id).then(setDetail).catch(() => setFailed(true));
                  }}
                  className={`min-w-40 rounded-xl border p-3 text-left ${selected === collection.id ? "border-brand-500 bg-brand-500/10" : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"}`}
                >
                  <span className="block font-semibold">{collection.name}</span>
                  <span className="text-xs text-slate-500">{t.count(collection.count)}</span>
                </button>
              ))}
            </nav>

            <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              {detail && (
                <>
                  <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h2 className="text-lg font-bold">{detail.name}</h2>
                      <p className="text-sm text-slate-500">{t.count(detail.items.length)}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => setPracticing((value) => !value)}
                        aria-pressed={practicing}
                      >
                        <Headphones className="size-4" aria-hidden /> {t.sentencePractice}
                      </Button>
                      <Button variant="ghost" disabled={busy} onClick={() => void removeCollection()} className="text-rose-700 dark:text-rose-300">
                        <Trash2 className="size-4" aria-hidden /> {t.delete}
                      </Button>
                    </div>
                  </header>
                  {practicing ? (
                    <WordCollectionPractice collection={detail} onClose={() => setPracticing(false)} />
                  ) : detail.items.length === 0 ? (
                    <Notice>{t.emptyItems}</Notice>
                  ) : (
                    <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                      {detail.items.map((word) => (
                        <li key={word.id} className="flex items-center gap-3 py-3">
                          <span className="w-9 shrink-0 text-right text-xs text-slate-400">{word.rank}</span>
                          <span className="min-w-0 flex-1">
                            <span lang={detail.language} className={`block truncate font-semibold ${word.gender ? genderClass(word.gender) : ""}`}>
                              {word.gender && word.gender.length > 1 ? `${word.gender} ` : ""}{word.lemma}
                            </span>
                            <span className="block truncate text-sm text-slate-500">{word.translation}</span>
                          </span>
                          <Button variant="ghost" disabled={busy} onClick={() => void removeWord(word.id)} aria-label={`${t.remove}: ${word.lemma}`}>
                            <Trash2 className="size-4" aria-hidden /> <span className="hidden sm:inline">{t.remove}</span>
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </section>
          </div>
        )}
      </div>
    </AppShell>
  );
}
