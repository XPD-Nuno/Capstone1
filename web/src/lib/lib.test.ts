import { leadsQuery } from "../api";
import fixtures from "../test/fixtures.json";
import { DEFAULT_FILTERS, filtersFromParams, filtersToParams, isFiltered, toggleBand } from "./filters";
import { formatEur, formatTimeline, rationaleReasons } from "./format";

describe("rationaleReasons", () => {
  it("splits the engine rationale into reasons without the preamble or numeric score", () => {
    const reasons = rationaleReasons(fixtures.detail.packet.score.rationale);
    expect(reasons[0]).toBe("Clear buy intent in the message");
    expect(reasons).toContain("Timeline is within 90 days");
    expect(reasons.join(" ")).not.toMatch(/Numeric score|operational signals/);
  });
});

describe("format", () => {
  it("formats euros in pt-PT and marks rents per month", () => {
    expect(formatEur(null)).toBe("—");
    expect(formatEur(1200, true)).toMatch(/1200.*€\/mês|1\s?200.*€\/mês/);
  });

  it("humanises timelines", () => {
    expect(formatTimeline(null)).toBe("Not stated");
    expect(formatTimeline(60)).toBe("~9 weeks");
    expect(formatTimeline(400)).toBe("Over a year");
  });
});

describe("filters", () => {
  it("round-trips through URL params and drops unknown values", () => {
    const filters = { q: "lisboa", bands: ["HOT", "WARM"] as const, status: "pending_review", channel: "telegram", sort: "score" } as const;
    const back = filtersFromParams(filtersToParams({ ...filters, bands: [...filters.bands] }));
    expect(back).toEqual({ ...filters, bands: ["HOT", "WARM"] });
    expect(filtersFromParams(new URLSearchParams("band=PURPLE&status=nope&sort=x"))).toEqual(DEFAULT_FILTERS);
  });

  it("toggles bands in canonical order", () => {
    expect(toggleBand(["COLD"], "HOT")).toEqual(["HOT", "COLD"]);
    expect(toggleBand(["HOT", "COLD"], "HOT")).toEqual(["COLD"]);
  });

  it("knows when anything is filtered and builds the API query", () => {
    expect(isFiltered(DEFAULT_FILTERS)).toBe(false);
    expect(isFiltered({ ...DEFAULT_FILTERS, sort: "newest" })).toBe(false);
    expect(leadsQuery({ ...DEFAULT_FILTERS, q: "  T2 ", bands: ["HOT", "WARM"] })).toBe("q=T2&band=HOT&band=WARM&sort=priority");
  });
});
