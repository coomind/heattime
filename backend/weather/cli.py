"""Run with python -m backend.weather.cli; no .env reader or network access."""
import argparse
from datetime import date
import json
import sys
from pathlib import Path
from .adapters import MockForecastAdapter, MockAsosAdapter
from .models import Venue
from .storage import WeatherStore

ROOT = Path(__file__).resolve().parents[2]


def demo_venues() -> list[Venue]:
    data = json.loads((ROOT / "data/mock/venues.json").read_text(encoding="utf-8"))
    return [Venue(**row) for row in data]


def run(day: date, db: Path, provider: str) -> dict:
    venues = demo_venues()
    store = WeatherStore(db)
    store.save_venues(venues)
    points = []
    for venue in venues:
        if provider == "forecast":
            points.extend(MockForecastAdapter().fetch(venue, day))
        elif provider == "asos":
            points.extend(MockAsosAdapter().fetch(venue, venue.asos_station_id, day))
        else:
            raise ValueError("Unknown mock provider")
    store.save_weather(points)
    source = "kma_fcst" if provider == "forecast" else "asos_obs"
    saved = store.load_weather(source=source, is_mock=True)
    count = sum(p.valid_time.date() == day for p in saved)
    return {"label": "가상 예시 · mock 합성 기상 (실제 관측 아님)", "date": day.isoformat(),
            "source": source, "venues": len(venues), "stored_for_day": count, "db": str(db)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="HeatTime P1 mock ingestion")
    parser.add_argument("--date", type=date.fromisoformat, default=date(2026, 8, 1))
    parser.add_argument("--db", type=Path, default=ROOT / "data/heattime.sqlite3")
    parser.add_argument("--provider", choices=["forecast", "asos"], default="forecast")
    args = parser.parse_args()
    print(json.dumps(run(args.date, args.db, args.provider), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
