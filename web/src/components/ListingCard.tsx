import { BedDouble, Check, Maximize2, MapPin, Zap } from "lucide-react";
import { AMENITY_LABEL, formatEur } from "../lib/format";
import type { ListingMatch } from "../types";
import { cx } from "./ui";

export function ListingCard({
  match,
  rank,
  selectable,
  selected,
  onToggle,
}: {
  match: ListingMatch;
  rank: number;
  selectable: boolean;
  selected: boolean;
  onToggle: () => void;
}) {
  const { listing } = match;
  const rent = listing.operation === "rent";
  const place = [listing.freguesia, listing.concelho].filter(Boolean).join(", ");
  return (
    <article
      className={cx(
        "relative flex flex-col overflow-hidden rounded-2xl border bg-white transition",
        selected ? "border-red-300 ring-2 ring-red-200" : "border-slate-200 hover:border-slate-300",
      )}
    >
      <div className="relative flex h-28 items-end bg-gradient-to-br from-brand-700 via-brand-600 to-emerald-500 p-4 text-white">
        <span className="absolute left-3 top-3 rounded-full bg-white/20 px-2 py-0.5 text-xs font-semibold backdrop-blur">
          #{rank} match
        </span>
        <span
          className={cx(
            "absolute right-3 top-3 rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
            listing.source === "idealista" ? "bg-lime-300 text-lime-950" : "bg-white/85 text-slate-700",
          )}
          title={listing.source === "mock" ? "Synthetic demo inventory" : "Live listing from Idealista"}
        >
          {listing.source}
        </span>
        <div>
          <p className="text-2xl font-bold tabular-nums leading-none">{formatEur(listing.price_eur, rent)}</p>
          <p className="mt-1 text-xs text-white/85">{rent ? "Rent" : "For sale"} · {listing.condition.replace("_", " ")}</p>
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3 className="font-semibold leading-snug text-slate-900">{listing.title}</h3>
          <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-500">
            <MapPin className="h-3.5 w-3.5" aria-hidden />
            {place}
          </p>
        </div>
        <dl className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-700">
          <div className="flex items-center gap-1">
            <dt className="sr-only">Typology</dt>
            <BedDouble className="h-4 w-4 text-slate-400" aria-hidden />
            <dd>{listing.typology}</dd>
          </div>
          <div className="flex items-center gap-1">
            <dt className="sr-only">Area</dt>
            <Maximize2 className="h-4 w-4 text-slate-400" aria-hidden />
            <dd>{listing.area_m2} m²</dd>
          </div>
          {listing.energy_class && (
            <div className="flex items-center gap-1">
              <dt className="sr-only">Energy class</dt>
              <Zap className="h-4 w-4 text-slate-400" aria-hidden />
              <dd>Class {listing.energy_class}</dd>
            </div>
          )}
        </dl>
        {listing.amenities.length > 0 && (
          <ul className="flex flex-wrap gap-1.5">
            {listing.amenities.map((a) => (
              <li key={a} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                {AMENITY_LABEL[a] ?? a}
              </li>
            ))}
          </ul>
        )}
        <ul className="space-y-1 border-t border-slate-100 pt-3 text-xs text-slate-600">
          {match.reasons.map((r) => (
            <li key={r} className="flex gap-1.5">
              <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" aria-hidden />
              {r}
            </li>
          ))}
        </ul>
        <div className="mt-auto flex items-center justify-between pt-1 text-xs text-slate-400">
          <span className="font-mono">{listing.listing_id}</span>
          {selectable && (
            <label className="flex cursor-pointer items-center gap-1.5 font-medium text-slate-600">
              <input
                type="checkbox"
                checked={selected}
                onChange={onToggle}
                className="h-4 w-4 rounded border-slate-300 accent-red-600"
              />
              Not a fit
            </label>
          )}
        </div>
      </div>
    </article>
  );
}
