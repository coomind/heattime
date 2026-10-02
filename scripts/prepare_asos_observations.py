"""Normalize existing, user-collected samples only. No network or credentials."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.weather.asos_samples import SampleDataset, DATASET


def prepare(source, output=DATASET):
    dataset = SampleDataset(source)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dataset.normalized(),ensure_ascii=False,separators=(',', ':'))+'\n',encoding='utf-8')
    return {'station': dataset.station_id, 'records': len(dataset.rows), 'days': len(dataset.dates),
            'original_sha256': dataset.original_sha256}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source)))
