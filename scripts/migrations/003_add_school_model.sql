-- SI-001: Add School model, school_id to class_groups, SchoolHealthSnapshot

CREATE TABLE IF NOT EXISTS schools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE class_groups
    ADD COLUMN IF NOT EXISTS school_id UUID REFERENCES schools(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS school_health_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    snapshot_date TIMESTAMPTZ NOT NULL,
    avg_health DOUBLE PRECISION NOT NULL,
    total_students INTEGER NOT NULL,
    at_risk_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_class_groups_school_id ON class_groups(school_id);
CREATE INDEX IF NOT EXISTS idx_school_health_snapshots_school_date ON school_health_snapshots(school_id, snapshot_date);
