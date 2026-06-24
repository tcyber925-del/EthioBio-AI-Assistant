ALTER TABLE misconception_patterns ADD COLUMN IF NOT EXISTS severity VARCHAR(30) NOT NULL DEFAULT 'misunderstanding';
ALTER TABLE misconception_patterns ADD COLUMN IF NOT EXISTS confidence FLOAT NOT NULL DEFAULT 0.0;

CREATE TABLE IF NOT EXISTS misconception_knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic VARCHAR(300) NOT NULL,
    misconception VARCHAR(500) NOT NULL,
    explanation TEXT NOT NULL,
    severity VARCHAR(30) NOT NULL DEFAULT 'misconception',
    related_objectives JSONB DEFAULT '[]'::jsonb,
    recommended_strategies JSONB DEFAULT '[]'::jsonb,
    detection_patterns JSONB DEFAULT '[]'::jsonb,
    grade_level INTEGER NOT NULL DEFAULT 10,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_misconception_kb_topic ON misconception_knowledge_base(topic);
