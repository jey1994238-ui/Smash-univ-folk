# Same job as tools/fetch.py, but through the OpenStreetMap editing API (api.openstreetmap.org) instead of Overpass,
# for networks where Overpass is blocked. Writes the same raw/ files that tools/build_campus.py reads.
# usage: python3 tools/fetch_osm_api.py <way_id> <raw_dir> [margin_m]
import json, math, os, subprocess, sys, urllib.request
import xml.etree.ElementTree as ET

WID, RAW = sys.argv[1], sys.argv[2]
MARGIN = float(sys.argv[3]) if len(sys.argv) > 3 else 45.0
API = "https://api.openstreetmap.org/api/0.6"
UA = {"User-Agent": "smash-univ-folk campus data build (github.com/jey1994238-ui/smash-univ-folk)"}

def http(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=200) as r:
            return r.read()
    except Exception:
        return subprocess.run(["curl", "-sf", "-m", "200", "-A", UA["User-Agent"], url], capture_output=True, check=True).stdout

def parse(xml):
    root = ET.fromstring(xml)
    nodes = {n.get("id"): {"lat": float(n.get("lat")), "lon": float(n.get("lon"))} for n in root if n.tag == "node"}
    tags = lambda e: {t.get("k"): t.get("v") for t in e.findall("tag")}
    ways = {}
    for w in root:
        if w.tag == "way":
            geo = [nodes[n.get("ref")] for n in w.findall("nd") if n.get("ref") in nodes]
            ways[w.get("id")] = {"type": "way", "id": int(w.get("id")), "tags": tags(w), "geometry": geo}
    rels = []
    for r in root:
        if r.tag != "relation": continue
        members = [{"type": "way", "ref": int(m.get("ref")), "role": m.get("role"), "geometry": ways[m.get("ref")]["geometry"]}
                   for m in r.findall("member") if m.get("type") == "way" and m.get("ref") in ways]
        if members: rels.append({"type": "relation", "id": int(r.get("id")), "tags": tags(r), "members": members})
    return ways, rels

os.makedirs(os.path.join(RAW, "dem"), exist_ok=True)
ways, _ = parse(http(f"{API}/way/{WID}/full"))
campus = ways[WID]
json.dump({"elements": [campus]}, open(os.path.join(RAW, "campus.json"), "w"))
lats = [p["lat"] for p in campus["geometry"]]; lons = [p["lon"] for p in campus["geometry"]]
lat0 = (min(lats) + max(lats)) / 2; lon0 = (min(lons) + max(lons)) / 2
dlat = MARGIN / 110987; dlon = MARGIN / (111320 * math.cos(math.radians(lat0)))
S_, W_, N_, E_ = min(lats) - dlat, min(lons) - dlon, max(lats) + dlat, max(lons) + dlon
ways, rels = parse(http(f"{API}/map?bbox={W_:.7f},{S_:.7f},{E_:.7f},{N_:.7f}"))
KEYS = ("building", "highway", "landuse", "leisure", "natural")
elements = [w for w in ways.values() if any(k in w["tags"] for k in KEYS)] + [r for r in rels if any(k in r["tags"] for k in KEYS)]
json.dump({"elements": elements}, open(os.path.join(RAW, "area.json"), "w"))

Z = 15
def tile(lat, lon):
    n = 2 ** Z
    return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
x0, y0 = tile(N_, W_); x1, y1 = tile(S_, E_)
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        dst = os.path.join(RAW, "dem", f"{Z}_{x}_{y}.png")
        if not os.path.exists(dst):
            open(dst, "wb").write(http(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png"))
json.dump({"otype": "way", "oid": WID, "bbox": [S_, W_, N_, E_], "center": [lat0, lon0], "margin": MARGIN}, open(os.path.join(RAW, "meta.json"), "w"))
print(f"saved: {len(elements)} features, {sum(1 for e in elements if 'building' in e['tags'])} buildings, {(x1-x0+1)*(y1-y0+1)} elevation tiles, bbox {S_:.7f},{W_:.7f},{N_:.7f},{E_:.7f}")
