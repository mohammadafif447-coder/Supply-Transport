-- Supabase Realtime's postgres_changes evaluates RLS policies against the
-- full row image for UPDATE/DELETE events. With the default REPLICA IDENTITY
-- (primary key only), Postgres only writes the PK into the WAL's "old" row
-- image, so Realtime cannot evaluate policies like
-- "company reads own orders" (which needs orders.company_id) and silently
-- drops the change instead of broadcasting it. REPLICA IDENTITY FULL makes
-- Postgres write the complete old row into the WAL, fixing this.
alter table orders replica identity full;
alter table order_tracking_events replica identity full;
