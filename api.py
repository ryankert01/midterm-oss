#!/usr/bin/env python3
import argparse
import requests
import pandas as pd
import sys
import time

def fetch_page(base_url, page, size, headers):
    """Fetch one page of JSON data."""
    url = f"{base_url}?page={page}&size={size}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def fetch_all(base_url, size, headers, pause):
    """Iterate pages until an empty page is returned."""
    all_records = []
    page = 0

    while True:
        print(f"Fetching page {page}...", end="", flush=True)
        data = fetch_page(base_url, page, size, headers)
        n = len(data) if isinstance(data, list) else 0
        print(f" got {n} records.")
        if not data:
            break
        all_records.extend(data)
        page += 1
        if pause:
            time.sleep(pause)

    return all_records

def main():
    p = argparse.ArgumentParser(
        description="Fetch ALL pages of NTPC JSON data and save to CSV"
    )
    p.add_argument("--size", "-s", type=int, default=100,
                   help="Number of records per page (default: 100)")
    p.add_argument("--pause", type=float, default=0,
                   help="Seconds to wait between page requests (default: 0)")
    args = p.parse_args()

    base_url = (
        "https://data.ntpc.gov.tw/api/datasets/"
        "50efd0ee-d589-46e1-813c-4c48afe9b37d/json"
    )
    headers = {"accept": "application/json"}

    try:
        records = fetch_all(base_url, args.size, headers, args.pause)
    except requests.HTTPError as e:
        print(f"\nHTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError fetching data: {e}", file=sys.stderr)
        sys.exit(1)

    if not records:
        print("No data retrieved.", file=sys.stderr)
        sys.exit(1)

    # Convert to DataFrame and write CSV
    df = pd.DataFrame(records)
    output_file = "api.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\nDone! Wrote {len(df)} rows × {len(df.columns)} cols to '{output_file}'")

if __name__ == "__main__":
    main()
