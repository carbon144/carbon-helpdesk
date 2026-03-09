-- Migration 004: Add triage_rules table and user.last_activity_at
-- Run BEFORE deploying new backend code

-- 1. Add last_activity_at to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ;

-- 2. Create triage_rules table
CREATE TABLE IF NOT EXISTS triage_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    category VARCHAR(100),
    assign_to UUID REFERENCES users(id),
    set_priority VARCHAR(20),
    auto_reply BOOLEAN DEFAULT FALSE,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
