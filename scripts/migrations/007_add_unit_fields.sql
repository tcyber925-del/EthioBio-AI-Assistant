ALTER TABLE lesson_plans
  ADD COLUMN IF NOT EXISTS unit_id UUID,
  ADD COLUMN IF NOT EXISTS day_index INTEGER,
  ADD COLUMN IF NOT EXISTS section_order INTEGER;

CREATE INDEX IF NOT EXISTS idx_lesson_plans_unit_id ON lesson_plans(unit_id);
