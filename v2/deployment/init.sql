# SHACKLE Postgres Audit Log Initialization

-- Audit entries table
CREATE TABLE IF NOT EXISTS audit_entries (
    entry_id UUID PRIMARY KEY,
    timestamp_ns BIGINT NOT NULL,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    organization_id TEXT NOT NULL DEFAULT 'default',
    call_number BIGINT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_params_hash BYTEA,
    verdict TEXT NOT NULL,  -- ALLOW | DENY | HITL
    deny_reason TEXT,
    budget_before_usd DOUBLE PRECISION,
    budget_after_usd DOUBLE PRECISION,
    operator_id TEXT,
    signature BYTEA,
    previous_entry_hash BYTEA,
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (timestamp_ns);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_entries (session_id, timestamp_ns);
CREATE INDEX IF NOT EXISTS idx_audit_org ON audit_entries (organization_id, timestamp_ns);
CREATE INDEX IF NOT EXISTS idx_audit_verdict ON audit_entries (verdict, timestamp_ns);
CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_entries (agent_id, timestamp_ns);
CREATE INDEX IF NOT EXISTS idx_audit_tool ON audit_entries (tool_name, timestamp_ns);
CREATE INDEX IF NOT EXISTS idx_audit_deny ON audit_entries (deny_reason) WHERE verdict = 'DENY';

-- Default partitions (create more as needed)
CREATE TABLE IF NOT EXISTS audit_entries_2026_q3 PARTITION OF audit_entries
    FOR VALUES FROM (0) TO (1759276799000000000);  -- 2026-09-30
CREATE TABLE IF NOT EXISTS audit_entries_2026_q4 PARTITION OF audit_entries
    FOR VALUES FROM (1759276800000000000) TO (1767225599000000000);

-- License validation table
CREATE TABLE IF NOT EXISTS license_validations (
    id SERIAL PRIMARY KEY,
    license_key_hash TEXT NOT NULL,
    node_id TEXT NOT NULL,
    node_count INTEGER,
    valid BOOLEAN NOT NULL,
    tier TEXT,
    expires_at_ns BIGINT,
    validated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_license_validations ON license_validations (license_key_hash, validated_at);

-- Session state backup (for disaster recovery)
CREATE TABLE IF NOT EXISTS session_snapshots (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    organization_id TEXT NOT NULL DEFAULT 'default',
    state_json JSONB NOT NULL,
    snapshot_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_snapshots_org ON session_snapshots (organization_id);

-- Chain integrity verification view
CREATE OR REPLACE VIEW audit_chain_integrity AS
SELECT
    entry_id,
    timestamp_ns,
    previous_entry_hash,
    LAG(signature) OVER (PARTITION BY session_id ORDER BY timestamp_ns) AS expected_previous_hash,
    CASE
        WHEN previous_entry_hash IS NULL THEN 'CHAIN_START'
        WHEN previous_entry_hash = LAG(signature) OVER (PARTITION BY session_id ORDER BY timestamp_ns)
            THEN 'VALID'
        ELSE 'CHAIN_BROKEN'
    END AS chain_status
FROM audit_entries
ORDER BY session_id, timestamp_ns;
