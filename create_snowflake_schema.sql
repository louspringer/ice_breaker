CREATE TABLE Contact (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    fullName STRING,
    contactEmail STRING,
    linkedInURL STRING
);

CREATE TABLE NetworkingDegree (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    degreeName STRING
);

CREATE TABLE InteractionPoint (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    contactId INTEGER,
    interactionType STRING,
    lastInteractionDate TIMESTAMP,
    FOREIGN KEY (contactId) REFERENCES Contact(id)
);

CREATE TABLE ResearchInsight (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    contactId INTEGER,
    insightSource STRING,
    relevanceScore INTEGER,
    discoveryDate TIMESTAMP,
    FOREIGN KEY (contactId) REFERENCES Contact(id)
);

CREATE TABLE CommonGround (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    contactId INTEGER,
    description STRING,
    FOREIGN KEY (contactId) REFERENCES Contact(id)
);

CREATE TABLE ContactRequest (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    contactId INTEGER,
    requestDate TIMESTAMP,
    requestNote STRING,
    requestStatus STRING,
    FOREIGN KEY (contactId) REFERENCES Contact(id)
);

CREATE TABLE ConnectionRationale (
    id INTEGER AUTOINCREMENT PRIMARY KEY,
    contactRequestId INTEGER,
    rationale STRING,
    confidenceScore INTEGER,
    FOREIGN KEY (contactRequestId) REFERENCES ContactRequest(id)
); 