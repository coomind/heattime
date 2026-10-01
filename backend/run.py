"""Local/container startup without dotenv or credential access."""
import argparse
from pathlib import Path
import uvicorn
from backend.app import create_app


def main():
    parser = argparse.ArgumentParser(description='HeatTime mock demo')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--db', type=Path, default=None)
    args = parser.parse_args()
    uvicorn.run(create_app(args.db), host=args.host, port=args.port)


if __name__ == '__main__':
    main()
