-- Start with ACCOUNTADMIN role
USE ROLE ACCOUNTADMIN;

-- Create database and warehouse if needed
CREATE DATABASE IF NOT EXISTS ICE_BREAKER_DB;

-- Create roles if they don't exist
CREATE ROLE IF NOT EXISTS ICE_BREAKER_ROLE;

-- Idempotent role grants (these are idempotent by default)
GRANT ROLE ICE_BREAKER_ROLE TO ROLE SYSADMIN;
GRANT ALL PRIVILEGES ON DATABASE ICE_BREAKER_DB TO ROLE SYSADMIN WITH GRANT OPTION;

-- Switch to SYSADMIN for object management
USE ROLE SYSADMIN;
USE DATABASE ICE_BREAKER_DB;

-- Create or replace schema
CREATE SCHEMA IF NOT EXISTS NETWORKING;

-- Idempotent schema grants
GRANT USAGE ON DATABASE ICE_BREAKER_DB TO ROLE ICE_BREAKER_ROLE;
GRANT USAGE ON SCHEMA NETWORKING TO ROLE ICE_BREAKER_ROLE;
GRANT CREATE TABLE, CREATE VIEW ON SCHEMA NETWORKING TO ROLE ICE_BREAKER_ROLE;

-- Drop existing objects if they exist to ensure clean recreation
DROP VIEW IF EXISTS NETWORKING.VW_CONTACT_SUMMARY;
DROP STREAM IF EXISTS NETWORKING.CONTACTS_STREAM;
DROP TABLE IF EXISTS NETWORKING.INTEGRATION_STATUS;
DROP TABLE IF EXISTS NETWORKING.CONTACT_QUALITY;
DROP TABLE IF EXISTS NETWORKING.CONTACTS;
DROP TABLE IF EXISTS NETWORKING.NETWORKING_DEGREES;

-- Create networking degrees lookup table
CREATE OR REPLACE TABLE NETWORKING.NETWORKING_DEGREES (
    degree VARCHAR(50) PRIMARY KEY
);

-- Insert valid networking degrees
INSERT INTO NETWORKING.NETWORKING_DEGREES VALUES ('FirstDegree'), ('SecondDegree');

-- Create denormalized CONTACTS table
CREATE OR REPLACE TABLE NETWORKING.CONTACTS (
    contact_id NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    full_name VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    location VARCHAR(255),
    contact_email VARCHAR(255),
    linkedin_url VARCHAR(500) NOT NULL,
    mutual_connections VARCHAR(1000),
    networking_degree VARCHAR(50) DEFAULT 'SecondDegree',
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    
    CONSTRAINT pk_contacts PRIMARY KEY (contact_id),
    CONSTRAINT unique_linkedin_url UNIQUE (linkedin_url),
    CONSTRAINT fk_networking_degree FOREIGN KEY (networking_degree) REFERENCES NETWORKING.NETWORKING_DEGREES(degree)
);

-- Create a stream for change tracking with metadata
CREATE OR REPLACE STREAM NETWORKING.CONTACTS_STREAM ON TABLE NETWORKING.CONTACTS
    APPEND_ONLY = FALSE
    SHOW_INITIAL_ROWS = TRUE;

-- Create data quality table
CREATE OR REPLACE TABLE NETWORKING.CONTACT_QUALITY (
    contact_id NUMBER NOT NULL,
    confidence_score DECIMAL(5,2) NOT NULL,
    last_verified_date TIMESTAMP_TZ NOT NULL,
    data_source VARCHAR(100),
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    
    CONSTRAINT pk_contact_quality PRIMARY KEY (contact_id),
    CONSTRAINT fk_contact_quality_contact FOREIGN KEY (contact_id) REFERENCES NETWORKING.CONTACTS(contact_id)
);

-- Create integration status table
CREATE OR REPLACE TABLE NETWORKING.INTEGRATION_STATUS (
    contact_id NUMBER NOT NULL,
    external_source VARCHAR(100) NOT NULL,
    sync_status VARCHAR(50) NOT NULL,
    last_sync_timestamp TIMESTAMP_TZ,
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    
    CONSTRAINT pk_integration_status PRIMARY KEY (contact_id, external_source),
    CONSTRAINT fk_integration_status_contact FOREIGN KEY (contact_id) REFERENCES NETWORKING.CONTACTS(contact_id)
);

-- Comments for documentation (these are idempotent)
COMMENT ON TABLE NETWORKING.NETWORKING_DEGREES IS 'Valid networking connection degrees';
COMMENT ON TABLE NETWORKING.CONTACTS IS 'Denormalized contacts table containing LinkedIn profile information';
COMMENT ON TABLE NETWORKING.CONTACT_QUALITY IS 'Data quality metrics and verification status for contacts';
COMMENT ON TABLE NETWORKING.INTEGRATION_STATUS IS 'Integration status and synchronization metadata for external systems';

-- Column comments (these are idempotent)
COMMENT ON COLUMN NETWORKING.CONTACTS.contact_id IS 'Unique identifier for each contact';
COMMENT ON COLUMN NETWORKING.CONTACTS.networking_degree IS 'Connection degree (FirstDegree, SecondDegree)';
COMMENT ON COLUMN NETWORKING.CONTACTS.created_at IS 'Timestamp when the record was created';
COMMENT ON COLUMN NETWORKING.CONTACTS.updated_at IS 'Timestamp when the record was last updated';

-- Create view
CREATE OR REPLACE VIEW NETWORKING.VW_CONTACT_SUMMARY AS
SELECT 
    c.contact_id,
    c.full_name,
    c.title,
    c.location,
    c.networking_degree,
    c.mutual_connections,
    q.confidence_score,
    q.last_verified_date
FROM NETWORKING.CONTACTS c
LEFT JOIN NETWORKING.CONTACT_QUALITY q ON c.contact_id = q.contact_id;

-- Idempotent grants
GRANT SELECT, INSERT, UPDATE ON TABLE NETWORKING.NETWORKING_DEGREES TO ROLE ICE_BREAKER_ROLE;
GRANT SELECT, INSERT, UPDATE ON TABLE NETWORKING.CONTACTS TO ROLE ICE_BREAKER_ROLE;
GRANT SELECT, INSERT, UPDATE ON TABLE NETWORKING.CONTACT_QUALITY TO ROLE ICE_BREAKER_ROLE;
GRANT SELECT, INSERT, UPDATE ON TABLE NETWORKING.INTEGRATION_STATUS TO ROLE ICE_BREAKER_ROLE;
GRANT SELECT ON VIEW NETWORKING.VW_CONTACT_SUMMARY TO ROLE ICE_BREAKER_ROLE;

-- Future grants for new tables/views in schema
GRANT SELECT, INSERT, UPDATE ON FUTURE TABLES IN SCHEMA NETWORKING TO ROLE ICE_BREAKER_ROLE;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA NETWORKING TO ROLE ICE_BREAKER_ROLE;

-- Switch to ICE_BREAKER_ROLE for subsequent operations
USE ROLE ICE_BREAKER_ROLE; 