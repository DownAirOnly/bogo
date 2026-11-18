#!/usr/bin/env python3
"""Apply approved photo database entries to the deal catalog.

Approvals require an exact product match or an explicitly labeled representative
variant. Image caching is handled separately by cache_images.py.
"""
import json
from pathlib import Path
catalog_path=Path("data/deals.json")
database_path=Path("data/product-images.json")
catalog=json.loads(catalog_path.read_text())
database=json.loads(database_path.read_text())
count=0
for deal in catalog["deals"]:
    record=database.get("products",{}).get(deal["id"])
    if not record or record.get("status")!="approved":continue
    image=record.get("imageUrl","")
    if not image.startswith("https://"):continue
    if record.get("matchType")=="representative" and not record.get("variantLabel"):
        print("Skipped unlabeled representative",deal["id"])
        continue
    deal["image"]=image
    deal["imageSource"]=record.get("source","Product photo database")
    deal["imageVariant"]=record.get("variantLabel","")
    deal["imageStatus"]="pending-cache"
    count+=1
catalog_path.write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+"\n")
print("Applied",count,"approved photo records")
