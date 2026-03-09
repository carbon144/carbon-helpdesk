-- Migration: Add auto-reply fields to tickets table
-- Date: 2026-03-09
-- Feature: Email Auto-Reply

ALTER TABLE tickets ADD COLUMN IF NOT EXISTS auto_replied BOOLEAN DEFAULT FALSE;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS auto_reply_at TIMESTAMPTZ;
