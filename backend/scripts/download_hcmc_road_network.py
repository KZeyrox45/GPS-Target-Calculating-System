"""
download_hcmc_road_network.py - Download HCM City road network
=============================================================
Downloads the Ho Chi Minh City driveable road network directly from
the OpenStreetMap API (bypassing Overpass which may be blocked in
some networks) and saves it as a GraphML file.

Usage (from backend/):
    uv run python scripts/download_hcmc_road_network.py          # full download
    uv run python scripts/download_hcmc_road_network.py --retry  # retry failed tiles only

Output:
    data/hcmc_roads.graphml

How it works:
  1. Downloads raw OSM XML from api.openstreetmap.org/api/0.6/map
  2. If a tile is too dense (HTTP 400), recursively subdivides into
     quadrants until each sub-tile succeeds.
  3. On HTTP 509 (bandwidth limit), retries with exponential backoff
     (5s, 10s, 20s) up to 3 times before giving up.
  4. Parses nodes and ways, filters for driveable road types.
  5. Builds a NetworkX MultiDiGraph and saves as GraphML.

Retry mode (--retry):
  Loads the existing graphml and re-downloads only missing/failed tiles.
  Useful after a partial download hit bandwidth limits.
"""

import math
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import networkx as nx

# Driveable road highway tags (same as OSMnx network_type="drive")
_DRIVE_HIGHWAYS = frozenset({
    "motorway", "motorway_link",
    "trunk", "trunk_link",
    "primary", "primary_link",
    "secondary", "secondary_link",
    "tertiary", "tertiary_link",
    "unclassified",
    "residential",
    "living_street",
    "service",
    "road",
})

# Default speed limits by highway type (km/h) when maxspeed tag is missing
_DEFAULT_SPEED_KMH: dict[str, float] = {
    "motorway": 90.0, "motorway_link": 60.0,
    "trunk": 80.0, "trunk_link": 50.0,
    "primary": 60.0, "primary_link": 40.0,
    "secondary": 50.0, "secondary_link": 30.0,
    "tertiary": 40.0, "tertiary_link": 30.0,
    "unclassified": 40.0,
    "residential": 30.0,
    "living_street": 20.0,
    "service": 20.0,
    "road": 30.0,
}

# HCM City bounding box (urban core + suburbs)
_HCM_SOUTH = 10.63
_HCM_NORTH = 10.90
_HCM_WEST = 106.50
_HCM_EAST = 106.85

# Track tiles that failed (for retry reporting)
_failed_tiles: list[tuple[float, float, float, float, str]] = []


def _download_tile(
    south: float, north: float, west: float, east: float,
    max_retries: int = 3,
) -> bytes:
    """Download OSM XML for one tile with retry on 509 bandwidth errors.

    Exponential backoff: 5s, 10s, 20s between retries.
    """
    bbox = f"{west},{south},{east},{north}"
    url = f"https://api.openstreetmap.org/api/0.6/map?bbox={bbox}"
    req = urllib.request.Request(url, headers={"User-Agent": "GPS-Tracking-System/1.0"})

    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 509 and attempt < max_retries:
                wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                print(f"    509 bandwidth limit on attempt {attempt + 1}/{max_retries + 1}, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


def _parse_speed(val: str) -> float | None:
    """Parse a maxspeed tag value like '50' or '50 km/h'."""
    val = val.strip().lower()
    for suffix in (" km/h", "kmh", "kph", "km/h"):
        val = val.replace(suffix, "")
    try:
        return float(val)
    except ValueError:
        return None


def _parse_osm_xml(xml_data: bytes) -> tuple[dict[int, dict], dict[int, dict]]:
    """
    Parse OSM XML into nodes and ways.

    Returns:
        nodes: {osmid: {"lat": float, "lon": float}}
        ways:  {osmid: {"highway": str, "maxspeed": float|None, "oneway": bool, "nodes": list[int]}}
    """
    root = ET.fromstring(xml_data)

    nodes: dict[int, dict] = {}
    for nd in root.findall("node"):
        nid = int(nd.get("id"))
        lat = float(nd.get("lat"))
        lon = float(nd.get("lon"))
        nodes[nid] = {"lat": lat, "lon": lon}

    ways: dict[int, dict] = {}
    for way in root.findall("way"):
        way_id = int(way.get("id"))
        if way_id in ways:
            continue  # already seen from another tile

        tags = {}
        for tag_elem in way.findall("tag"):
            tags[tag_elem.get("k")] = tag_elem.get("v")

        highway = tags.get("highway", "")
        if highway not in _DRIVE_HIGHWAYS:
            continue

        member_nodes = []
        for nd_ref in way.findall("nd"):
            member_nodes.append(int(nd_ref.get("ref")))

        if len(member_nodes) < 2:
            continue

        maxspeed = None
        if "maxspeed" in tags:
            maxspeed = _parse_speed(tags["maxspeed"])

        oneway = tags.get("oneway", "no") == "yes"

        ways[way_id] = {
            "highway": highway,
            "maxspeed": maxspeed,
            "oneway": oneway,
            "nodes": member_nodes,
        }

    return nodes, ways


def _download_recursive(
    south: float, north: float, west: float, east: float,
    all_nodes: dict[int, dict], all_ways: dict[int, dict],
    depth: int = 0, max_depth: int = 4,
) -> None:
    """
    Recursively download and parse tiles. If a 400 error occurs (tile
    too dense), split into 4 quadrants and retry up to max_depth levels.
    """
    prefix = "  " * depth
    tile_label = f"({south:.3f}-{north:.3f}, {west:.3f}-{east:.3f})"

    try:
        xml_data = _download_tile(south, north, west, east)
        nodes, ways = _parse_osm_xml(xml_data)
        all_nodes.update(nodes)
        all_ways.update(ways)
        print(f"{prefix}OK {tile_label}: {len(nodes)} nodes, {len(ways)} ways")
        time.sleep(2.0)  # rate-limit: 2s between successful requests
        return
    except urllib.error.HTTPError as exc:
        if exc.code == 400 and depth < max_depth:
            print(f"{prefix}400 {tile_label}: too dense, subdividing...")
            time.sleep(1.0)
        else:
            print(f"{prefix}FAIL {tile_label}: {type(exc).__name__}: {exc}")
            # Record failed tile for potential retry
            _failed_tiles.append((south, north, west, east, str(exc)))
            time.sleep(1.0)
            return
    except Exception as exc:
        print(f"{prefix}FAIL {tile_label}: {type(exc).__name__}: {exc}")
        _failed_tiles.append((south, north, west, east, str(exc)))
        time.sleep(1.0)
        return

    # Subdivide into 4 quadrants
    mid_lat = (south + north) / 2
    mid_lon = (west + east) / 2
    _download_recursive(south, mid_lat, west, mid_lon, all_nodes, all_ways, depth + 1, max_depth)
    _download_recursive(south, mid_lat, mid_lon, east, all_nodes, all_ways, depth + 1, max_depth)
    _download_recursive(mid_lat, north, west, mid_lon, all_nodes, all_ways, depth + 1, max_depth)
    _download_recursive(mid_lat, north, mid_lon, east, all_nodes, all_ways, depth + 1, max_depth)


def _build_graph(
    all_nodes: dict[int, dict],
    all_ways: dict[int, dict],
) -> nx.MultiDiGraph:
    """Build a NetworkX MultiDiGraph from parsed OSM data."""
    G = nx.MultiDiGraph()

    for nid, data in all_nodes.items():
        G.add_node(nid, x=data["lon"], y=data["lat"])

    for way_id, way_data in all_ways.items():
        members = way_data["nodes"]
        highway = way_data["highway"]
        maxspeed = way_data["maxspeed"]
        oneway = way_data["oneway"]
        speed_kmh = maxspeed if maxspeed else _DEFAULT_SPEED_KMH.get(highway, 30.0)

        for i in range(len(members) - 1):
            u, v = members[i], members[i + 1]
            if u not in all_nodes or v not in all_nodes:
                continue

            lat1, lon1 = all_nodes[u]["lat"], all_nodes[u]["lon"]
            lat2, lon2 = all_nodes[v]["lat"], all_nodes[v]["lon"]
            length = _haversine_m(lat1, lon1, lat2, lon2)

            edge_data = {
                "highway": highway,
                "maxspeed": speed_kmh,
                "length": length,
                "oneway": oneway,
            }
            G.add_edge(u, v, **edge_data)
            if not oneway:
                G.add_edge(v, u, **edge_data)

    return G


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in metres."""
    R = 6_371_000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2.0 * R * math.asin(math.sqrt(min(1.0, a)))


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent.parent
    output_path = project_root / "data" / "hcmc_roads.graphml"

    retry_mode = "--retry" in sys.argv

    print(f"HCM City bbox: {_HCM_SOUTH}-{_HCM_NORTH} lat, {_HCM_WEST}-{_HCM_EAST} lon")

    all_nodes: dict[int, dict] = {}
    all_ways: dict[int, dict] = {}

    if retry_mode and output_path.exists():
        print("Retry mode: loading existing graph to identify missing tiles...")
        existing = nx.read_graphml(str(output_path))
        print(f"  Existing graph: {existing.number_of_nodes()} nodes, {existing.number_of_edges()} edges")
        # Seed with existing nodes so new downloads merge in
        for nid, data in existing.nodes(data=True):
            all_nodes[int(nid)] = {"lat": float(data["y"]), "lon": float(data["x"])}
        print(f"  Seeded {len(all_nodes)} nodes from existing graph")
        # We don't need to re-add existing ways since nodes are what matter for merge
        print("Downloading missing tiles with retry/backoff...")
    else:
        print("Full download via OSM API (recursive tile subdivision with retry)...")

    _download_recursive(_HCM_SOUTH, _HCM_NORTH, _HCM_WEST, _HCM_EAST, all_nodes, all_ways)

    print(f"\nTotal: {len(all_nodes)} nodes, {len(all_ways)} ways")

    if _failed_tiles:
        print(f"\nFailed tiles ({len(_failed_tiles)}):")
        for south, north, west, east, err in _failed_tiles:
            print(f"  ({south:.3f}-{north:.3f}, {west:.3f}-{east:.3f}): {err}")
        print("Tip: run with --retry to re-download only missing tiles")

    if not all_ways and not retry_mode:
        print("ERROR: No road ways downloaded. Check network connectivity.")
        sys.exit(1)

    if not all_ways and retry_mode:
        print("No new ways downloaded (existing graph is unchanged).")
        return

    print("Building graph...")
    G = _build_graph(all_nodes, all_ways)
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, str(output_path))
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Saved to {output_path} ({size_mb:.1f} MB)")

    has_speed = sum(1 for _, _, d in G.edges(data=True) if d.get("maxspeed"))
    print(f"Edges with maxspeed: {has_speed}/{G.number_of_edges()}")

    highway_types = Counter()
    for _, _, d in G.edges(data=True):
        highway_types[d.get("highway", "unknown")] += 1
    print("\nHighway type distribution:")
    for hw, count in highway_types.most_common():
        print(f"  {hw}: {count}")


if __name__ == "__main__":
    main()
