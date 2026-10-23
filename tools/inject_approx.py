# Adds the approximate building footprints in data/buildings_approx.json to raw/area.json as OSM-style building ways,
# so tools/build_campus.py treats them like real OpenStreetMap buildings.
# usage: python3 tools/inject_approx.py <raw_dir> [preview.png]
import json, math, os, sys

RAW = sys.argv[1]
src = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "buildings_approx.json"), encoding="utf-8"))
LAT0, LON0 = src["origin"]
MLAT = 110987.0; MLON = 111320.0 * math.cos(math.radians(LAT0))
def corners(b):
    a = math.radians(b["a"]); ux, uz = math.cos(a), math.sin(a); vx, vz = -uz, ux
    return [(b["x"] + sx * b["w"] / 2 * ux + sz * b["d"] / 2 * vx, b["z"] + sx * b["w"] / 2 * uz + sz * b["d"] / 2 * vz)
            for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
area = json.load(open(os.path.join(RAW, "area.json")))
area["elements"] = [e for e in area["elements"] if not str(e.get("id", "")).startswith("-")]   # re-runnable
for i, b in enumerate(src["buildings"]):
    ring = corners(b); ring.append(ring[0])
    geo = [{"lat": LAT0 - z / MLAT, "lon": LON0 + x / MLON} for x, z in ring]
    area["elements"].append({"type": "way", "id": -(i + 1), "tags": {"building": "yes", "name": b["n"], "building:levels": str(b["lv"]), "approx": "yes"}, "geometry": geo})
json.dump(area, open(os.path.join(RAW, "area.json"), "w"))
print(f"injected {len(src['buildings'])} approximate buildings")
