-- Fix: unique index on customers.email blocks WhatsApp customers with NULL/empty email
-- Replace absolute unique with partial unique (only enforce uniqueness for non-empty emails)
DROP INDEX IF EXISTS ix_customers_email;
CREATE UNIQUE INDEX ix_customers_email ON customers (email) WHERE email IS NOT NULL AND email != '';
