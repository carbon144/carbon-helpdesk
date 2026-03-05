-- Add original_ticket_id to messages for merge tracking
ALTER TABLE messages ADD COLUMN IF NOT EXISTS original_ticket_id UUID;
