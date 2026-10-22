-- The official image runs this only while initializing an empty data volume.
-- Read the generated secret without embedding it in SQL or command arguments.
\set ON_ERROR_STOP on
\set learner_password `cat /run/secrets/college_learner_password`

CREATE ROLE college_learner
    LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
    PASSWORD :'learner_password';
\unset learner_password

CREATE DATABASE college_learning OWNER college_learner;
ALTER DATABASE college_learning SET timezone TO 'UTC';
