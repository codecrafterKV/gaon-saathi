-- Gaon Saathi: PostgreSQL setup with restricted permissions.
-- Run as the postgres superuser:  psql -U postgres -f deploy/postgres-setup.sql
-- Replace the two CHANGE_ME passwords with long random values first.
--
-- Two roles:
--   gaon_owner : owns the schema, used ONLY to run migrations
--   gaon_app   : used by the running application; can read/write rows but
--                cannot create, alter or drop tables.

CREATE ROLE gaon_owner LOGIN PASSWORD 'CHANGE_ME_OWNER_PASSWORD';
CREATE ROLE gaon_app   LOGIN PASSWORD 'CHANGE_ME_APP_PASSWORD';

CREATE DATABASE gaon_saathi OWNER gaon_owner ENCODING 'UTF8' TEMPLATE template0;
REVOKE ALL ON DATABASE gaon_saathi FROM PUBLIC;
GRANT CONNECT ON DATABASE gaon_saathi TO gaon_app;

\connect gaon_saathi

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO gaon_app;

-- Tables created later by gaon_owner (migrations) are automatically usable by the app.
ALTER DEFAULT PRIVILEGES FOR ROLE gaon_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gaon_app;
ALTER DEFAULT PRIVILEGES FOR ROLE gaon_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO gaon_app;

-- Audit log is append-only for the application: it may add entries but
-- never change or delete them. (Run AFTER the first migration.)
-- REVOKE UPDATE, DELETE ON admin_audit_logs FROM gaon_app;
