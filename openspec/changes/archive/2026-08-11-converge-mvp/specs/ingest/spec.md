## ADDED Requirements

### Requirement: Pluggable loaders behind a Loader protocol
The system SHALL load input files through drivers implementing a `Loader` protocol
(`can_load` / `load`), so that new formats can be added without changing the pipeline. Ingest
SHALL select an applicable loader per file and SHALL NOT hard-code format handling in the
pipeline stages.

#### Scenario: Loader selected by file type
- **WHEN** the ingest stage encounters a file
- **THEN** it picks the first registered loader whose `can_load` returns true for that file

#### Scenario: Unsupported file is recorded, not fatal
- **WHEN** no registered loader can load a file
- **THEN** the file is skipped with an audit event stating it was unsupported
- **AND** the run continues with the remaining files

### Requirement: Email loading preserves headers
The `.eml`/`.msg` loader SHALL preserve the RFC 5322 headers required for thread reconstruction
(`Message-ID`, `In-Reply-To`, `References`) and the sender, recipients, subject, and date in the
document metadata.

#### Scenario: Threading headers retained
- **WHEN** an `.eml` file with `Message-ID` and `In-Reply-To` headers is ingested
- **THEN** those header values are present in the resulting document's metadata

#### Scenario: Attachments become linked documents
- **WHEN** an email carries an attachment
- **THEN** the attachment is ingested as its own document linked to the email by an
  `attachment-of` relation

### Requirement: Digital PDF text extraction
The PDF loader SHALL extract the embedded text layer of digital PDFs into `Document.text` and
SHALL tag documents whose text layer is absent or empty as `pdf_scanned` without attempting OCR
in this change.

#### Scenario: Digital PDF yields text
- **WHEN** a PDF with a text layer is ingested
- **THEN** its extracted text populates `Document.text` and `doc_type` is `pdf_digital`

#### Scenario: Scanned PDF flagged for later
- **WHEN** a PDF has no extractable text layer
- **THEN** the document is tagged `pdf_scanned` and an audit event records that OCR is out of
  scope for this change
