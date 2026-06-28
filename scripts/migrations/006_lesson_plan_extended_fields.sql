ALTER TABLE lesson_plans ADD COLUMN IF NOT EXISTS classroom_id UUID;
ALTER TABLE lesson_plans ADD COLUMN IF NOT EXISTS rating INTEGER;
ALTER TABLE lesson_plans ADD COLUMN IF NOT EXISTS feedback TEXT;
ALTER TABLE lesson_plans ADD COLUMN IF NOT EXISTS used_in_class BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_lesson_plans_classroom_id ON lesson_plans(classroom_id);
