-- Wave 3 Fix #13: Unique partial index on gmail_message_id to prevent duplicate email imports
-- Only applies where gmail_message_id IS NOT NULL (most messages don't have one)

CREATE UNIQUE INDEX IF NOT EXISTS ix_messages_gmail_message_id_unique
ON messages (gmail_message_id)
WHERE gmail_message_id IS NOT NULL;
