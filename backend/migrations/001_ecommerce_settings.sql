-- Migration: Add ecommerce settings support
-- This file creates tables to support storing ecommerce API credentials
-- in the database (optional, as they can also be loaded from environment variables)

-- Create settings table if it doesn't exist
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value TEXT,
    description TEXT,
    is_secret BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);

-- Insert ecommerce-related settings (initially empty/null)
INSERT INTO settings (key, description, is_secret) 
VALUES 
    ('yampi_token', 'Yampi API token', true),
    ('yampi_alias', 'Yampi store alias', false),
    ('appmax_api_key', 'Appmax API key', true)
ON CONFLICT (key) DO NOTHING;

-- Create ecommerce_integrations table to track which integrations are enabled
CREATE TABLE IF NOT EXISTS ecommerce_integrations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT FALSE,
    config JSONB,
    last_sync_at TIMESTAMP,
    sync_errors_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default integrations
INSERT INTO ecommerce_integrations (name, enabled) 
VALUES 
    ('yampi', false),
    ('appmax', false),
    ('shopify', false)
ON CONFLICT (name) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_ecommerce_integrations_name ON ecommerce_integrations(name);
