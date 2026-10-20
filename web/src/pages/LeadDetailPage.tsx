import {
  AlertOctagon,
  ArrowLeft,
  Building,
  CheckCircle2,
  Clipboard,
  ClipboardCheck,
  History,
  Info,
  Lightbulb,
  MessageSquareQuote,
  RefreshCw,
  ShieldCheck,
  UserRound,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api } from "../api";
import { ListingCard } from "../components/ListingCard";
import { useToast } from "../components/toast";
import { BandBadge, ErrorState, ScoreRing, SectionCard, Spinner, StatusPill, cx } from "../components/ui";
import {
  AMENITY_LABEL,
  CHANNEL_LABEL,
  INTENT_LABEL,
  formatEur,
  formatTimeline,
  rationaleReasons,
  timeAgo,
} from "../lib/format";
import type { LeadDetail, LeadEvent } from "../types";

const AGENT_KEY = "leadDesk.agentId";

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="text-right text-sm font-medium text-slate-800">{children}</dd>
    </div>
  );
}

function YesNo({ value }: { value: boolean }) {
  return value ? (
    <span className="inline-flex items-center gap-1 text-emerald-700">
      <CheckCircle2 className="h-4 w-4" aria-hidden /> Yes
    </span>
  ) : (
    <span className="text-slate-400">No</span>
  );
}

function describeEvent(e: LeadEvent): string {
  const p = e.payload as Record<string, unknown>;
  switch (e.event_type) {
    case "ingested":
      return `Received via ${p.channel ?? "intake"}`;
    case "scored":
      return `Scored ${p.band} · ${p.score_0_100}/100 (${p.model_version})`;
    case "packet":
      return `Review packet created with ${(p.listing_ids as string[] | undefined)?.length ?? 0} match(es)`;
    case "notified":
      return `Placed on the ${p.channel} desk`;
    case "decision":
      return `${String(p.status).replace("_", " ")}${p.note ? ` — ${p.note}` : ""}`;
    case "listing_rejected":
      return `Excluded ${(p.listing_ids as string[]).join(", ")}`;
    default:
      return e.event_type;
  }
}

export function LeadDetailPage() {
  const { leadId = "" } = useParams();
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [error, setError] = useState<{ message: string; notFound: boolean } | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [agentId, setAgentId] = useState(() => localStorage.getItem(AGENT_KEY) || "agent_demo");
  const [busy, setBusy] = useState<"approve" | "reject" | "rematch" | null>(null);
  const [confirmReject, setConfirmReject] = useState(false);
  const [copied, setCopied] = useState(false);
  const toast = useToast();

  const load = useCallback(async () => {
    setError(null);
    try {
      setDetail(await api.lead(leadId));
    } catch (e) {
      setError({
        message: e instanceof Error ? e.message : "Could not load lead",
        notFound: e instanceof ApiError && e.status === 404,
      });
    }
  }, [leadId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    localStorage.setItem(AGENT_KEY, agentId);
  }, [agentId]);

  if (error) {
    return (
      <div className="space-y-4">
        <BackLink />
        <ErrorState message={error.notFound ? `Lead ${leadId} was not found.` : error.message} onRetry={error.notFound ? undefined : load} />
      </div>
    );
  }
  if (!detail) return <Spinner label="Loading lead…" />;

  const { packet } = detail;
  const { lead, score } = packet;
  const open = packet.status === "pending_review" || packet.status === "blocked_guardrail";
  const blocked = packet.status === "blocked_guardrail";
  const reasons = rationaleReasons(score.rationale);
  const signer = agentId.trim() || "agent_demo";

  const run = async (kind: "approve" | "reject" | "rematch") => {
    setBusy(kind);
    try {
      let next: LeadDetail;
      if (kind === "approve") {
        next = await api.approve(packet.packet_id, signer, note);
        toast("Approved. Copy the draft and send it yourself — nothing was sent to the customer.");
      } else if (kind === "reject") {
        next = await api.reject(packet.packet_id, signer, [], note);
        toast("Packet rejected. The lead stays on file; no listings will be presented.");
      } else {
        next = await api.reject(packet.packet_id, signer, selected, note);
        toast(`Excluded ${selected.length} listing${selected.length > 1 ? "s" : ""}. ${next.packet.matches.length} new match(es) found.`);
      }
      setDetail(next);
      setSelected([]);
      setNote("");
      setConfirmReject(false);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Action failed", "error");
    } finally {
      setBusy(null);
    }
  };

  const copyDraft = async () => {
    try {
      await navigator.clipboard.writeText(packet.draft_reply_for_agent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast("Could not copy — select the text and copy it manually.", "error");
    }
  };

  const toggle = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const actions = (
    <div className="flex flex-col gap-2">
      <button
        onClick={() => run("approve")}
        disabled={!open || blocked || busy !== null}
        className="btn w-full bg-emerald-600 text-white hover:bg-emerald-700"
      >
        <CheckCircle2 className="h-4 w-4" aria-hidden />
        {busy === "approve" ? "Approving…" : packet.matches.length ? "Approve & present listings" : "Approve"}
      </button>
      {selected.length > 0 && (
        <button
          onClick={() => run("rematch")}
          disabled={!open || busy !== null}
          className="btn w-full bg-amber-500 text-white hover:bg-amber-600"
        >
          <RefreshCw className={cx("h-4 w-4", busy === "rematch" && "animate-spin")} aria-hidden />
          Exclude {selected.length} & re-match
        </button>
      )}
      <button
        onClick={() => (confirmReject ? run("reject") : setConfirmReject(true))}
        onBlur={() => setConfirmReject(false)}
        disabled={!open || busy !== null}
        className={cx(
          "btn w-full",
          confirmReject ? "bg-red-600 text-white hover:bg-red-700" : "bg-white text-red-700 ring-1 ring-red-200 hover:bg-red-50",
        )}
      >
        <XCircle className="h-4 w-4" aria-hidden />
        {busy === "reject" ? "Rejecting…" : confirmReject ? "Confirm reject packet" : "Reject packet"}
      </button>
    </div>
  );

  return (
    <div className="space-y-6">
      <BackLink />

      <div className="card overflow-hidden">
        <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:p-6">
          <ScoreRing score={score.score_0_100} band={score.band} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight">{lead.lead_id}</h1>
              <BandBadge band={score.band} size="lg" />
              <StatusPill status={packet.status} />
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {INTENT_LABEL[score.intent]} · {lead.city ?? "City not stated"} · via {CHANNEL_LABEL[lead.channel]} (
              {lead.source.replace("_", " ")}) · received {timeAgo(lead.received_at)}
            </p>
            <div className="mt-3 flex items-start gap-2 rounded-xl bg-brand-50 px-3 py-2.5 text-sm text-brand-900">
              <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-brand-700" aria-hidden />
              <span>
                <span className="font-semibold">Next action: </span>
                {score.next_action}
              </span>
            </div>
          </div>
        </div>
        {blocked && (
          <div className="flex items-start gap-2 border-t border-red-200 bg-red-50 px-6 py-3 text-sm text-red-800" role="alert">
            <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            The guardrail blocked this packet ({packet.guardrail.hits.join(", ")}). It cannot be approved; review manually or reject.
          </div>
        )}
        {!open && (
          <div className="flex items-start gap-2 border-t border-slate-200 bg-slate-50 px-6 py-3 text-sm text-slate-700">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" aria-hidden />
            {packet.status === "approved" ? "Approved" : "Rejected"} by {detail.decided_by ?? "agent"} {timeAgo(detail.decided_at)}
            {packet.decision_note ? ` — “${packet.decision_note}”` : ""}.
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <SectionCard title="Why this band" icon={<ShieldCheck className="h-4 w-4" aria-hidden />}>
            <ul className="space-y-2">
              {reasons.map((r) => (
                <li key={r} className="flex gap-2 text-sm text-slate-700">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" aria-hidden />
                  {r}
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs text-slate-500">
              Operational signals only (intent, budget, timing, search activity, contactability). Nationality,
              neighbourhood and language ability are never used · {score.model_version}
            </p>
          </SectionCard>

          <SectionCard title="Customer message" icon={<MessageSquareQuote className="h-4 w-4" aria-hidden />}>
            <blockquote className="whitespace-pre-line border-l-4 border-slate-200 pl-4 text-slate-700">{lead.message}</blockquote>
            {packet.logistics_notes.length > 0 && (
              <ul className="mt-4 space-y-1.5">
                {packet.logistics_notes.map((n) => (
                  <li key={n} className="flex gap-2 rounded-lg bg-sky-50 px-3 py-2 text-sm text-sky-900">
                    <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                    {n}
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>

          <SectionCard
            title={`Property matches (${packet.matches.length})`}
            icon={<Building className="h-4 w-4" aria-hidden />}
            action={
              open && packet.matches.length > 0 ? (
                <span className="text-xs text-slate-500">Tick “Not a fit” to exclude and re-match</span>
              ) : undefined
            }
          >
            {packet.matches.length === 0 ? (
              <p className="rounded-xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                {score.band === "COLD"
                  ? "No matching for cold leads — qualify first."
                  : score.intent === "sell"
                    ? "Seller lead: book a valuation instead of matching listings."
                    : "No listings match the stated criteria right now."}
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {packet.matches.map((m, i) => (
                  <ListingCard
                    key={m.listing.listing_id}
                    match={m}
                    rank={i + 1}
                    selectable={open}
                    selected={selected.includes(m.listing.listing_id)}
                    onToggle={() => toggle(m.listing.listing_id)}
                  />
                ))}
              </div>
            )}
            {detail.rejected_listing_ids.length > 0 && (
              <p className="mt-4 text-xs text-slate-500">
                Excluded for this lead: <span className="font-mono">{detail.rejected_listing_ids.join(", ")}</span>
              </p>
            )}
          </SectionCard>

          <SectionCard
            title="Draft reply"
            icon={<UserRound className="h-4 w-4" aria-hidden />}
            action={
              <button onClick={copyDraft} className="btn px-3 py-1.5 text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50">
                {copied ? <ClipboardCheck className="h-4 w-4 text-emerald-600" aria-hidden /> : <Clipboard className="h-4 w-4" aria-hidden />}
                {copied ? "Copied" : "Copy"}
              </button>
            }
          >
            <pre className="whitespace-pre-wrap rounded-xl bg-slate-50 p-4 font-sans text-sm leading-relaxed text-slate-800">
              {packet.draft_reply_for_agent}
            </pre>
            <p className="mt-3 text-xs text-slate-500">
              Lead Desk never sends this. If you approve, copy it and send it from your own phone, email or CRM.
            </p>
          </SectionCard>
        </div>

        <aside className="space-y-6">
          <section className="card hidden p-5 lg:sticky lg:top-24 lg:z-10 lg:block">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Decision</h2>
            <DecisionFields agentId={agentId} setAgentId={setAgentId} note={note} setNote={setNote} disabled={!open} />
            <div className="mt-4">{actions}</div>
          </section>

          <SectionCard title="Lead facts">
            <dl className="divide-y divide-slate-100">
              <Fact label="Budget">{formatEur(lead.budget_eur, score.intent === "rent")}</Fact>
              <Fact label="Timeline">{formatTimeline(lead.timeline_days)}</Fact>
              <Fact label="Typology">{lead.preferences.typology ?? "—"}</Fact>
              {lead.preferences.min_area_m2 && <Fact label="Min. area">{lead.preferences.min_area_m2} m²</Fact>}
              {lead.preferences.amenities.length > 0 && (
                <Fact label="Wants">{lead.preferences.amenities.map((a) => AMENITY_LABEL[a] ?? a).join(", ")}</Fact>
              )}
              <Fact label="Listing views (7 d)">{lead.property_views_7d}</Fact>
              <Fact label="Saved listings">{lead.saved_listings}</Fact>
              <Fact label="Phone number"><YesNo value={lead.phone_provided} /></Fact>
              <Fact label="Email"><YesNo value={lead.email_provided} /></Fact>
              <Fact label="Replied before"><YesNo value={lead.replied_to_agent} /></Fact>
              {lead.portal_listing_ref && <Fact label="Portal ref">{lead.portal_listing_ref}</Fact>}
            </dl>
          </SectionCard>

          <SectionCard title="History" icon={<History className="h-4 w-4" aria-hidden />}>
            <ol className="relative space-y-4 border-l border-slate-200 pl-4">
              {[...detail.events].reverse().map((e, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-slate-300" aria-hidden />
                  <p className="text-sm text-slate-700">{describeEvent(e)}</p>
                  <p className="text-xs text-slate-400">
                    {e.actor} · {timeAgo(e.created_at)}
                  </p>
                </li>
              ))}
            </ol>
          </SectionCard>
        </aside>
      </div>

      {open && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 p-3 shadow-[0_-4px_16px_rgba(15,23,42,0.06)] backdrop-blur lg:hidden">
          <details className="mb-2">
            <summary className="cursor-pointer text-xs font-medium text-slate-500">Signed as {signer} · add a note</summary>
            <div className="mt-2">
              <DecisionFields agentId={agentId} setAgentId={setAgentId} note={note} setNote={setNote} disabled={!open} />
            </div>
          </details>
          {actions}
        </div>
      )}
    </div>
  );
}

function DecisionFields({
  agentId,
  setAgentId,
  note,
  setNote,
  disabled,
}: {
  agentId: string;
  setAgentId: (v: string) => void;
  note: string;
  setNote: (v: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="space-y-3">
      <label className="block">
        <span className="text-xs font-medium text-slate-600">Signed as</span>
        <input
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
          maxLength={64}
          className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-slate-600">Note (optional)</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          disabled={disabled}
          maxLength={500}
          rows={2}
          placeholder="e.g. Called, prefers viewings after 18h"
          className="mt-1 w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none disabled:bg-slate-50"
        />
      </label>
    </div>
  );
}

function BackLink() {
  return (
    <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900">
      <ArrowLeft className="h-4 w-4" aria-hidden /> Lead queue
    </Link>
  );
}
