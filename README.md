# Web Scraper in Python

Web scraper modulare che estrae e salva tutti i contenuti di una pagina web in formato JSON.

## Installazione dipendenze

```bash
pip install -r requirements.txt
```

## Utilizzo

Lo scraper può essere usato in due modi:

### 1. Linea di comando

```bash
# Scraping base - salva i risultati in ./Results
python scraper.py https://example.com

# Scraping multiplo - ogni URL genera un file JSON separato in ./Results
python scraper.py https://example.com https://example.org/articolo

# Salvataggio in percorso specifico (solo con un singolo URL)
python scraper.py https://example.com -o risultato.json

# Specifica una cartella di output personalizzata
python scraper.py https://example.com --output-dir ./miei_risultati

# Stampa anche su console
python scraper.py https://example.com --stdout

# Opzioni aggiuntive
python scraper.py https://example.com --timeout 20 --user-agent "MyScraper/1.0" --no-pretty
```

Opzioni disponibili:
- `-o, --output`: Percorso del file di output JSON (solo quando è presente un unico URL)
- `--output-dir`: Cartella in cui salvare i risultati (default `Results`)
- `--stdout`: Stampa l'output su console oltre a salvarlo
- `--timeout`: Timeout delle richieste HTTP (secondi)
- `--user-agent`: User Agent personalizzato
- `--no-pretty`: Disabilita la formattazione leggibile del JSON

### 2. Modulo Python

```python
from content_extractor import ContentExtractor
from json_formatter import save_json

# Crea l'estrattore
extractor = ContentExtractor(timeout=10)

# Estrai i contenuti
data = extractor.extract("https://example.com")

# Salva il risultato
save_json(data, "output.json")
```

## Struttura del progetto

Il progetto è composto da diversi moduli per una migliore organizzazione:

- `scraper.py`: Script principale per l'esecuzione da linea di comando
- `content_extractor.py`: Orchestrazione dell'estrazione dei contenuti
- `html_parser.py`: Recupero e parsing delle pagine HTML con focus sui contenuti giornalistici
- `json_formatter.py`: Formattazione e salvataggio in formato JSON
- `utils.py`: Funzioni di utilità condivise

## Struttura del JSON di output

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

## Esempi

Per un esempio completo di utilizzo, puoi testare lo scraper con:

```bash
python scraper.py https://www.example.com
```
