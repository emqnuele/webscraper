# Web Scraper in Python

Modular web scraper that extracts and saves the meaningful content of a web page as JSON.

## Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

You can run the scraper in two ways:

### 1. Command line

```bash
# Basic scraping - saves results under ./Results
python scraper.py https://example.com

# Multiple URLs - each one produces a JSON file in ./Results
python scraper.py https://example.com https://example.org/article

# Save to a specific file (single URL only)
python scraper.py https://example.com -o result.json

# Custom output directory
python scraper.py https://example.com --output-dir ./my_results

# Also print to stdout
python scraper.py https://example.com --stdout

# Additional options
python scraper.py https://example.com --timeout 20 --user-agent "MyScraper/1.0" --no-pretty
```

Available options:
- `-o, --output`: JSON output path (only when a single URL is provided)
- `--output-dir`: Directory where results are saved (default `Results`)
- `--stdout`: Print JSON to console in addition to saving it
- `--timeout`: HTTP request timeout (seconds)
- `--user-agent`: Custom User-Agent string
- `--no-pretty`: Disable pretty-printed JSON

### 2. Python module

```python
from content_extractor import ContentExtractor
from json_formatter import save_json

# Create the extractor
extractor = ContentExtractor(timeout=10)

# Extract content
data = extractor.extract("https://example.com")

# Save the result
save_json(data, "output.json")
```

## Project structure

The project is split into several modules for clarity:

- `scraper.py`: Command line entry point
- `content_extractor.py`: Coordinates the scraping workflow
- `html_parser.py`: Fetches and parses HTML focusing on news articles
- `json_formatter.py`: Formats and writes JSON
- `utils.py`: Shared helper functions

## Output JSON structure

```json
{
  "page": {
    "url": "https://example.com",
    "status_code": 200,
    "encoding": "utf-8",
    "size_bytes": 1234,
    "size_readable": "1.2 KB",
    "headers": {...}
  },
  "content": {
    "title": "Titolo della pagina",
    "base_url": "https://example.com",
    "domain": "example.com",
    "meta": {...},
    "article": {
      "title": "Titolo articolo",
      "subtitle": "Sottotitolo",
      "section": "Cronaca",
      "authors": ["Nome Cognome"],
      "published_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "excerpt": "Primo paragrafo significativo...",
      "keywords": ["tag1", "tag2"],
      "body": {
        "text": "...",
        "paragraphs": ["...", "..."],
        "word_count": 480,
        "reading_time_minutes": 2.4,
        "source": "readability|heuristic",
        "html": "<p>...</p>"
      },
      "media": {
        "hero_image": "https://example.com/hero.jpg",
        "gallery": [{"src": "...", "alt": "..."}],
        "videos": ["https://..."]
      },
      "links": [{"text": "...", "href": "..."}],
      "lists": {"ul": [...], "ol": [...]},
      "tables": [...],
      "stats": {
        "confidence": 0.88,
        "paragraph_count": 6,
        "has_media": true,
        "has_links": false
      }
    },
    "context": {
      "headings": {...},
      "related_links": [...],
      "candidates": [
        {"id": "block_0", "heading": "Titolo", "word_count": 520, "score": 820.5, "dom_path": "..."}
      ]
    }
  }
}
```

## Examples

For a quick test run:

```bash
python scraper.py https://www.example.com
```
