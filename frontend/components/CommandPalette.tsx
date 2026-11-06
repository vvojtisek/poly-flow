"use client";

import {
  Award,
  BarChart3,
  BookMarked,
  BookOpen,
  BookOpenText,
  ClipboardCheck,
  Compass,
  CornerDownLeft,
  Drama,
  Hash,
  AlarmClock,
  ArrowDownUp,
  Dumbbell,
  FlaskConical,
  Gauge,
  GraduationCap,
  Headphones,
  Home,
  Languages,
  LogOut,
  Monitor,
  Moon,
  Repeat,
  Search,
  Settings,
  Shapes,
  Sun,
  Trophy,
  Users,
  Waves,
  type LucideIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Kbd } from "@/components/Kbd";
import { LANGUAGES, logout, updateOwnProfile, type Me, type RankPath, type Theme } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cs } from "@/lib/i18n/cs";
import { isTypingTarget } from "@/lib/keyboard";
import { rank } from "@/lib/palette";
import { PATH_NAMES } from "@/lib/ranks";
import { applyTheme } from "@/lib/theme";
import { invalidateRanks } from "@/lib/useRanks";

interface Command {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
  keywords?: string[];
  run: () => void | Promise<void>;
}

const OPEN_EVENT = "pf-open-palette";
export const openPalette = () => window.dispatchEvent(new Event(OPEN_EVENT));

/** Ctrl+K / Cmd+K (or "/" outside text fields): jump anywhere and change settings by typing. */
export function CommandPalette({ me }: { me: Me }) {
  const router = useRouter();
  const { setMe } = useAuth();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const combo = (e.ctrlKey || e.metaKey) && !e.altKey && e.code === "KeyK";
      const slash = e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey && !isTypingTarget(e.target);
      if (combo || slash) {
        e.preventDefault();
        setOpen((o) => !o || !combo);
      }
    }
    const onOpen = () => setOpen(true);
    document.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_EVENT, onOpen);
    };
  }, []);

  useEffect(() => {
    const d = dialog.current;
    if (!d) return;
    if (open && !d.open) {
      setQuery("");
      setActive(0);
      d.showModal();
      input.current?.focus();
    } else if (!open && d.open) d.close();
  }, [open]);

  const commands = useMemo<Command[]>(() => {
    const go = (href: string) => () => router.push(href);
    const nav = cs.palette.groups.go;
    const list: Command[] = [
      { id: "home", label: cs.palette.home, group: nav, icon: Home, keywords: ["prehled", "dashboard", "domu"], run: go("/") },
      { id: "lesson", label: cs.lesson.start, group: nav, icon: BookOpen, keywords: ["lekce", "ucit"], run: go("/lesson") },
      { id: "check", label: cs.check.start, group: nav, icon: ClipboardCheck, keywords: ["overeni", "opakovani", "test"], run: go("/check") },
      { id: "grammar", label: cs.grammar.title, group: nav, icon: GraduationCap, keywords: ["gramatika", "pravidla"], run: go("/grammar") },
      { id: "stories", label: cs.stories.link, group: nav, icon: BookOpenText, keywords: ["cteni", "pribeh"], run: go("/stories") },
      { id: "placement", label: cs.placement.title, group: nav, icon: Compass, keywords: ["slovni zasoba"], run: go("/placement") },
      { id: "cefr", label: cs.cefr.title, group: nav, icon: Gauge, keywords: ["cefr", "uroven", "b2"], run: go("/placement/cefr") },
      { id: "levels", label: cs.tests.levels, group: nav, icon: Award, keywords: ["zkouska", "a1", "a2", "b1", "b2"], run: go("/levels") },
      { id: "cases", label: cs.cases.title, group: nav, icon: FlaskConical, keywords: ["pady", "clen", "koncovky", "der die das", "deklinace"], run: go("/grammar/cases") },
      { id: "shadowing", label: cs.shadow.title, group: nav, icon: Waves, keywords: ["stinovani", "vyslovnost", "mluvit", "nahrat", "shadowing"], run: go("/shadowing") },
      { id: "genders", label: cs.genders.title, group: nav, icon: Shapes, keywords: ["rod", "der die das", "clen", "le la", "il la", "trideni"], run: go("/genders") },
      { id: "practice", label: cs.practice.title, group: nav, icon: Dumbbell, keywords: ["procvicovat", "cviceni", "trenink"], run: go("/practice") },
      { id: "verbs", label: cs.verbs.title, group: nav, icon: Repeat, keywords: ["slovesa", "casovani", "konjugace", "verb"], run: go("/grammar/verbs") },
      { id: "numbers", label: cs.numbers.title, group: nav, icon: Hash, keywords: ["cisla", "cislovky", "zahlen", "nombres", "numeri", "numbers"], run: go("/numbers") },
      { id: "clock", label: cs.clock.title, group: nav, icon: AlarmClock, keywords: ["hodiny", "cas", "uhrzeit", "heure", "ora", "time"], run: go("/clock") },
      { id: "word-order", label: cs.wordOrder.title, group: nav, icon: ArrowDownUp, keywords: ["slovosled", "poradi", "veta", "word order"], run: go("/word-order") },
      { id: "roleplay", label: cs.roleplay.title, group: nav, icon: Drama, keywords: ["scenka", "dialog", "role", "konverzace", "rozhovor"], run: go("/roleplay") },
      { id: "dictation", label: cs.dictation.title, group: nav, icon: Headphones, keywords: ["diktat", "poslech", "psat"], run: go("/dictation") },
      { id: "words", label: cs.words.title, group: nav, icon: BookMarked, keywords: ["slovnik", "slova", "hledat"], run: go("/words") },
      { id: "insights", label: cs.insights.title, group: nav, icon: BarChart3, keywords: ["statistiky", "grafy", "aktivita", "predpoved"], run: go("/insights") },
      { id: "ranks", label: cs.palette.ranks, group: nav, icon: Trophy, keywords: ["hodnost", "odznaky", "cesta"], run: go("/ranks") },
      { id: "settings", label: cs.settings.title, group: nav, icon: Settings, keywords: ["nastaveni", "hlas", "rychlost"], run: go("/settings") },
    ];
    if (me.can_manage)
      list.push({ id: "profiles", label: cs.profiles.title, group: nav, icon: Users, keywords: ["profily", "deti"], run: go("/profiles") });
    for (const l of LANGUAGES) {
      if (l === me.acting.active_language) continue;
      list.push({
        id: `lang-${l}`,
        label: cs.palette.switchLanguage(cs.languages[l] ?? l),
        group: cs.palette.groups.language,
        icon: Languages,
        keywords: ["jazyk", l],
        run: async () => {
          const acting = await updateOwnProfile({ active_language: l });
          setMe({ ...me, acting, principal: me.principal.id === acting.id ? acting : me.principal });
        },
      });
    }
    const themes: [Theme, LucideIcon][] = [
      ["light", Sun],
      ["dark", Moon],
      ["system", Monitor],
    ];
    for (const [t, icon] of themes)
      list.push({
        id: `theme-${t}`,
        label: cs.palette.theme(cs.settings.themes[t] ?? t),
        group: cs.palette.groups.look,
        icon,
        keywords: ["motiv", "vzhled", "barvy"],
        run: async () => {
          applyTheme(t);
          await updateOwnProfile({ settings: { theme: t } });
        },
      });
    for (const p of ["hockey", "royal", "off"] as RankPath[])
      list.push({
        id: `path-${p}`,
        label: cs.palette.path(PATH_NAMES[p]),
        group: cs.palette.groups.look,
        icon: Trophy,
        keywords: ["hodnosti", "tema"],
        run: async () => {
          await updateOwnProfile({ settings: { rank_path: p } });
          invalidateRanks();
          router.refresh();
        },
      });
    if (me.acting.id === me.principal.id)
      list.push({
        id: "logout",
        label: cs.auth.logout,
        group: cs.palette.groups.account,
        icon: LogOut,
        keywords: ["odhlasit"],
        run: async () => {
          try {
            await logout();
          } finally {
            setMe(null);
            router.replace("/login");
          }
        },
      });
    return list;
  }, [me, router, setMe]);

  const results = useMemo(() => rank(query, commands, 12), [query, commands]);
  const current = Math.min(active, Math.max(results.length - 1, 0));

  async function run(c: Command | undefined) {
    if (!c) return;
    setOpen(false);
    await c.run();
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((current + 1) % Math.max(results.length, 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((current - 1 + results.length) % Math.max(results.length, 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      void run(results[current]);
    }
  }

  return (
    <dialog
      ref={dialog}
      onClose={() => setOpen(false)}
      onClick={(e) => e.target === dialog.current && setOpen(false)}
      aria-label={cs.palette.title}
      className="mx-auto mt-[12vh] w-[min(94vw,36rem)] rounded-2xl border border-slate-200 bg-white p-0 text-slate-900 shadow-2xl backdrop:bg-slate-950/40 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
    >
      <div className="flex items-center gap-2 border-b border-slate-200 px-4 dark:border-slate-800">
        <Search className="size-5 text-slate-400" aria-hidden />
        <input
          ref={input}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
          placeholder={cs.palette.placeholder}
          aria-label={cs.palette.placeholder}
          aria-controls="palette-results"
          aria-activedescendant={results[current] ? `palette-${results[current].id}` : undefined}
          role="combobox"
          aria-expanded="true"
          className="w-full bg-transparent py-4 text-base outline-none placeholder:text-slate-400"
        />
        <Kbd>Esc</Kbd>
      </div>
      <ul id="palette-results" role="listbox" className="max-h-[50vh] overflow-y-auto p-2">
        {results.length === 0 && <li className="p-3 text-sm text-slate-500">{cs.palette.empty}</li>}
        {results.map((c, i) => {
          const Icon = c.icon;
          return (
            <li
              key={c.id}
              id={`palette-${c.id}`}
              role="option"
              aria-selected={i === current}
              onMouseEnter={() => setActive(i)}
              onClick={() => void run(c)}
              className={`flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${
                i === current ? "bg-brand-500 text-white" : "text-slate-700 dark:text-slate-200"
              }`}
            >
              <Icon className="size-4 shrink-0" aria-hidden />
              <span className="flex-1">{c.label}</span>
              <span className={`text-xs ${i === current ? "text-white/80" : "text-slate-400"}`}>{c.group}</span>
              {i === current && <CornerDownLeft className="size-4" aria-hidden />}
            </li>
          );
        })}
      </ul>
      <p className="hidden gap-3 border-t border-slate-200 px-4 py-2 text-xs text-slate-500 dark:border-slate-800 lg:flex">
        <span>
          <Kbd>↑</Kbd> <Kbd>↓</Kbd> {cs.palette.move}
        </span>
        <span>
          <Kbd>Enter</Kbd> {cs.palette.run}
        </span>
        <span>
          <Kbd>Ctrl</Kbd>+<Kbd>K</Kbd> / <Kbd>/</Kbd> {cs.palette.open}
        </span>
      </p>
    </dialog>
  );
}
