import json
from typing import Any, Dict, Optional
from pathlib import Path


def to_json(data: Dict[str, Any], pretty: bool = True) -> str:
    """Converte un dizionario in stringa JSON."""
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def save_json(data: Dict[str, Any], output_path: str, pretty: bool = True) -> str:
    """Salva i dati JSON su file e restituisce il percorso del file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    json_str = to_json(data, pretty=pretty)
    path.write_text(json_str, encoding="utf-8")
    return str(path)
