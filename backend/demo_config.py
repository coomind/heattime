"""Author-chosen observed demo date (backend/config/demo.yaml); not a selection rule."""
from pathlib import Path
import yaml


def _value(key):
    path = Path(__file__).parent/'config/demo.yaml'
    if not path.exists():
        return None
    value = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}).get(key)
    return value.isoformat() if hasattr(value, 'isoformat') else (str(value) if value else None)


def demo_date():
    return _value('demo_date')


def extreme_date():
    """Second observed scene: a hotter day where rescheduling still leaves postponements."""
    return _value('extreme_date')
