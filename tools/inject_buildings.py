# Adds the building footprints in data/overture_buildings.json to raw/area.json as OSM-style building ways,
# so tools/build_campus.py treats them like OpenStreetMap buildings. OSM has no buildings for this campus.
# usage: python3 tools/inject_buildings.py <raw_dir>
# data/overture_buildings.json may carry optional per-building "name" and "levels" (added by hand once they are known).
import json, os, sys

RAW = sys.argv[1]
src = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "overture_buildings.json"), encoding="utf-8"))
area = json.load(open(os.path.join(RAW, "area.json")))
area["elements"] = [e for e in area["elements"] if not str(e.get("id", "")).startswith("-")]   # re-runnable
for i, b in enumerate(src["buildings"]):
    tags = {"building": "yes", "source": "overture"}
    if b.get("name"): tags["name"] = b["name"]
    if b.get("levels"): tags["building:levels"] = str(b["levels"])
    area["elements"].append({"type": "way", "id": -(i + 1), "tags": tags, "geometry": [{"lat": y, "lon": x} for x, y in b["ring"]]})
json.dump(area, open(os.path.join(RAW, "area.json"), "w"))
print(f"injected {len(src['buildings'])} buildings")
