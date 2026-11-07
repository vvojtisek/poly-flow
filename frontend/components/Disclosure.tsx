"use client";

import { ChevronDown } from "lucide-react";
import { useState, type ReactNode } from "react";

/**
 * A collapsible section built on <details>/<summary>, so it is keyboard- and screen-reader-native.
 * `forceOpen` keeps it open (e.g. while a search filter is active) without losing the learner's own
 * choice, which is restored when the filter clears.
 */
export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  forceOpen = false,
  className = "",
  summaryClassName = "",
  id,
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  forceOpen?: boolean;
  className?: string;
  summaryClassName?: string;
  id?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const shown = open || forceOpen;
  return (
    <details
      id={id}
      open={shown}
      onToggle={(event) => {
        const next = (event.currentTarget as HTMLDetailsElement).open;
        if (!forceOpen && next !== open) setOpen(next);
      }}
      className={`disclosure group ${className}`}
    >
      <summary
        onClick={(event) => {
          // While forced open the toggle is meaningless; keep the DOM in sync with React.
          if (forceOpen) event.preventDefault();
        }}
        className={`flex cursor-pointer items-center gap-2 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${summaryClassName}`}
      >
        <span className="min-w-0 flex-1">{summary}</span>
        <ChevronDown
          className={`size-5 shrink-0 text-slate-400 transition-transform duration-200 group-open:rotate-180 ${forceOpen ? "opacity-0" : ""}`}
          aria-hidden
        />
      </summary>
      {children}
    </details>
  );
}
