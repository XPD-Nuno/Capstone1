import { AlertTriangle, Flame, Loader2, Snowflake, Sun } from "lucide-react";
import type { ReactNode } from "react";
import { BAND_LABEL, STATUS_LABEL } from "../lib/format";
import type { Band, PacketStatus } from "../types";

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

const BAND_STYLE: Record<Band, string> = {
  HOT: "bg-rose-50 text-rose-700 ring-rose-600/20",
  WARM: "bg-amber-50 text-amber-800 ring-amber-600/25",
  COLD: "bg-sky-50 text-sky-700 ring-sky-600/20",
};

const BAND_ICON: Record<Band, typeof Flame> = { HOT: Flame, WARM: Sun, COLD: Snowflake };

export const BAND_ACCENT: Record<Band, string> = {
  HOT: "bg-rose-500",
  WARM: "bg-amber-400",
  COLD: "bg-sky-400",
};

export function BandBadge({ band, size = "sm" }: { band: Band; size?: "sm" | "lg" }) {
  const Icon = BAND_ICON[band];
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-full font-semibold ring-1 ring-inset",
        BAND_STYLE[band],
        size === "lg" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs",
      )}
    >
      <Icon className={size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5"} aria-hidden />
      {BAND_LABEL[band]}
    </span>
  );
}

const STATUS_STYLE: Record<PacketStatus, string> = {
  pending_review: "bg-violet-50 text-violet-700 ring-violet-600/20",
  approved: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  rejected: "bg-slate-100 text-slate-600 ring-slate-500/20",
  blocked_guardrail: "bg-red-50 text-red-700 ring-red-600/20",
};

export function StatusPill({ status }: { status: PacketStatus }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        STATUS_STYLE[status],
      )}
    >
      <span
        className={cx(
          "h-1.5 w-1.5 rounded-full",
          status === "pending_review" && "bg-violet-500",
          status === "approved" && "bg-emerald-500",
          status === "rejected" && "bg-slate-400",
          status === "blocked_guardrail" && "bg-red-500",
        )}
      />
      {STATUS_LABEL[status]}
    </span>
  );
}

export function ScoreBar({ score, band }: { score: number; band: Band }) {
  return (
    <div className="flex items-center gap-2" title={`Score ${score}/100`}>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
        <div className={cx("h-full rounded-full", BAND_ACCENT[band])} style={{ width: `${score}%` }} />
      </div>
      <span className="w-7 text-right text-xs font-semibold tabular-nums text-slate-700">{score}</span>
    </div>
  );
}

export function ScoreRing({ score, band }: { score: number; band: Band }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const stroke = band === "HOT" ? "#f43f5e" : band === "WARM" ? "#f59e0b" : "#38bdf8";
  return (
    <div className="relative h-20 w-20 shrink-0" role="img" aria-label={`Score ${score} out of 100`}>
      <svg viewBox="0 0 80 80" className="h-20 w-20 -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#f1f5f9" strokeWidth="8" />
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${(score / 100) * c} ${c}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-bold tabular-nums leading-none">{score}</span>
        <span className="text-[10px] font-medium uppercase tracking-wide text-slate-400">/ 100</span>
      </div>
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500" role="status">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-12 text-center" role="alert">
      <AlertTriangle className="h-8 w-8 text-red-500" aria-hidden />
      <p className="text-sm text-slate-700">{message}</p>
      {onRetry && (
        <button className="btn bg-slate-900 text-white hover:bg-slate-700" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function SectionCard({
  title,
  icon,
  action,
  children,
  className,
}: {
  title: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("card p-5 sm:p-6", className)}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
          {icon}
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}
