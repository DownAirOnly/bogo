#!/usr/bin/env python3
"""Fast, offline pre-deployment validation of the dated BOGO data files."""
import datetime as dt
import json
from pathlib import Path

CATALOGS = (
    Path("data/current-deals.json"),
    Path("data/previous-deals.json"),
    Path("data/deals.json"),
    Path("data/next-deals.json"),
)

def validate(path):
    catalog = json.loads(path.read_text(encoding="utf-8"))
    start=dt.date.fromisoformat(catalog["saleStart"])
    end=dt.date.fromisoformat(catalog["saleEnd"])
    if not 5 <= (end-start).days <= 8:
        raise ValueError(f"{path}: unusual sale duration")
    deals=catalog["deals"]
    if len(deals)<50:
        raise ValueError(f"{path}: only {len(deals)} deals")
    ids=set()
    for i,deal in enumerate(deals):
        ident=deal.get("id")
        if not isinstance(ident,str) or not ident.strip() or ident in ids:
            raise ValueError(f"{path}: invalid/duplicate ID at row {i}")
        ids.add(ident)
        if not isinstance(deal.get("name"),str) or len(deal["name"].strip())<3:
            raise ValueError(f"{path}: invalid name at row {i}")
        lo,hi=deal.get("priceMin"),deal.get("priceMax")
        if lo is not None and hi is not None:
            if not isinstance(lo,(int,float)) or not isinstance(hi,(int,float)) or lo<0 or hi<lo or hi>300:
                raise ValueError(f"{path}: invalid price range at row {i}")
    print(f"Catalog valid: {path} — {len(deals)} BOGOs ({start} to {end})")

def main():
    if not Path("data/deals.json").is_file():
        raise SystemExit("Main BOGO catalog missing")
    found=0
    for path in CATALOGS:
        if path.is_file():
            validate(path)
            found+=1
    print("Catalog checks passed:",found,"files")

if __name__=="__main__":
    main()
