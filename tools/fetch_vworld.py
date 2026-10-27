# Downloads building footprints (with names and floor counts where the register has them) from the VWorld Data API
# (국토교통부 도로명주소 건물 레이어) and writes data/vworld_buildings.json, which tools/inject_buildings.py prefers
# over data/overture_buildings.json when it exists.
# usage: VWORLD_KEY=... [VWORLD_DOMAIN=...] python3 tools/fetch_vworld.py [south west north east]
# Needs network access to api.vworld.kr. Field names differ between VWorld layers, so the first run prints the
# property names it saw; adjust NAME_KEYS / FLOOR_KEYS below if the names or floors come out empty.
import json, os, sys, urllib.parse, urllib.request

KEY = os.environ.get("VWORLD_KEY")
if not KEY: sys.exit("set VWORLD_KEY (VWorld 오픈API 인증키)")
DOMAIN = os.environ.get("VWORLD_DOMAIN", "https://jey1994238-ui.github.io")   # must match the service URL registered for the key
S, W, N, E = (map(float, sys.argv[1:5]) if len(sys.argv) >= 5 else (37.2442, 127.2955, 37.2499, 127.3028))
LAYER = os.environ.get("VWORLD_LAYER", "LT_C_SPBD")           # 도로명주소 건물
NAME_KEYS = ("buld_nm", "bld_nm", "bldnm", "buld_nm_dc", "name")
FLOOR_KEYS = ("gro_flo_co", "grnd_flr", "flo_co", "floors")

def page(n):
    q = {"service": "data", "version": "2.0", "request": "GetFeature", "key": KEY, "format": "json", "size": 1000, "page": n,
         "data": LAYER, "geomFilter": f"BOX({W},{S},{E},{N})", "crs": "EPSG:4326", "geometry": "true", "attrFilter": "", "domain": DOMAIN}
    q = {k: v for k, v in q.items() if v != ""}
    with urllib.request.urlopen("https://api.vworld.kr/req/data?" + urllib.parse.urlencode(q), timeout=60) as r:
        return json.load(r)["response"]

feats, n = [], 1
while True:
    res = page(n)
    if res.get("status") != "OK":
        if n == 1: sys.exit("VWorld: " + json.dumps(res, ensure_ascii=False)[:500])
        break
    got = res["result"]["featureCollection"]["features"]; feats += got
    if len(got) < 1000: break
    n += 1
print(len(feats), "features; property names:", sorted({k for f in feats for k in f["properties"]})[:40])

def first(props, keys):
    for k in keys:
        v = props.get(k)
        if v not in (None, "", 0, "0"): return v
out = []
for f in feats:
    g = f["geometry"]; polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for poly in polys:
        ring = [[round(x, 7), round(y, 7)] for x, y in poly[0]]
        name, fl = first(f["properties"], NAME_KEYS), first(f["properties"], FLOOR_KEYS)
        b = {"id": str(f.get("id") or f["properties"].get("bd_mgt_sn") or len(out)), "ring": ring}
        if name: b["name"] = str(name)
        try:
            if fl: b["levels"] = int(float(fl))
        except ValueError: pass
        out.append(b)
json.dump({"source": f"VWorld Data API, layer {LAYER} (국토교통부)", "buildings": out},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "vworld_buildings.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote data/vworld_buildings.json:", len(out), "buildings,", sum("name" in b for b in out), "named,", sum("levels" in b for b in out), "with floors")
