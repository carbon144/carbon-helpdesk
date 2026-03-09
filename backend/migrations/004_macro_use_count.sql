-- Migration 004: Add use_count and created_by to macros
ALTER TABLE macros ADD COLUMN IF NOT EXISTS use_count INTEGER DEFAULT 0;
ALTER TABLE macros ADD COLUMN IF NOT EXISTS created_by VARCHAR(255);
