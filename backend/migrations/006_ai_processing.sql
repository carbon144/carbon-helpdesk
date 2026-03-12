-- Migration 006: Add ai_processing flag for ticket locking during AI reply generation
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_processing BOOLEAN DEFAULT FALSE;
