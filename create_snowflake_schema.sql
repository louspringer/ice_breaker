-- Create database and role
CREATE DATABASE IF NOT EXISTS ICE_BREAKER_DB;
USE DATABASE ICE_BREAKER_DB;

-- Create role with appropriate permissions
CREATE ROLE IF NOT EXISTS ICE_BREAKER_ROLE;
GRANT USAGE ON DATABASE ICE_BREAKER_DB TO ROLE ICE_BREAKER_ROLE;

-- Create schema
CREATE SCHEMA IF NOT EXISTS NETWORKING;
GRANT USAGE ON SCHEMA NETWORKING TO ROLE ICE_BREAKER_ROLE;

-- Create denormalized CONTACTS table
CREATE OR REPLACE TABLE NETWORKING.CONTACTS (
    contact_id NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    full_name VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    location VARCHAR(255),
    contact_email VARCHAR(255),
    linkedin_url VARCHAR(500) NOT NULL CONSTRAINT valid_linkedin_url CHECK (linkedin_url LIKE 'https://www.linkedin.com/%'),
    mutual_connections VARCHAR(1000),
    networking_degree VARCHAR(50) DEFAULT 'SecondDegree',
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    -- Constraints
    CONSTRAINT pk_contacts PRIMARY KEY (contact_id),
    CONSTRAINT unique_linkedin_url UNIQUE (linkedin_url)
);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON TABLE NETWORKING.CONTACTS TO ROLE ICE_BREAKER_ROLE;

-- Create a stream for change tracking
CREATE OR REPLACE STREAM NETWORKING.CONTACTS_STREAM ON TABLE NETWORKING.CONTACTS;

-- Comments for documentation
COMMENT ON TABLE NETWORKING.CONTACTS IS 'Denormalized contacts table containing LinkedIn profile information';
COMMENT ON COLUMN NETWORKING.CONTACTS.contact_id IS 'Unique identifier for each contact';
COMMENT ON COLUMN NETWORKING.CONTACTS.networking_degree IS 'Connection degree (FirstDegree, SecondDegree, etc.)';

-- Create a view for basic contact information
CREATE OR REPLACE VIEW NETWORKING.VW_CONTACT_SUMMARY AS
SELECT 
    contact_id,
    full_name,
    title,
    location,
    networking_degree,
    mutual_connections
FROM NETWORKING.CONTACTS;

-- Grant view access
GRANT SELECT ON VIEW NETWORKING.VW_CONTACT_SUMMARY TO ROLE ICE_BREAKER_ROLE; 