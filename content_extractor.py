from typing import Dict, Any
from html_parser import HTMLParser
from utils import setup_logging

logger = setup_logging()

class ContentExtractor:
    """Orchestratore che usa HTMLParser per costruire un output completo."""

    def __init__(self, timeout: int = 10, user_agent: str | None = None):
        self.parser = HTMLParser(timeout=timeout, user_agent=user_agent)

    def extract(self, url: str) -> Dict[str, Any]:
        page_info, html = self.parser.fetch_page(url)
        parsed = self.parser.parse_html(html, page_info["url"])  # usa l'URL finale dopo redirect
        return {
            "page": page_info,
            "content": parsed,
        }
