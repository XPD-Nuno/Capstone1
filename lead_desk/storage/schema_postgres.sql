-- Lead Desk schema (Postgres). Same tables/columns as schema_sqlite.sql.
-- Not executed by the v1 demo; apply with psql when moving to SaaS.

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    user_id     TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    display_name TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'agent',
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
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
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at  TIMESTAMPTZ NOT NULL,
    latest_band   TEXT,
    latest_score  INTEGER,
    lead_json     JSONB NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_leads_tenant_dedup ON leads(tenant_id, dedup_key);

CREATE TABLE IF NOT EXISTS lead_events (
    event_id    BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    lead_id     TEXT NOT NULL REFERENCES leads(lead_id),
    event_type  TEXT NOT NULL,
    actor       TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_events_lead ON lead_events(lead_id, created_at);

CREATE TABLE IF NOT EXISTS packets (
    packet_id   TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    lead_id     TEXT NOT NULL REFERENCES leads(lead_id),
    status      TEXT NOT NULL,
    packet_json JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at  TIMESTAMPTZ,
    decided_by  TEXT
);
CREATE INDEX IF NOT EXISTS ix_packets_status ON packets(tenant_id, status);

CREATE TABLE IF NOT EXISTS rejected_listings (
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    lead_id     TEXT NOT NULL REFERENCES leads(lead_id),
    listing_id  TEXT NOT NULL,
    rejected_by TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, lead_id, listing_id)
);

CREATE TABLE IF NOT EXISTS usage_meters (
    tenant_id   TEXT NOT NULL REFERENCES tenants(tenant_id),
    period      TEXT NOT NULL,
    meter       TEXT NOT NULL,
    quantity    BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, period, meter)
);
