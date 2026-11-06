"use client";

import { FolderPlus } from "lucide-react";
import { useEffect, useState } from "react";

import { Button, Notice } from "@/components/ui";
import {
  ApiError,
  addWordToCollection,
  createWordCollection,
  listWordCollections,
  type Language,
  type WordCollection,
} from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

const t = cs.collections;

export function WordCollectionControl({ itemId, language }: { itemId: string; language: Language }) {
  const [items, setItems] = useState<WordCollection[]>([]);
  const [selected, setSelected] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  async function refresh(preferred?: string) {
    const rows = await listWordCollections(language);
    setItems(rows);
    setSelected((current) =>
      preferred && rows.some((item) => item.id === preferred) ? preferred : current || rows[0]?.id || "",
    );
  }

  useEffect(() => {
    let active = true;
    listWordCollections(language)
      .then((rows) => {
        if (!active) return;
        setItems(rows);
        setSelected(rows[0]?.id ?? "");
      })
      .catch(() => active && setError(t.failed));
    return () => {
      active = false;
    };
  }, [language]);

  async function add(collectionId: string) {
    if (!collectionId) return;
    setBusy(true);
    setSaved(false);
    setError("");
    try {
      await addWordToCollection(collectionId, itemId);
      await refresh();
      setSaved(true);
    } catch {
      setError(t.failed);
    } finally {
      setBusy(false);
    }
  }

  async function createAndAdd(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError("");
    setSaved(false);
    let createdCollection = false;
    try {
      const created = await createWordCollection(language, name);
      createdCollection = true;
      setName("");
      setCreating(false);
      await refresh(created.id);
      await addWordToCollection(created.id, itemId);
      await refresh(created.id);
      setSelected(created.id);
      setSaved(true);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 409
          ? t.duplicate
          : createdCollection
            ? t.addFailed
            : t.failed,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-2 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <FolderPlus className="size-4 text-brand-500" aria-hidden /> {t.add}
      </h3>
      <p className="text-xs text-slate-500">{t.ownWordsOnly}</p>
      {items.length > 0 && (
        <div className="flex gap-2">
          <select
            aria-label={t.choose}
            value={selected}
            onChange={(event) => setSelected(event.target.value)}
            className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            {items.map((item) => (
              <option key={item.id} value={item.id}>{item.name} · {t.count(item.count)}</option>
            ))}
          </select>
          <Button variant="secondary" disabled={busy} onClick={() => void add(selected)}>{t.add}</Button>
        </div>
      )}
      {creating ? (
        <form className="flex gap-2" onSubmit={(event) => void createAndAdd(event)}>
          <input
            autoFocus
            maxLength={60}
            value={name}
            onChange={(event) => setName(event.target.value)}
            aria-label={t.name}
            placeholder={t.name}
            className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          />
          <Button disabled={busy || !name.trim()}>{t.createAction}</Button>
        </form>
      ) : (
        <Button variant="ghost" className="self-start !px-2 !py-1.5 text-sm" onClick={() => setCreating(true)}>
          <FolderPlus className="size-4" aria-hidden /> {t.create}
        </Button>
      )}
      {error && <Notice tone="error">{error}</Notice>}
      {saved && <p role="status" className="text-sm text-emerald-700 dark:text-emerald-300">{t.added}</p>}
    </section>
  );
}
