CREATE TABLE IF NOT EXISTS bills
(
    id SERIAL NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    amount numeric(10,2) NOT NULL,
    due_date date NOT NULL,
    paid boolean DEFAULT false,
    paid_date date,
    CONSTRAINT bills_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS car_mileage
(
    id SERIAL NOT NULL,
    log_date date NOT NULL,
    odometer integer NOT NULL,
    CONSTRAINT car_mileage_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS expenses
(
    id SERIAL NOT NULL,
    amount numeric(10,2) NOT NULL,
    description text COLLATE pg_catalog."default" NOT NULL,
    spent_date date NOT NULL,
    category text COLLATE pg_catalog."default",
    CONSTRAINT expenses_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS income
(
    id SERIAL NOT NULL,
    source text COLLATE pg_catalog."default" NOT NULL,
    amount numeric(10,2) NOT NULL,
    received_date date NOT NULL,
    notes text COLLATE pg_catalog."default",
    CONSTRAINT income_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS weight
(
    id SERIAL NOT NULL,
    entry_date date NOT NULL,
    weight numeric(5,2) NOT NULL,
    CONSTRAINT weight_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS blood_pressure
(
    id SERIAL NOT NULL,
    entry_date date NOT NULL DEFAULT CURRENT_DATE,
    systolic integer NOT NULL,
    diastolic integer NOT NULL
);

CREATE TABLE journal (
    id SERIAL PRIMARY KEY,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS safety_meeting_daily (
    entry_date DATE PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE diet (
    id SERIAL PRIMARY KEY,
    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
    meal TEXT NOT NULL,       -- e.g., "Breakfast", "Lunch", "Dinner", "Snack"
    food TEXT NOT NULL,       -- description of what you ate
    calories INTEGER NOT NULL, -- estimated calories for that food
	confidence TEXT NULL
);

CREATE TABLE workout (
	id SERIAL PRIMARY KEY,
	workout_date DATE NOT NULL DEFAULT CURRENT_DATE,
	workout TEXT NOT NULL,
	calories_burnt INTEGER NOT NULL
);

CREATE TABLE tarot_cards (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    arcana TEXT NOT NULL,
    short_meaning TEXT NOT NULL,
    full_summary TEXT NOT NULL
);

CREATE TABLE job_apps (
	id SERIAL PRIMARY KEY,
	position TEXT NOT NULL,
	company TEXT NOT NULL, 
	link TEXT NOT NUll,
	description TEXT NULL,
	applied_date DATE NOT NULL,
	rejection_yn TEXT NULL
);

CREATE TABLE recruiters (
    id SERIAL PRIMARY KEY,
    -- recruiter info
    name TEXT NOT NULL,
    company TEXT NULL,
    email TEXT NULL,
    linkedin_url TEXT NULL,
    -- outreach tracking
    connection_requested BOOLEAN DEFAULT FALSE,
    connection_accepted BOOLEAN DEFAULT FALSE,
    message_sent BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE,
    -- optional notes
	notes TEXT NULL, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS convo (
	id SERIAL PRIMARY KEY,
	convo_date DATE NOT NULL,
	location TEXT NOT NULL,
	performance TEXT NOT NULL,
	description TEXT NOT NULL
);

CREATE TABLE weather_daily (
    id BIGSERIAL PRIMARY KEY,
    weather_date DATE NOT NULL UNIQUE,
    weather_code INTEGER,
    weather_summary TEXT NOT NULL,
    temp_max_f NUMERIC(5,2),
    temp_min_f NUMERIC(5,2),
    sunrise TIMESTAMP,
    sunset TIMESTAMP,
    moon_phase_percent NUMERIC(5,2),
    moon_phase_name TEXT,
    raw_payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_weather_daily_weather_date
ON weather_daily (weather_date);

------------------------------------------------------------------------
-- AI SCHEMA 
------------------------------------------------------------------------
-- ai_insights.sql
------------------------------------------------------------------------
-- AI SCHEMA 
------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ai_insights (
  id BIGSERIAL PRIMARY KEY,
  insight_type TEXT NOT NULL CHECK (
    insight_type IN (
      'daily_summary',
      'daily_observation',
      'weekly_report',
      'pattern_detection',
      'forecast',
      'mental_health',
      'habit_insight',
      'journal_entry_analysis',
      'journal_weekly_summary',
      'journal_monthly_summary',
      'journal_yearly_summary'
    )
  ),
  insight_date DATE NOT NULL DEFAULT CURRENT_DATE,
  period_start DATE,
  period_end DATE,
  period_type TEXT CHECK (
    period_type IN ('daily', 'weekly', 'monthly', 'yearly')
  ),
  category TEXT NOT NULL DEFAULT 'general' CHECK (
    category IN (
      'general',
      'health',
      'weight',
      'blood_pressure',
      'calories',
      'journal',
      'alcohol',
      'diet'
    )
  ),
  source_table TEXT,
  source_id BIGINT,
  model_provider TEXT NOT NULL DEFAULT 'ollama',
  model_name TEXT NOT NULL DEFAULT 'gemma3:4b',
  prompt_version TEXT NOT NULL DEFAULT 'v1',
  input_payload JSONB,
  insight_text TEXT NOT NULL,
  structured_output JSONB,
  status TEXT NOT NULL DEFAULT 'complete'
    CHECK (status IN ('pending', 'complete', 'failed')),
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_insights_type
  ON ai_insights (insight_type);

CREATE INDEX IF NOT EXISTS idx_ai_insights_insight_date
  ON ai_insights (insight_date DESC);

CREATE INDEX IF NOT EXISTS idx_ai_insights_period
  ON ai_insights (period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_ai_insights_period_type
  ON ai_insights (period_type);

CREATE INDEX IF NOT EXISTS idx_ai_insights_category
  ON ai_insights (category);

CREATE INDEX IF NOT EXISTS idx_ai_insights_source
  ON ai_insights (source_table, source_id);

CREATE INDEX IF NOT EXISTS idx_ai_insights_input_payload_gin
  ON ai_insights USING GIN (input_payload);

CREATE INDEX IF NOT EXISTS idx_ai_insights_structured_output_gin
  ON ai_insights USING GIN (structured_output);

CREATE UNIQUE INDEX IF NOT EXISTS ux_ai_insights_journal_weekly_summary_period
  ON ai_insights (insight_type, category, period_start, period_end)
  WHERE insight_type = 'journal_weekly_summary' AND category = 'journal';

CREATE UNIQUE INDEX IF NOT EXISTS ux_ai_insights_journal_monthly_summary_period
  ON ai_insights (insight_type, category, period_start, period_end)
  WHERE insight_type = 'journal_monthly_summary' AND category = 'journal';

CREATE UNIQUE INDEX IF NOT EXISTS ux_ai_insights_journal_yearly_summary_period
  ON ai_insights (insight_type, category, period_start, period_end)
  WHERE insight_type = 'journal_yearly_summary' AND category = 'journal';

CREATE OR REPLACE FUNCTION set_ai_insights_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ai_insights_updated_at ON ai_insights;

CREATE TRIGGER trg_ai_insights_updated_at
BEFORE UPDATE ON ai_insights
FOR EACH ROW
EXECUTE FUNCTION set_ai_insights_updated_at();

CREATE TABLE IF NOT EXISTS journal_analysis (
    id BIGSERIAL PRIMARY KEY,
    journal_entry_id BIGINT NOT NULL UNIQUE,
    model_provider TEXT NOT NULL DEFAULT 'ollama',
    model_name TEXT NOT NULL DEFAULT 'gemma3:4b',
    mood_score NUMERIC(5,2),
    stress_score NUMERIC(5,2),
    energy_score NUMERIC(5,2),
    sentiment_label TEXT,
    themes JSONB,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS journal_entry_analysis (
    id BIGSERIAL PRIMARY KEY,
    journal_entry_id BIGINT NOT NULL UNIQUE REFERENCES journal(id) ON DELETE CASCADE,

    model_provider TEXT NOT NULL DEFAULT 'anthropic',
    model_name TEXT NOT NULL DEFAULT 'claude-haiku-4-5',
    prompt_version TEXT NOT NULL DEFAULT 'v2',

    mood_score NUMERIC(4,2),
    emotional_tone TEXT,

    key_emotions JSONB NOT NULL DEFAULT '[]'::jsonb,
    stressors JSONB NOT NULL DEFAULT '[]'::jsonb,
    positive_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    thinking_patterns JSONB NOT NULL DEFAULT '[]'::jsonb,
    life_direction_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    reflection_questions JSONB NOT NULL DEFAULT '[]'::jsonb,

    insight TEXT,
    encouragement TEXT,
    raw_output JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_journal_entry_analysis_journal_entry_id
    ON journal_entry_analysis (journal_entry_id);

CREATE INDEX IF NOT EXISTS idx_journal_entry_analysis_mood_score
    ON journal_entry_analysis (mood_score);

CREATE INDEX IF NOT EXISTS idx_journal_entry_analysis_key_emotions_gin
    ON journal_entry_analysis USING GIN (key_emotions);

CREATE INDEX IF NOT EXISTS idx_journal_entry_analysis_stressors_gin
    ON journal_entry_analysis USING GIN (stressors);

CREATE INDEX IF NOT EXISTS idx_journal_entry_analysis_positive_signals_gin
    ON journal_entry_analysis USING GIN (positive_signals);

CREATE INDEX IF NOT EXISTS idx_journal_entry_analysis_thinking_patterns_gin
    ON journal_entry_analysis USING GIN (thinking_patterns);

CREATE INDEX IF NOT EXISTS idx_journal_entry_analysis_life_direction_signals_gin
    ON journal_entry_analysis USING GIN (life_direction_signals);


CREATE TABLE IF NOT EXISTS journal_pattern_profile (
    id BIGSERIAL PRIMARY KEY,

    period_type TEXT NOT NULL CHECK (
        period_type IN ('weekly', 'monthly', 'yearly', 'rolling_10_entries', 'custom')
    ),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    entry_count INTEGER NOT NULL DEFAULT 0,

    model_provider TEXT NOT NULL DEFAULT 'anthropic',
    model_name TEXT NOT NULL DEFAULT 'claude-haiku-4-5',
    prompt_version TEXT NOT NULL DEFAULT 'v2',

    average_mood_score NUMERIC(4,2),

    dominant_emotions JSONB NOT NULL DEFAULT '[]'::jsonb,
    recurring_stressors JSONB NOT NULL DEFAULT '[]'::jsonb,
    recurring_positive_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    recurring_thinking_patterns JSONB NOT NULL DEFAULT '[]'::jsonb,
    recurring_life_direction_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    core_values JSONB NOT NULL DEFAULT '[]'::jsonb,
    motivation_drivers JSONB NOT NULL DEFAULT '[]'::jsonb,
    growth_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_signals JSONB NOT NULL DEFAULT '[]'::jsonb,

    pattern_summary TEXT,
    raw_output JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_journal_pattern_profile_period
    ON journal_pattern_profile (period_type, period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_journal_pattern_profile_dominant_emotions_gin
    ON journal_pattern_profile USING GIN (dominant_emotions);

CREATE INDEX IF NOT EXISTS idx_journal_pattern_profile_recurring_stressors_gin
    ON journal_pattern_profile USING GIN (recurring_stressors);

CREATE INDEX IF NOT EXISTS idx_journal_pattern_profile_recurring_positive_signals_gin
    ON journal_pattern_profile USING GIN (recurring_positive_signals);

CREATE INDEX IF NOT EXISTS idx_journal_pattern_profile_recurring_thinking_patterns_gin
    ON journal_pattern_profile USING GIN (recurring_thinking_patterns);

CREATE INDEX IF NOT EXISTS idx_journal_pattern_profile_recurring_life_direction_signals_gin
    ON journal_pattern_profile USING GIN (recurring_life_direction_signals);

CREATE INDEX IF NOT EXISTS idx_journal_pattern_profile_core_values_gin
    ON journal_pattern_profile USING GIN (core_values);

CREATE INDEX IF NOT EXISTS idx_journal_pattern_profile_motivation_drivers_gin
    ON journal_pattern_profile USING GIN (motivation_drivers);