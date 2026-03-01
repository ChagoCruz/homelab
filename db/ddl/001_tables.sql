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
    content TEXT NOT NULL
);

CREATE TABLE diet (
    id SERIAL PRIMARY KEY,
    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
    meal TEXT NOT NULL,       -- e.g., "Breakfast", "Lunch", "Dinner", "Snack"
    food TEXT NOT NULL,       -- description of what you ate
    calories INTEGER NOT NULL -- estimated calories for that food
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