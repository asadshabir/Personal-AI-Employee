# Docusaurus Embedding Pipeline

**Enterprise-ready solution for RAG-based knowledge systems**

Pipeline for extracting text from Docusaurus URLs, generating embeddings using Cohere, and storing them in Qdrant for RAG-based retrieval. A comprehensive solution for creating intelligent search systems from documentation sites.

---

## Overview

The Docusaurus Embedding Pipeline provides a complete solution for transforming Docusaurus-based documentation sites into intelligent search systems. It automatically discovers all documentation pages, extracts clean content, generates semantic embeddings, and stores them in a vector database for efficient similarity search.

## Key Capabilities

| Feature | Description |
|---------|-------------|
| **URL Crawling** | Automatically discovers all documentation pages on a Docusaurus site |
| **Text Extraction** | Extracts clean, relevant content while filtering out navigation and UI elements |
| **Content Chunking** | Splits large documents into manageable chunks with overlap |
| **Embedding Generation** | Uses Cohere's powerful embedding models for semantic understanding |
| **Vector Storage** | Stores embeddings in Qdrant for efficient similarity search |
| **Robust Processing** | Handles errors gracefully and respects robots.txt |

## Architecture

The pipeline follows a systematic approach:

```
URL Discovery → Content Extraction → Text Processing → Embedding → Vector Storage
```

1. **URL Discovery**: Crawl Docusaurus site to identify all documentation pages
2. **Content Extraction**: Extract main content while filtering out navigation/UI
3. **Text Processing**: Clean and chunk content with appropriate overlap
4. **Embedding Generation**: Generate semantic embeddings using Cohere models
5. **Vector Storage**: Store in Qdrant for efficient retrieval

## Tech Stack

| Component | Technology |
|-----------|-------------|
| **Language** | Python 3.11+ |
| **Embeddings** | Cohere embedding models |
| **Vector DB** | Qdrant Cloud or local instance |
| **Web Scraping** | Robust HTML parsing and URL handling |
| **Processing** | Asynchronous processing for efficiency |
| **Configuration** | YAML-based configuration system |

## Usage

```python
from docusaurus_pipeline import DocusaurusEmbedder

# Initialize the embedder
embedder = DocusaurusEmbedder(
    site_url="https://your-docusaurus-site.com",
    cohere_api_key="your-cohere-key",
    qdrant_url="your-qdrant-instance"
)

# Process the entire site
await embedder.process_site()

# Perform similarity search
results = await embedder.similarity_search(
    query="How do I configure the authentication system?",
    top_k=5
)
```

## Design Philosophy

This pipeline embodies:

- **Reliability**: Comprehensive error handling and retry mechanisms
- **Efficiency**: Optimized for processing large documentation sites
- **Scalability**: Designed to handle sites with thousands of pages
- **Quality**: Focus on extracting clean, relevant content for best search results

The system ensures that documentation search is both accurate and efficient.

## Real Use Cases

- **Documentation Search**: Create intelligent search for technical documentation
- **Knowledge Bases**: Transform documentation into question-answering systems
- **Support Systems**: Enable automated responses based on documentation content
- **Internal Wikis**: Create semantic search for organizational knowledge

## Future Roadmap

- [ ] Support for additional documentation platforms
- [ ] Enhanced content filtering capabilities
- [ ] Integration with additional embedding models
- [ ] Advanced chunking strategies
- [ ] Real-time update mechanisms

---

*Part of the comprehensive AI tooling ecosystem*