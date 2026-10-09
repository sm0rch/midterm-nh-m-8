"""Optional CLI; the Streamlit application acquires data automatically."""

import argparse
from datetime import date, datetime
import json
from pathlib import Path

from src.data.acquisition import acquire
from src.data.providers import VN_TIME

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", default="HPG")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(VN_TIME).date())
    parser.add_argument("--report-limit", type=int, default=2)
    args = parser.parse_args()
    if args.report_limit < 0:
        parser.error("report-limit must be nonnegative")
    if args.start > args.as_of:
        parser.error("start must be on or before as-of")
    result = acquire(args.ticker, args.start, args.as_of, Path(__file__).resolve().parents[1], args.report_limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
