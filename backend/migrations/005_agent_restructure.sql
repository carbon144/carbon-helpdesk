-- Migration 005: AI Agent Restructure — 7→13 agents by sector
-- Run BEFORE deploying new backend code

-- Add new columns to ai_agents
ALTER TABLE ai_agents ADD COLUMN IF NOT EXISTS sector VARCHAR(50);
ALTER TABLE ai_agents ADD COLUMN IF NOT EXISTS specialty VARCHAR(100);
ALTER TABLE ai_agents ADD COLUMN IF NOT EXISTS coordinator_id UUID REFERENCES ai_agents(id);
ALTER TABLE ai_agents ADD COLUMN IF NOT EXISTS slack_channel VARCHAR(100);

-- Add ai_agent_id to csat_ratings to track which agent handled
ALTER TABLE csat_ratings ADD COLUMN IF NOT EXISTS ai_agent_id UUID REFERENCES ai_agents(id);
-- Add resolved_by_ai flag to tickets
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS resolved_by_ai BOOLEAN DEFAULT FALSE;
-- Add human_pending fields to tickets for supervisor tracking
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS human_pending_action VARCHAR(255);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS human_pending_since TIMESTAMPTZ;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS human_pending_assigned VARCHAR(100);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS slack_cobro_count INTEGER DEFAULT 0;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS slack_last_cobro_at TIMESTAMPTZ;
-- Add interaction_count for escalation logic (3 interactions without resolution → escalate)
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ai_interaction_count INTEGER DEFAULT 0;

-- Index for supervisor queries
CREATE INDEX IF NOT EXISTS idx_tickets_human_pending ON tickets(human_pending_since) WHERE human_pending_action IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ai_agents_sector ON ai_agents(sector);
