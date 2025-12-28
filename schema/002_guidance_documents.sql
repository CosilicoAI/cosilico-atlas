-- Schema extension for IRS guidance documents (Revenue Procedures, Revenue Rulings, Notices)
-- Designed to work alongside the existing sections table for statute text

-- ============================================================================
-- GUIDANCE_DOCUMENTS: Store IRS guidance (Rev. Procs, Rev. Rulings, Notices)
-- ============================================================================

CREATE TABLE IF NOT EXISTS guidance_documents (
    id TEXT PRIMARY KEY,  -- e.g., "rp-2023-34", "rr-2023-12", "notice-2023-45"

    -- Document classification
    doc_type TEXT NOT NULL,  -- 'revenue_procedure', 'revenue_ruling', 'notice', 'announcement'
    doc_number TEXT NOT NULL,  -- e.g., "2023-34"

    -- Metadata
    title TEXT NOT NULL,
    irb_citation TEXT,  -- e.g., "2023-48 IRB"
    published_date TEXT,  -- ISO date

    -- Content
    full_text TEXT NOT NULL,
    sections_json TEXT,  -- JSON-serialized structured sections

    -- Applicability
    effective_date TEXT,  -- ISO date
    tax_years_json TEXT,  -- JSON array of years, e.g., "[2024, 2025]"
    subject_areas_json TEXT,  -- JSON array, e.g., '["EITC", "Income Tax"]'

    -- Extracted parameters (for parameter-heavy docs like EITC Rev. Procs)
    parameters_json TEXT,  -- JSON object mapping variable paths to values

    -- Source tracking
    source_url TEXT NOT NULL,
    pdf_url TEXT,
    retrieved_at TEXT NOT NULL  -- ISO date
);

-- Indexes for efficient queries
-- Note: doc_number is NOT unique - different document types can have the same number
-- (e.g., Notice 2024-10 and Rev. Rul. 2024-10 are different documents)
CREATE INDEX IF NOT EXISTS idx_guidance_doc_number
    ON guidance_documents(doc_number);

CREATE INDEX IF NOT EXISTS idx_guidance_doc_type
    ON guidance_documents(doc_type);

CREATE INDEX IF NOT EXISTS idx_guidance_published
    ON guidance_documents(published_date DESC);

CREATE INDEX IF NOT EXISTS idx_guidance_tax_years
    ON guidance_documents(tax_years_json);

-- ============================================================================
-- FULL-TEXT SEARCH for guidance documents
-- ============================================================================

CREATE VIRTUAL TABLE IF NOT EXISTS guidance_fts USING fts5(
    title,
    full_text,
    subject_areas,
    content='guidance_documents',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS guidance_ai AFTER INSERT ON guidance_documents BEGIN
    INSERT INTO guidance_fts(rowid, title, full_text, subject_areas)
    VALUES (new.rowid, new.title, new.full_text, new.subject_areas_json);
END;

CREATE TRIGGER IF NOT EXISTS guidance_ad AFTER DELETE ON guidance_documents BEGIN
    INSERT INTO guidance_fts(guidance_fts, rowid, title, full_text, subject_areas)
    VALUES ('delete', old.rowid, old.title, old.full_text, old.subject_areas_json);
END;

CREATE TRIGGER IF NOT EXISTS guidance_au AFTER UPDATE ON guidance_documents BEGIN
    INSERT INTO guidance_fts(guidance_fts, rowid, title, full_text, subject_areas)
    VALUES ('delete', old.rowid, old.title, old.full_text, old.subject_areas_json);
    INSERT INTO guidance_fts(rowid, title, full_text, subject_areas)
    VALUES (new.rowid, new.title, new.full_text, new.subject_areas_json);
END;

-- ============================================================================
-- GUIDANCE_STATUTE_REFS: Link guidance docs to statute sections
-- ============================================================================

CREATE TABLE IF NOT EXISTS guidance_statute_refs (
    guidance_id TEXT NOT NULL,  -- references guidance_documents(id)
    statute_title INTEGER NOT NULL,  -- e.g., 26 for IRC
    statute_section TEXT NOT NULL,  -- e.g., "32" for EITC
    ref_type TEXT NOT NULL,  -- 'implements', 'interprets', 'modifies', 'cites'
    excerpt TEXT,  -- Relevant quote from the guidance

    PRIMARY KEY (guidance_id, statute_title, statute_section, ref_type),
    FOREIGN KEY (guidance_id) REFERENCES guidance_documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_guidance_statute_refs_statute
    ON guidance_statute_refs(statute_title, statute_section);

CREATE INDEX IF NOT EXISTS idx_guidance_statute_refs_guidance
    ON guidance_statute_refs(guidance_id);
