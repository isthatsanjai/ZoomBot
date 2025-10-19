-- Drop existing tables to start fresh.
-- CASCADE will drop dependent objects (like foreign key constraints).
DROP TABLE IF EXISTS chat_logs;
DROP TABLE IF EXISTS commands;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS meetings;

-- Create the users table to store information about participants.
-- The ON CONFLICT clause in db_manager.py requires user_id to be a primary key.
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    user_name TEXT,
    user_email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create the meetings table to store unique meeting IDs.
-- The ON CONFLICT clause requires meeting_id to be a primary key.
CREATE TABLE meetings (
    meeting_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create the commands table for host-triggered actions.
-- The trigger_phrases column is a TEXT ARRAY to match the Python code.
CREATE TABLE commands (
    id SERIAL PRIMARY KEY,
    command_name VARCHAR(255) UNIQUE NOT NULL,
    trigger_phrases TEXT[] NOT NULL,
    broadcast_message TEXT NOT NULL,
    ack_message TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create the main table for logging all chat interactions.
-- It references the users and meetings tables via foreign keys for data integrity.
CREATE TABLE chat_logs (
    id SERIAL PRIMARY KEY,
    meeting_id VARCHAR(255) NOT NULL REFERENCES meetings(meeting_id),
    user_id VARCHAR(255) NOT NULL REFERENCES users(user_id),
    user_name TEXT,
    user_role VARCHAR(50),
    user_chat TEXT,
    chat_type VARCHAR(50),
    bot_classification VARCHAR(255),
    bot_response TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- (Optional but Recommended) Add some default commands directly into your schema.

INSERT INTO commands (command_name, trigger_phrases, broadcast_message, ack_message) VALUES
(
    'SEND_BREAKTHROUGH_SESSION_LINK',
    '{"send the breakthrough session message", "send breakthrough link", "post breakthrough", "drop the breakthrough link", "send everyone the breakthrough link", "breakthrough session please"}',
    'This is the link for your Breakthrough Session! 😊 You definitely want to be here tomorrow with us Full Body Fixers! 👇\n\nhttps://calendly.com/thefitnessdoctor/main-event-your-breakthrough-strategy-session-12?utm_source=session-4-7am',
    '✅ Got it! Sending the Breakthrough Session link to everyone now.'
),
(
    'SEND_REPLAY_LINK',
    '{"send the replay link", "post replays", "where are the replays", "send everyone the replay link", "drop the replay link", "can we get the replays", "post the link for the replays"}',
    'Hi everyone! For anyone who missed a session or wants to re-watch, all the replays and materials are available on our event page. Here is the link:\n\nhttps://www.thefitnessdoctor.com/fbf-event/the-full-body-fix-event',
    '✅ Okay, I''m sending the link for the replays to all participants.'
),
(
    'SEND_PRIVATE_CONSULT_LINK',
    '{"send private consult link", "post private consultation", "send everyone the consultation link", "drop the private consult link", "post the link for private consultations"}',
    'For those ready to take the next step with a personalized plan, you can book a 1-on-1 Private Consultation with our expert team here:\n\nhttps://sm.thefitnessdoctor.com/private-consult',
    '✅ You got it. The Private Consultation link is being sent out.'
),
(
    'REMIND_CAMERA_ON',
    '{"remind camera on", "ask for cameras", "send a reminder to turn on cameras", "remind everyone to turn on their camera", "post the camera reminder", "can you ask people to turn on cameras"}',
    'Just a friendly reminder to please turn on your cameras if you''re able to! 🎥 This is an interactive session and we''d love to see you to give you the best experience possible!',
    '✅ Done. I''ve sent a friendly reminder about turning on cameras.'
);

-- add indexes for faster queries on frequently searched columns.
CREATE INDEX idx_chat_logs_meeting_id ON chat_logs(meeting_id);
CREATE INDEX idx_chat_logs_user_id ON chat_logs(user_id);