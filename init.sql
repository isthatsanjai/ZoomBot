-- init.sql

-- Table to store unique users who have interacted with the bot
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY, -- Zoom's user ID
    user_name VARCHAR(255) NOT NULL,
    user_email VARCHAR(255),
    first_seen_timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Table to store meeting information
CREATE TABLE IF NOT EXISTS meetings (
    meeting_id BIGINT PRIMARY KEY,
    password VARCHAR(255),
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration_minutes INT,
    meeting_type VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table to log every chat interaction
CREATE TABLE IF NOT EXISTS chat_logs (
    log_id SERIAL PRIMARY KEY, -- Auto-incrementing ID for each log entry
    meeting_id BIGINT REFERENCES meetings(meeting_id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    user_chat TEXT,
    user_role VARCHAR(50), --  'host', 'co-host', 'attendee'
    chat_type VARCHAR(50), -- 'DM', 'Everyone'
    bot_classification VARCHAR(100), -- 'Command' or 'RAG'
    bot_response TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Table for host-triggered commands, loaded from this DB instead of a file
CREATE TABLE IF NOT EXISTS commands (
    command_id SERIAL PRIMARY KEY,
    command_name VARCHAR(255) UNIQUE NOT NULL,
    trigger_phrases TEXT[] NOT NULL, -- An array of trigger phrases
    broadcast_message TEXT NOT NULL,
    ack_message TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

INSERT INTO commands (command_name, trigger_phrases, broadcast_message, ack_message) VALUES
('SEND_BREAKTHROUGH_SESSION_LINK', 
'{"send the breakthrough session message", "send breakthrough link", "post breakthrough", "drop the breakthrough link", "send everyone the breakthrough link", "breakthrough session please"}',
'This is the link for your Breakthrough Session! 😊
You definitely want to be here tomorrow with us Full Body Fixers! 👇

https://calendly.com/thefitnessdoctor/main-event-your-breakthrough-strategy-session-12?utm_source=session-4-7am',
'✅ Got it! Sending the Breakthrough Session link to everyone now.'
),
('SEND_REPLAY_LINK',
'{"send the replay link", "post replays", "where are the replays", "send everyone the replay link", "drop the replay link", "can we get the replays", "post the link for the replays"}',
'Hi everyone! For anyone who missed a session or wants to re-watch, all the replays and materials are available on our event page. Here is the link:

https://www.thefitnessdoctor.com/fbf-event/the-full-body-fix-event',
'✅ Okay, I''m sending the link for the replays to all participants.'
),
('SEND_PRIVATE_CONSULT_LINK',
'{"send private consult link", "post private consultation", "send everyone the consultation link", "drop the private consult link", "post the link for private consultations"}',
'For those ready to take the next step with a personalized plan, you can book a 1-on-1 Private Consultation with our expert team here:

https://sm.thefitnessdoctor.com/private-consult',
'✅ You got it. The Private Consultation link is being sent out.'
),
('REMIND_CAMERA_ON',
'{"remind camera on", "ask for cameras", "send a reminder to turn on cameras", "remind everyone to turn on their camera", "post the camera reminder", "can you ask people to turn on cameras"}',
'Just a friendly reminder to please turn on your cameras if you''re able to! 🎥 This is an interactive session and we''d love to see you to give you the best experience possible!',
'✅ Done. I''ve sent a friendly reminder about turning on cameras.'
)
ON CONFLICT (command_name) DO NOTHING;