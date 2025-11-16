import re
import logging
from typing import Dict, Any

def setup_logging(level=logging.INFO):
    """Configura il sistema di logging"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraper.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('webscraper')

def is_valid_url(url: str) -> bool:
    """Verifica se l'URL fornito è valido"""
    pattern = re.compile(
        r'^(https?:\/\/)?'  # http:// o https://
        r'((([A-Za-z0-9-]+\.)+[A-Za-z]{2,})|'  # dominio
        r'localhost|'  # localhost
        r'(\d{1,3}\.){3}\d{1,3})'  # o indirizzo IP
        r'(\:\d+)?'  # porta opzionale
        r'(\/[^\s]*)?$', re.IGNORECASE)
    return re.match(pattern, url) is not None

def clean_text(text: str) -> str:
    """Pulisce il testo rimuovendo spazi extra e caratteri non necessari"""
    if not text:
        return ""
    return ' '.join(text.split())

def format_size(size_bytes: int) -> str:
    """Converte una dimensione in byte in un formato leggibile"""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/(1024*1024):.1f} MB"