import { useId, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";

import { BuildInfo } from "@/components/BuildInfo";
import { cs } from "@/lib/i18n/cs";

const base =
  "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-base font-semibold transition disabled:cursor-not-allowed disabled:opacity-50";
const variants = {
  primary: "bg-brand-500 text-white hover:bg-brand-600",
  secondary:
    "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800",
  ghost: "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof variants }) {
  return <button type="button" className={`${base} ${variants[variant]} ${className}`} {...props} />;
}

export function Field({
  label,
  help,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; help?: string }) {
  const id = useId();
  // Help text is linked via aria-describedby so the accessible name stays just the label.
  return (
    <div className="flex flex-col gap-1 text-sm">
      <label htmlFor={id} className="font-medium text-slate-700 dark:text-slate-300">
        {label}
      </label>
      <input
        id={id}
        aria-describedby={help ? `${id}-help` : undefined}
        className="rounded-xl border border-slate-300 bg-white px-3 py-3 text-base text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
        {...props}
      />
      {help && (
        <span id={`${id}-help`} className="text-xs text-slate-500">
          {help}
        </span>
      )}
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "error" | "ok"; children: ReactNode }) {
  const tones = {
    info: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
    error: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-200",
    ok: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-200",
  };
  return (
    <p role={tone === "error" ? "alert" : "status"} className={`rounded-xl px-3 py-2 text-sm ${tones[tone]}`}>
      {children}
    </p>
  );
}

export function CenteredCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-full max-w-md flex-col justify-center gap-4 p-4">
      <h1 className="text-2xl font-bold text-brand-600">{title}</h1>
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        {children}
      </div>
      <BuildInfo className="justify-center text-center" />
    </main>
  );
}

/**
 * Placeholder blocks shown while a panel loads, sized like the content so the page does not jump.
 * Announced once as "loading" to screen readers; the shimmer respects reduced motion.
 */
export function Skeleton({ lines = 3, className = "" }: { lines?: number; className?: string }) {
  return (
    <div role="status" aria-live="polite" className={`flex flex-col gap-2 ${className}`}>
      <span className="sr-only">{cs.common.loading}</span>
      {Array.from({ length: lines }, (_, i) => (
        <span
          key={i}
          aria-hidden
          className="h-4 rounded-md bg-slate-200/80 motion-safe:animate-pulse dark:bg-slate-800"
          style={{ width: `${[92, 76, 84, 60, 70][i % 5]}%` }}
        />
      ))}
    </div>
  );
}
