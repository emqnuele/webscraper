import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

from utils import is_valid_url, setup_logging
from content_extractor import ContentExtractor
from json_formatter import save_json, to_json

logger = setup_logging()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Web scraper semplice in JSON")
    parser.add_argument("urls", nargs="+", help="Uno o più URL delle pagine da analizzare")
    parser.add_argument("-o", "--output", help="Percorso file di output (solo se viene fornito un singolo URL)")
    parser.add_argument("--output-dir", default="Results", help="Cartella dove salvare i risultati (default: Results)")
    parser.add_argument("--no-pretty", action="store_true", help="Disabilita la formattazione leggibile del JSON")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout richieste HTTP (s)")
    parser.add_argument("--user-agent", type=str, default=None, help="User-Agent personalizzato")
    parser.add_argument("--stdout", action="store_true", help="Stampa il JSON su stdout oltre a salvarlo su file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    invalid_urls = [url for url in args.urls if not is_valid_url(url)]
    if invalid_urls:
        logger.error(f"Gli URL non sono validi: {invalid_urls}")
        return 2

    if len(args.urls) > 1 and args.output:
        logger.warning("Opzione --output ignorata quando si specificano più URL. Verrà usata la cartella dei risultati.")

    base_output_dir = Path(args.output_dir)
    base_output_dir.mkdir(parents=True, exist_ok=True)

    extractor = ContentExtractor(timeout=args.timeout, user_agent=args.user_agent)
    encountered_error = False

    for idx, url in enumerate(args.urls, start=1):
        try:
            logger.info(f"==> Elaborazione URL {idx}/{len(args.urls)}: {url}")
            data = extractor.extract(url)

            if args.stdout:
                print(f"\n=== {url} ===")
                print(to_json(data, pretty=(not args.no_pretty)), flush=True)

            output_path = determine_output_path(
                custom_output=args.output if len(args.urls) == 1 else None,
                output_dir=base_output_dir,
                data=data,
                url=url,
                index=idx
            )
            saved = save_json(data, str(output_path), pretty=(not args.no_pretty))
            logger.info(f"Risultato salvato in: {saved}")

        except Exception as exc:
            encountered_error = True
            logger.exception(f"Errore durante lo scraping di {url}: {exc}")

    return 0 if not encountered_error else 1


def determine_output_path(
    custom_output: str | None,
    output_dir: Path,
    data: dict,
    url: str,
    index: int
) -> Path:
    if custom_output:
        return Path(custom_output)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    domain = data.get("content", {}).get("domain") or urlparse(url).netloc or "output"
    slug = sanitize_slug(urlparse(url).path) or "page"
    filename = f"scrape_{sanitize_slug(domain)}_{slug}_{ts}_{index}.json"
    return output_dir / filename


def sanitize_slug(value: str) -> str:
    trimmed = value.strip("/")
    if not trimmed:
        return ""
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", trimmed)
    return normalized.strip("_") or ""


if __name__ == "__main__":
    sys.exit(main())
