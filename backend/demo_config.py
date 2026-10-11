"""Author-chosen observed demo date (backend/config/demo.yaml); not a selection rule."""
from pathlib import Path
import yaml


def demo_date():
    path = Path(__file__).parent/'config/demo.yaml'
    if not path.exists():
        return None
    value = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}).get('demo_date')
    return value.isoformat() if hasattr(value, 'isoformat') else (str(value) if value else None)
