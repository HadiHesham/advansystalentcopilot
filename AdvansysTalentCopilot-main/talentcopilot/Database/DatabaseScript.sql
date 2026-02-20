CREATE TABLE Candidates (
    Id UUID PRIMARY KEY,
    FirstName VARCHAR(100) NOT NULL,
    LastName VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    PhoneNumber VARCHAR(20) NOT NULL UNIQUE,
    LinkedInURL VARCHAR(255) UNIQUE,
    GithubURL VARCHAR(255) UNIQUE,
    Address TEXT,
    Status VARCHAR(20) NOT NULL DEFAULT 'Processing'
        CHECK (Status IN ('Accepted', 'Rejected', 'Processing', 'Interview', 'Hiring manager'))
);

CREATE TABLE skills (
    Id UUID PRIMARY KEY,
    CandidateId UUID NOT NULL REFERENCES Candidates(Id) ON DELETE CASCADE,
    SkillName VARCHAR(100) NOT NULL
);


CREATE TABLE Projects (
    Id UUID PRIMARY KEY,
    CandidateId UUID NOT NULL REFERENCES Candidates(Id) ON DELETE CASCADE,
    ProjectName VARCHAR(255) NOT NULL,
    StartDate DATE,
    EndDate DATE,
    Title VARCHAR(100),
    Description TEXT
);

CREATE TABLE Experience (
    Id UUID PRIMARY KEY,
    CandidateId UUID REFERENCES Candidates(Id),
    CompanyName VARCHAR(255) NOT NULL,
    Title VARCHAR(100),
    Description TEXT,
    StartDate DATE NOT NULL,
    EndDate DATE
);

CREATE TABLE ExtraCurriculum (
    Id UUID PRIMARY KEY,
    CandidateId UUID REFERENCES Candidates(Id),
    Name VARCHAR(150) NOT NULL,
    Description TEXT,
    Location VARCHAR(150),
    Date DATE
);

CREATE TABLE Jobs (
    Id UUID PRIMARY KEY,
    CandidateId UUID REFERENCES Candidates(Id),
    Title VARCHAR(150) NOT NULL,
    Description TEXT,
    Department VARCHAR(100) NOT NULL,
    Team VARCHAR(100),
    Requirements TEXT,
    Type VARCHAR(50)
);
