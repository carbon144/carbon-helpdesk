-- Migration 007: AI Agents table + ai_agent_id on tickets
-- Run BEFORE deploying new backend code

-- AI Agents table
CREATE TABLE IF NOT EXISTS ai_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    human_name VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,
    level INTEGER DEFAULT 1,
    categories VARCHAR[],
    tools_enabled VARCHAR[],
    system_prompt TEXT NOT NULL,
    few_shot_examples JSONB,
    escalation_keywords VARCHAR[],
    confidence_threshold FLOAT DEFAULT 0.7,
    auto_send BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    total_replies INTEGER DEFAULT 0,
    total_approved INTEGER DEFAULT 0,
    total_escalated INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add ai_agent_id to tickets
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_agent_id UUID REFERENCES ai_agents(id);

-- Add ai_draft_text to tickets (stores pending AI reply for review)
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_draft_text TEXT;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_draft_confidence FLOAT;
