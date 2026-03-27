# Architecture

## Components

- Pipeline Orchestrator, using Prefect
  - Define a Workflow for Extraction
    - Get documents not processed yet, check against document processing status
    - ...
  - Define a Workflow for Chunking and Embedding, then Upsert to Vector Store
  - Define a Workflow to search on ArXiv and download PDF documents (`flows/arxiv_search.py`)
- Postgres Database
  - Store document extraction status
  - Store documents chunks
  - Store documents vectors
- Local Folder
  - Raw data for documents
  - Extracted documents in markdown format

## Data flow

Arxiv ingestion → local folder → extraction → chunking/embedding → RAG

0. Arxiv ingestion flow searches arxiv, downloads PDFs into `data/pdfs/<YYMM>/`, tracks in Postgres
1. PDF documents go through extraction workflow to write to local folder as markdown files
   - Images?
   - Formulas?
2. Markdown files go through workflow to chunk and embed
   - Export chunks in PG table
   - Export embedding vectors in PG Table
3. RAG


## Database schema

Tables

- Documents Processing Status
  - Document Id 
  - Extracted At
  - Source file
  - Output file
  - Output Images? 
- Documents metadata (source URL)
  - Document Id
  - Title
  - Authors (array)
  - Institutes (schools, labs, organisation...etc)
  - Summaries (LLM generated)
  - Abstracts (first paragraph)
- Chunks Processing Status
  - Chunk Id
  - Processed At
- Chunks
  - Chunk Id
  - Document Id
  - Chunk texts
  - Chunk strategy
- Embeddings
  - Unique Id to each chunk
  - Vectors
  - Embedding Model
  - Embedding Model Params
- Arxiv Papers
  - Arxiv ID (PK, clean ID without version)
  - Title, Authors, Abstract, Categories
  - Download Status (pending/downloading/downloaded/failed)
  - Local PDF Path
  - Published At, Updated At
- Search Runs (audit log of each arxiv search execution)
  - Query String, Date Range, Max Results
  - Result Count, New Papers Count, Status
- Search Run Papers (many-to-many: search run ↔ paper)
  - Search Run ID, Arxiv ID, Rank in Run
- PG view to combine, row grain at chunks (includes arxiv metadata via LEFT JOIN)
  - Final View table for RAG querying

## API endpoints

- https://jina.ai/reader/
- ...

## Folder structure

- ...
