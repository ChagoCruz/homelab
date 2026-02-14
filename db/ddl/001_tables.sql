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