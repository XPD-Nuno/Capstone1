-- Lead Desk schema (SQLite). Mirrors schema_postgres.sql column-for-column.
-- Timestamps are ISO-8601 UTC text; JSON columns are TEXT (JSONB in Postgres).

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id     TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    display_name TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'agent',
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    lead_id       TEXT PRIMARY KEY,
    tenant_id     TEXT NOT NULL REFERENCES tenants(tenant_id),
    channel       TEXT NOT NULL,
    source        TEXT NOT NULL,
    dedup_key     TEXT,
    contact_handle TEXT,
    portal_listing_ref TEXT,
    city          TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL,
    latest_band   TEXT,
    latest_score  INTEGER,
    lead_json     TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_leads_tenant_dedup ON leads(tenant_id, dedup_key);

CREATE TABLE IF NOT EXISTS lead_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    lead_id     TEXT NOT NULL REFERENCES leads(lead_id),
    event_type  TEXT NOT NULL,   -- ingested | scored | packet | notified | decision | listing_rejected
    actor       TEXT NOT NULL,   -- system | agent:<user_id>
    payload_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_lead ON lead_events(lead_id, created_at);

CREATE TABLE IF NOT EXISTS packets (
    packet_id   TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    lead_id     TEXT NOT NULL REFERENCES leads(lead_id),
    status      TEXT NOT NULL,
    packet_json TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    decided_at  TEXT,
    decided_by  TEXT
);
CREATE INDEX IF NOT EXISTS ix_packets_status ON packets(tenant_id, status);

CREATE TABLE IF NOT EXISTS rejected_listings (
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    lead_id     TEXT NOT NULL REFERENCES leads(lead_id),
    listing_id  TEXT NOT NULL,
    rejected_by TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (tenant_id, lead_id, listing_id)
);

CREATE TABLE IF NOT EXISTS usage_meters (
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    period      TEXT NOT NULL,   -- YYYY-MM
    meter       TEXT NOT NULL,   -- scores | llm_tokens | listing_fetches | notifications
    quantity    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, period, meter)
);

-- One row per erased lead. Holds no lead content: only a SHA-256 of the lead id, so a later
-- request about the same id can be answered ("erased on ...") without keeping the data.
CREATE TABLE IF NOT EXISTS erasure_log (
    erasure_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    lead_id_sha256 TEXT NOT NULL,
    reason      TEXT NOT NULL,   -- request | retention
    actor       TEXT NOT NULL,   -- agent:<user_id> | system:retention
    counts_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
