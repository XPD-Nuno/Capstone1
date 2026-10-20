import { ChevronRight, Flame, Inbox, Mail, MessageCircle, Search, Snowflake, Sparkles, Sun, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useToast } from "../components/toast";
import { BAND_ACCENT, BandBadge, ErrorState, ScoreBar, Spinner, StatusPill, cx } from "../components/ui";
import { DEFAULT_FILTERS, filtersFromParams, filtersToParams, isFiltered, toggleBand } from "../lib/filters";
import { CHANNEL_LABEL, INTENT_LABEL, formatEur, formatTimeline, timeAgo } from "../lib/format";
import type { Band, LeadFilters, LeadSummary, Stats } from "../types";

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

const BAND_CARDS: { band: Band; icon: typeof Flame; hint: string; tone: string }[] = [
  { band: "HOT", icon: Flame, hint: "Call within the hour", tone: "text-rose-600 bg-rose-50" },
  { band: "WARM", icon: Sun, hint: "Qualify this week", tone: "text-amber-600 bg-amber-50" },
  { band: "COLD", icon: Snowflake, hint: "Park or reply by email", tone: "text-sky-600 bg-sky-50" },
];

function StatsRow({ stats, filters, onBand, onPending }: {
  stats: Stats | null;
  filters: LeadFilters;
  onBand: (band: Band) => void;
  onPending: () => void;
}) {
  const pendingActive = filters.status === "pending_review";
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <button
        onClick={onPending}
        aria-pressed={pendingActive}
        className={cx(
          "card flex items-center gap-3 p-4 text-left transition hover:border-violet-300",
          pendingActive && "border-violet-400 ring-2 ring-violet-200",
        )}
      >
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
          <Inbox className="h-5 w-5" aria-hidden />
        </span>
        <span>
          <span className="block text-2xl font-bold tabular-nums">{stats?.pending ?? "–"}</span>
          <span className="block text-xs font-medium text-slate-500">Need review</span>
        </span>
      </button>
      {BAND_CARDS.map(({ band, icon: Icon, hint, tone }) => {
        const active = filters.bands.includes(band);
        return (
          <button
            key={band}
            onClick={() => onBand(band)}
            aria-pressed={active}
            className={cx(
              "card flex items-center gap-3 p-4 text-left transition hover:border-slate-300",
              active && "border-slate-400 ring-2 ring-slate-200",
            )}
          >
            <span className={cx("flex h-10 w-10 items-center justify-center rounded-xl", tone)}>
              <Icon className="h-5 w-5" aria-hidden />
            </span>
            <span className="min-w-0">
              <span className="block text-2xl font-bold tabular-nums">{stats?.by_band[band] ?? "–"}</span>
              <span className="block truncate text-xs font-medium text-slate-500">
                {band.charAt(0) + band.slice(1).toLowerCase()} · {hint}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ChannelIcon({ channel }: { channel: LeadSummary["channel"] }) {
  const Icon = channel === "email" ? Mail : MessageCircle;
  return <Icon className="h-3.5 w-3.5 text-slate-400" aria-label={CHANNEL_LABEL[channel]} />;
}

function LeadRowMeta({ lead }: { lead: LeadSummary }) {
  return (
    <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
      <span className="inline-flex items-center gap-1">
        <ChannelIcon channel={lead.channel} />
        {lead.source.replace("_", " ")}
      </span>
      <span aria-hidden>·</span>
      <span>{timeAgo(lead.packet_created_at)}</span>
    </span>
  );
}

function LeadTable({ leads }: { leads: LeadSummary[] }) {
  const navigate = useNavigate();
  return (
    <div className="card hidden overflow-hidden md:block">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50/70 text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th className="py-3 pl-5 pr-3">Lead</th>
            <th className="px-3 py-3">Band</th>
            <th className="px-3 py-3">Intent · City</th>
            <th className="hidden px-3 py-3 lg:table-cell">Budget</th>
            <th className="hidden px-3 py-3 xl:table-cell">Timeline</th>
            <th className="px-3 py-3">Score</th>
            <th className="px-3 py-3">Matches</th>
            <th className="px-3 py-3">Status</th>
            <th className="w-8 py-3 pr-4" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {leads.map((lead) => (
            <tr
              key={lead.lead_id}
              onClick={() => navigate(`/leads/${lead.lead_id}`)}
              className="group cursor-pointer transition hover:bg-slate-50"
            >
              <td className="relative py-3.5 pl-5 pr-3">
                <span className={cx("absolute inset-y-2 left-0 w-1 rounded-r-full", BAND_ACCENT[lead.band])} aria-hidden />
                <Link
                  to={`/leads/${lead.lead_id}`}
                  className="block font-semibold text-slate-900 group-hover:text-brand-700"
                  onClick={(e) => e.stopPropagation()}
                >
                  {lead.lead_id}
                </Link>
                <LeadRowMeta lead={lead} />
              </td>
              <td className="px-3 py-3.5">
                <BandBadge band={lead.band} />
              </td>
              <td className="px-3 py-3.5">
                <span className="font-medium text-slate-800">{INTENT_LABEL[lead.intent]}</span>
                <span className="block text-xs text-slate-500">{lead.city ?? "City not stated"}</span>
              </td>
              <td className="hidden px-3 py-3.5 tabular-nums text-slate-700 lg:table-cell">
                {formatEur(lead.budget_eur, lead.intent === "rent")}
              </td>
              <td className="hidden px-3 py-3.5 text-slate-700 xl:table-cell">{formatTimeline(lead.timeline_days)}</td>
              <td className="px-3 py-3.5">
                <ScoreBar score={lead.score} band={lead.band} />
              </td>
              <td className="px-3 py-3.5 tabular-nums text-slate-700">{lead.match_count || "—"}</td>
              <td className="px-3 py-3.5">
                <StatusPill status={lead.status} />
              </td>
              <td className="py-3.5 pr-4 text-slate-300 group-hover:text-slate-500">
                <ChevronRight className="h-4 w-4" aria-hidden />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LeadCards({ leads }: { leads: LeadSummary[] }) {
  return (
    <ul className="space-y-3 md:hidden">
      {leads.map((lead) => (
        <li key={lead.lead_id}>
          <Link to={`/leads/${lead.lead_id}`} className="card relative block overflow-hidden p-4 active:bg-slate-50">
            <span className={cx("absolute inset-y-0 left-0 w-1", BAND_ACCENT[lead.band])} aria-hidden />
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-semibold">{lead.lead_id}</p>
                <LeadRowMeta lead={lead} />
              </div>
              <BandBadge band={lead.band} />
            </div>
            <p className="mt-2 line-clamp-2 text-sm text-slate-600">{lead.message_preview}</p>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs text-slate-600">
                {INTENT_LABEL[lead.intent]} · {lead.city ?? "—"} · {formatEur(lead.budget_eur, lead.intent === "rent")}
              </span>
              <div className="flex items-center gap-2">
                <ScoreBar score={lead.score} band={lead.band} />
                <StatusPill status={lead.status} />
              </div>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function QueuePage() {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => filtersFromParams(params), [params]);
  const [search, setSearch] = useState(filters.q);
  const debouncedSearch = useDebounced(search, 250);
  const [leads, setLeads] = useState<LeadSummary[] | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const toast = useToast();

  const update = useCallback(
    (patch: Partial<LeadFilters>) => setParams(filtersToParams({ ...filters, ...patch }), { replace: true }),
    [filters, setParams],
  );

  useEffect(() => {
    if (debouncedSearch !== filters.q) update({ q: debouncedSearch });
  }, [debouncedSearch]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [l, s] = await Promise.all([api.leads(filters), api.stats()]);
      setLeads(l);
      setStats(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load leads");
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const loadDemo = async () => {
    setLoadingDemo(true);
    try {
      const res = await api.loadDemo();
      toast(res.created.length ? `Loaded ${res.created.length} synthetic leads` : "Demo leads are already loaded");
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not load demo leads", "error");
    } finally {
      setLoadingDemo(false);
    }
  };

  const clear = () => {
    setSearch("");
    setParams(filtersToParams(DEFAULT_FILTERS), { replace: true });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Lead queue</h1>
          <p className="mt-1 text-sm text-slate-500">
            Highest priority first. Open a lead to see why it was banded, matching properties and the draft reply.
          </p>
        </div>
        {stats && (
          <p className="text-xs text-slate-500">
            Listings source: <span className="font-semibold text-slate-700">{stats.listings_provider}</span>
          </p>
        )}
      </div>

      <StatsRow
        stats={stats}
        filters={filters}
        onBand={(band) => update({ bands: toggleBand(filters.bands, band) })}
        onPending={() => update({ status: filters.status === "pending_review" ? "" : "pending_review" })}
      />

      <div className="card flex flex-col gap-3 p-3 sm:p-4 lg:flex-row lg:items-center">
        <label className="relative flex-1">
          <span className="sr-only">Search leads</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search lead id, city, message, typology, listing…"
            className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2.5 pl-9 pr-3 text-sm placeholder:text-slate-400 focus:border-brand-500 focus:bg-white focus:outline-none"
          />
        </label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:flex">
          <select
            aria-label="Status"
            value={filters.status}
            onChange={(e) => update({ status: e.target.value as LeadFilters["status"] })}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm"
          >
            <option value="">All statuses</option>
            <option value="pending_review">Needs review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="blocked_guardrail">Blocked</option>
          </select>
          <select
            aria-label="Channel"
            value={filters.channel}
            onChange={(e) => update({ channel: e.target.value as LeadFilters["channel"] })}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm"
          >
            <option value="">All channels</option>
            <option value="email">Email</option>
            <option value="telegram">Telegram</option>
          </select>
          <select
            aria-label="Sort"
            value={filters.sort}
            onChange={(e) => update({ sort: e.target.value as LeadFilters["sort"] })}
            className="col-span-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm sm:col-span-1"
          >
            <option value="priority">Priority</option>
            <option value="newest">Newest</option>
            <option value="score">Score</option>
          </select>
        </div>
        {isFiltered(filters) && (
          <button onClick={clear} className="btn px-3 text-slate-600 hover:bg-slate-100">
            <X className="h-4 w-4" aria-hidden /> Clear
          </button>
        )}
      </div>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : leads === null ? (
        <Spinner label="Loading leads…" />
      ) : leads.length === 0 ? (
        <div className="card flex flex-col items-center gap-3 px-6 py-14 text-center">
          <Inbox className="h-10 w-10 text-slate-300" aria-hidden />
          {stats && stats.total === 0 ? (
            <>
              <p className="font-semibold">No leads yet</p>
              <p className="max-w-md text-sm text-slate-500">
                New emails and Telegram messages appear here once they are scored. Load the synthetic demo set to try it.
              </p>
              <button
                onClick={loadDemo}
                disabled={loadingDemo}
                className="btn mt-2 bg-brand-700 text-white hover:bg-brand-800"
              >
                <Sparkles className="h-4 w-4" aria-hidden />
                {loadingDemo ? "Loading…" : "Load demo leads"}
              </button>
            </>
          ) : (
            <>
              <p className="font-semibold">No leads match these filters</p>
              <button onClick={clear} className="btn mt-1 bg-slate-100 text-slate-700 hover:bg-slate-200">
                Clear filters
              </button>
            </>
          )}
        </div>
      ) : (
        <>
          <p className="text-xs font-medium text-slate-500" aria-live="polite">
            {leads.length} lead{leads.length === 1 ? "" : "s"}
          </p>
          <LeadTable leads={leads} />
          <LeadCards leads={leads} />
        </>
      )}
    </div>
  );
}
