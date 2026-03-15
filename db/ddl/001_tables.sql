CREATE TABLE IF NOT EXISTS bills
(
    id integer NOT NULL DEFAULT nextval('bills_id_seq'::regclass),
    name text COLLATE pg_catalog."default" NOT NULL,
    amount numeric(10,2) NOT NULL,
    due_date date NOT NULL,
    paid boolean DEFAULT false,
    paid_date date,
    CONSTRAINT bills_pkey PRIMARY KEY (id)
)

CREATE TABLE IF NOT EXISTS car_mileage
(
    id integer NOT NULL DEFAULT nextval('car_mileage_id_seq'::regclass),
    log_date date NOT NULL,
    odometer integer NOT NULL,
    CONSTRAINT car_mileage_pkey PRIMARY KEY (id)
)

CREATE TABLE IF NOT EXISTS expenses
(
    id integer NOT NULL DEFAULT nextval('expenses_id_seq'::regclass),
    amount numeric(10,2) NOT NULL,
    description text COLLATE pg_catalog."default" NOT NULL,
    spent_date date NOT NULL,
    category text COLLATE pg_catalog."default",
    CONSTRAINT expenses_pkey PRIMARY KEY (id)
)

CREATE TABLE IF NOT EXISTS income
(
    id integer NOT NULL DEFAULT nextval('income_id_seq'::regclass),
    source text COLLATE pg_catalog."default" NOT NULL,
    amount numeric(10,2) NOT NULL,
    received_date date NOT NULL,
    notes text COLLATE pg_catalog."default",
    CONSTRAINT income_pkey PRIMARY KEY (id)
)

CREATE TABLE IF NOT EXISTS weight
(
    id integer NOT NULL DEFAULT nextval('weight_id_seq'::regclass),
    entry_date date NOT NULL,
    weight numeric(5,2) NOT NULL,
    CONSTRAINT weight_pkey PRIMARY KEY (id)
)

CREATE TABLE IF NOT EXISTS blood_pressure
(
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entry_date date NOT NULL DEFAULT CURRENT_DATE,
    systolic integer NOT NULL,
    diastolic integer NOT NULL
)

CREATE TABLE journal (
    id SERIAL PRIMARY KEY,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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

------------------------------------------------------------------------
-- AI SCHEMA 
------------------------------------------------------------------------
-- ai_insights.sql
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
      'journal_weekly_summary'
    )
  ),
  insight_date DATE NOT NULL DEFAULT CURRENT_DATE,
  period_start DATE,
  period_end DATE,
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

CREATE INDEX IF NOT EXISTS idx_ai_insights_category
  ON ai_insights (category);

CREATE INDEX IF NOT EXISTS idx_ai_insights_source
  ON ai_insights (source_table, source_id);

CREATE INDEX IF NOT EXISTS idx_ai_insights_input_payload_gin
  ON ai_insights USING GIN (input_payload);

CREATE INDEX IF NOT EXISTS idx_ai_insights_structured_output_gin
  ON ai_insights USING GIN (structured_output);

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