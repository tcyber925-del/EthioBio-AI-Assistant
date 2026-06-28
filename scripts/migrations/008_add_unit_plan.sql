CREATE TABLE IF NOT EXISTS unit_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID REFERENCES users(id),
    unit_title VARCHAR(300) NOT NULL,
    grade_level INTEGER NOT NULL,
    topic VARCHAR(300) NOT NULL,
    days INTEGER NOT NULL,
    duration_minutes INTEGER DEFAULT 40,
    language VARCHAR(10) DEFAULT 'en',
    model_used VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_unit_plans_teacher_id ON unit_plans(teacher_id);
CREATE INDEX IF NOT EXISTS idx_unit_plans_grade_level ON unit_plans(grade_level);
