"""
data_loaders.py - Real-world trajectory dataset loaders
=========================================================
Loads and preprocesses trajectory data from:
  - Geolife dataset (pedestrian walk segments, GPS WGS-84)
  - AMIT dataset (motorcycle tracks from UAV camera, metric coordinates)

Both loaders return segments as NumPy arrays of (East, North) positions
sampled at 10 Hz in a local ENU flat-earth frame centred at the segment
centroid.  Altitude is set to 0.0 for all ground-level targets.

ENU frame origin convention:
  - Geolife: centroid of the walk segment (mean lat/lon) projected to flat ENU.
  - AMIT: centroid of the vehicle track (mean FrontX+RearX/2, FrontY+RearY/2).

Data directories (relative to project root):
  - Geolife: data/Geolife Trajectories 1.3/Data/
  - AMIT:    data/AMIT/
"""

import csv
import logging
import math
from datetime import datetime
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.interpolate import PchipInterpolator

logger = logging.getLogger(__name__)

# Project root: 4 levels up from this file (backend/app/simulation/data_loaders.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_GEOLIFE_ROOT = _PROJECT_ROOT / "data" / "Geolife Trajectories 1.3" / "Data"
_AMIT_ROOT = _PROJECT_ROOT / "data" / "AMIT"

# Target sampling rate
_TARGET_HZ = 10.0
_TARGET_DT = 1.0 / _TARGET_HZ

# Geolife segment filter criteria
_WALK_DURATION_MIN_S = 60.0    # minimum segment length (seconds)
_WALK_DURATION_MAX_S = 180.0   # maximum segment length
_WALK_MAX_DISPLACEMENT_M = 390.0  # max distance any point from centroid
_WALK_MAX_GAP_S = 3.0          # max time gap between consecutive GPS points
_WALK_MIN_POINTS = 20          # minimum GPS points before interpolation

# AMIT filter criteria
_AMIT_MIN_FRAMES = 30          # minimum 30 frames = 6 s at 5 Hz = 60 points at 10 Hz
_AMIT_CLASS_MOTORCYCLE = "m"


# -------------------------------------------------------------------------
# Coordinate utilities
# -------------------------------------------------------------------------

def _lat_lon_to_enu(lat: float, lon: float, lat_ref: float, lon_ref: float) -> tuple[float, float]:
    """
    Flat-earth ENU approximation.  Accurate to within 0.1% for distances < 10 km.

    Returns (east_m, north_m) relative to (lat_ref, lon_ref).
    """
    R = 6_371_000.0
    north = R * math.radians(lat - lat_ref)
    east = R * math.cos(math.radians(lat_ref)) * math.radians(lon - lon_ref)
    return east, north


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in metres between two WGS-84 points."""
    R = 6_371_000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2.0 * R * math.asin(math.sqrt(min(1.0, a)))


# -------------------------------------------------------------------------
# Geolife loader
# -------------------------------------------------------------------------

def _parse_plt(path: Path) -> list[tuple[datetime, float, float]]:
    """
    Parse a Geolife .plt file.

    Returns a list of (datetime_utc, lat, lon) sorted by time.
    The first 6 lines are header and are skipped.
    Format: lat,lon,0,alt_feet,days_since_1899,date,time
    """
    records: list[tuple[datetime, float, float]] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i < 6:
                    continue
                parts = line.strip().split(",")
                if len(parts) < 7:
                    continue
                try:
                    lat = float(parts[0])
                    lon = float(parts[1])
                    date_str = parts[5].strip()
                    time_str = parts[6].strip()
                    dt = datetime.strptime(
                        f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S"
                    ).replace(tzinfo=datetime.UTC)
                    records.append((dt, lat, lon))
                except (ValueError, IndexError):
                    continue
    except OSError as e:
        logger.warning("Skipping unreadable trajectory file: %s", e)
    return records


def _parse_labels(path: Path) -> list[tuple[datetime, datetime, str]]:
    """
    Parse a Geolife labels.txt file.

    Returns a list of (start_dt, end_dt, mode) for each labeled segment.
    """
    labels: list[tuple[datetime, datetime, str]] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i == 0:  # header line
                    continue
                parts = line.strip().split("\t")
                if len(parts) < 3:
                    continue
                try:
                    start = datetime.strptime(parts[0].strip(), "%Y/%m/%d %H:%M:%S").replace(tzinfo=datetime.UTC)
                    end = datetime.strptime(parts[1].strip(), "%Y/%m/%d %H:%M:%S").replace(tzinfo=datetime.UTC)
                    mode = parts[2].strip().lower()
                    labels.append((start, end, mode))
                except (ValueError, IndexError):
                    continue
    except OSError as e:
        logger.warning("Skipping unreadable labels file: %s", e)
    return labels


def _build_walk_segment(
    records: list[tuple[datetime, float, float]],
    start_dt: datetime,
    end_dt: datetime,
) -> np.ndarray | None:
    """
    Extract GPS points between start_dt and end_dt from a list of records,
    apply quality filters, interpolate to 10 Hz using PCHIP, and return a
    (N, 2) float64 array of (east, north) positions in metres.

    Returns None if the segment fails any filter criterion.
    """
    # Extract points in the labeled window
    points = [(dt, lat, lon) for dt, lat, lon in records
              if start_dt <= dt <= end_dt]

    if len(points) < _WALK_MIN_POINTS:
        return None

    # Check duration
    t_start = points[0][0].timestamp()
    t_end = points[-1][0].timestamp()
    duration = t_end - t_start
    if not (_WALK_DURATION_MIN_S <= duration <= _WALK_DURATION_MAX_S):
        return None

    # Check for gaps > 3 s
    times_s = np.array([p[0].timestamp() for p in points])
    gaps = np.diff(times_s)
    if np.any(gaps > _WALK_MAX_GAP_S):
        return None

    lats = np.array([p[1] for p in points])
    lons = np.array([p[2] for p in points])

    # Compute ENU relative to segment centroid
    lat_c = float(np.mean(lats))
    lon_c = float(np.mean(lons))
    enu = np.array([_lat_lon_to_enu(la, lo, lat_c, lon_c) for la, lo in zip(lats, lons)])

    # Check max displacement from centroid
    dist = np.sqrt(enu[:, 0] ** 2 + enu[:, 1] ** 2)
    if np.max(dist) > _WALK_MAX_DISPLACEMENT_M:
        return None

    # PCHIP interpolation to 10 Hz
    t_rel = times_s - times_s[0]
    t_new = np.arange(0.0, t_rel[-1], _TARGET_DT)
    if len(t_new) < int(_WALK_DURATION_MIN_S * _TARGET_HZ):
        return None

    try:
        pchip_e = PchipInterpolator(t_rel, enu[:, 0])
        pchip_n = PchipInterpolator(t_rel, enu[:, 1])
        east_interp = pchip_e(t_new)
        north_interp = pchip_n(t_new)
    except ValueError:
        return None

    return np.column_stack([east_interp, north_interp])


class GeolifeWalkLoader:
    """
    Loads pedestrian walk segments from the Geolife GPS trajectory dataset.

    The dataset contains GPS trajectories collected by 182 users in Beijing,
    China.  Of these, 69 users have transport mode labels (walk, bus, bike,
    taxi, etc.).  This loader extracts only the segments labelled as walk,
    filters them by duration (60-180 s), maximum displacement (< 390 m from
    centroid), and time gap (consecutive GPS points no more than 3 s apart),
    then interpolates to 10 Hz using PCHIP.

    Gap threshold justification: the Geolife walk-dense segments have a
    nominal sampling interval of 1-2 s.  A gap exceeding 3 s (three times
    the nominal interval) represents either a GPS dropout or a mode
    boundary and is therefore excluded to avoid generating spurious
    interpolated velocities.

    PCHIP is used instead of natural cubic spline because PCHIP is
    shape-preserving and monotone within each sub-interval.  Where a
    pedestrian stands still between two GPS points, PCHIP keeps the
    interpolated velocity near zero; natural cubic spline would introduce
    a velocity hump at the stop-to-walk transition.
    """

    _segments: list[np.ndarray] | None = None  # module-level cache
    _CACHE_PATH = _GEOLIFE_ROOT / "_cached_segments.npz"

    @classmethod
    def load(cls) -> list[np.ndarray]:
        """
        Load and cache all valid walk segments.  Idempotent: subsequent calls
        return the cached result without re-reading disk.
        A binary cache avoids re-parsing 18,670 Geolife files.
        """
        if cls._segments is not None:
            return cls._segments

        # Try loading from binary cache first
        if cls._CACHE_PATH.exists():
            try:
                data = np.load(cls._CACHE_PATH, allow_pickle=False)
                if "offsets" in data:
                    flat = data["data"]
                    offsets = data["offsets"]
                    cls._segments = [flat[offsets[i]:offsets[i + 1]] for i in range(len(offsets) - 1)]
                else:
                    keys = sorted(data.files, key=lambda s: int(s.split("_")[1]))
                    cls._segments = [data[k] for k in keys]
                logger.info("GeolifeWalkLoader: loaded %d segments from cache", len(cls._segments))
                return cls._segments
            except (OSError, ValueError):
                logger.warning("Geolife cache corrupt, re-parsing .plt files")

        if not _GEOLIFE_ROOT.exists():
            logger.warning("Geolife dataset not found at %s", _GEOLIFE_ROOT)
            cls._segments = []
            return cls._segments

        segments: list[np.ndarray] = []
        user_dirs = sorted(p for p in _GEOLIFE_ROOT.iterdir() if p.is_dir())

        for user_dir in user_dirs:
            labels_file = user_dir / "labels.txt"
            if not labels_file.exists():
                continue

            labels = _parse_labels(labels_file)
            walk_labels = [(s, e) for s, e, m in labels if m == "walk"]
            if not walk_labels:
                continue

            traj_dir = user_dir / "Trajectory"
            if not traj_dir.exists():
                continue

            # Load all .plt files for this user, sorted chronologically
            plt_files = sorted(traj_dir.glob("*.plt"))
            all_records: list[tuple[datetime, float, float]] = []
            for plt_path in plt_files:
                all_records.extend(_parse_plt(plt_path))

            if not all_records:
                continue

            all_records.sort(key=lambda x: x[0])

            for start_dt, end_dt in walk_labels:
                seg = _build_walk_segment(all_records, start_dt, end_dt)
                if seg is not None:
                    segments.append(seg)

        cls._segments = segments
        logger.info("GeolifeWalkLoader: loaded %d valid walk segments", len(segments))

        # Save binary cache as single concatenated array
        if segments:
            try:
                offsets = np.zeros(len(segments) + 1, dtype=np.int64)
                for i, seg in enumerate(segments):
                    offsets[i + 1] = offsets[i] + len(seg)
                flat = np.concatenate(segments)
                np.savez_compressed(cls._CACHE_PATH, data=flat, offsets=offsets)
                logger.info("GeolifeWalkLoader: saved cache to %s", cls._CACHE_PATH)
            except OSError as e:
                logger.warning("Could not save Geolife cache: %s", e)

        return cls._segments

    @classmethod
    def get_segment(cls, rng: np.random.Generator) -> np.ndarray | None:
        """Return a random walk segment, or None if no segments are available."""
        segs = cls.load()
        if not segs:
            return None
        idx = int(rng.integers(0, len(segs)))
        return segs[idx]


# -------------------------------------------------------------------------
# AMIT loader
# -------------------------------------------------------------------------

def _load_amit_csv(path: Path) -> dict[float, list[tuple[int, float, float]]]:
    """
    Parse one AMIT _TRJ.csv file.

    Returns a dict mapping vehicle_id -> list of (frame, center_x, center_y)
    for all motorcycle (class == 'm') vehicles.
    Coordinates are in metres (metric planar frame from UAV homography).

    Uses csv.reader with index-based access for ~2x speed vs DictReader.
    Column indices: 1=Frame, 2=Vehicle ID, 3=Front X, 4=Front Y,
                    5=Rear X, 6=Rear Y, 13=class
    """
    _COL_FRAME = 1
    _COL_VID = 2
    _COL_FX = 3
    _COL_FY = 4
    _COL_RX = 5
    _COL_RY = 6
    _COL_CLASS = 13

    vehicles: dict[float, list[tuple[int, float, float]]] = {}
    try:
        with path.open(newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                try:
                    if len(row) <= _COL_CLASS:
                        continue
                    if row[_COL_CLASS].strip() != _AMIT_CLASS_MOTORCYCLE:
                        continue
                    vid = float(row[_COL_VID])
                    frame = int(float(row[_COL_FRAME]))
                    cx = (float(row[_COL_FX]) + float(row[_COL_RX])) / 2.0
                    cy = (float(row[_COL_FY]) + float(row[_COL_RY])) / 2.0
                    if vid not in vehicles:
                        vehicles[vid] = []
                    vehicles[vid].append((frame, cx, cy))
                except (ValueError, IndexError):
                    continue
    except OSError as e:
        logger.warning("Skipping unreadable AMIT CSV: %s", e)
    return vehicles


def _build_motorcycle_track(
    frames_xy: list[tuple[int, float, float]],
) -> np.ndarray | None:
    """
    Build an interpolated 10 Hz (E, N) track from a list of (frame, cx, cy).

    AMIT is sampled at 5 Hz (Timestep = 0.2 s).  Linear interpolation is
    used to upsample to 10 Hz (insert one midpoint between each pair of
    consecutive frames).

    Returns a (N, 2) float64 array of (east, north) positions, or None if
    the track is too short or has missing frames.
    """
    frames_xy.sort(key=lambda x: x[0])

    if len(frames_xy) < _AMIT_MIN_FRAMES:
        return None

    # Check for large frame gaps (vehicle disappeared)
    frame_nums = [f for f, _, _ in frames_xy]
    gaps = [frame_nums[i + 1] - frame_nums[i] for i in range(len(frame_nums) - 1)]
    if any(g > 3 for g in gaps):  # > 3 frames = > 0.6 s missing
        return None

    xs = np.array([cx for _, cx, _ in frames_xy])
    ys = np.array([cy for _, _, cy in frames_xy])

    # ENU relative to track centroid
    cx_mean = float(np.mean(xs))
    cy_mean = float(np.mean(ys))
    east = xs - cx_mean
    north = ys - cy_mean

    # Check max displacement from centroid
    dist = np.sqrt(east ** 2 + north ** 2)
    if np.max(dist) > _WALK_MAX_DISPLACEMENT_M:
        return None

    # Linear interpolation from 5 Hz to 10 Hz
    east_10hz = np.empty(len(east) * 2 - 1)
    north_10hz = np.empty(len(north) * 2 - 1)
    for i in range(len(east) - 1):
        east_10hz[2 * i] = east[i]
        east_10hz[2 * i + 1] = (east[i] + east[i + 1]) / 2.0
        north_10hz[2 * i] = north[i]
        north_10hz[2 * i + 1] = (north[i] + north[i + 1]) / 2.0
    east_10hz[-1] = east[-1]
    north_10hz[-1] = north[-1]

    return np.column_stack([east_10hz, north_10hz])


class AMITMotorcycleLoader:
    """
    Loads motorcycle tracks from the AMIT dataset.

    AMIT (Asian Motorcycle Intersection Trajectory) contains UAV-captured
    trajectory data at 6 signalised urban intersections in Taiwan.  Vehicle
    positions are extracted from aerial video via homography projection into
    a metric planar coordinate system - they are NOT GPS measurements.

    This loader extracts tracks of class 'm' (motorcycle), computes the
    vehicle centre as the midpoint of the front and rear axle positions,
    centres each track at its own centroid, then upsamples from the native
    5 Hz rate to 10 Hz using linear interpolation.

    Linear interpolation is appropriate here because the 5 Hz native rate
    is already dense relative to the vehicle dynamics; the interpolation
    factor is only 2x and the trajectory is essentially straight or gently
    curved between consecutive frames.

    A binary cache (.npz) is stored alongside the dataset to avoid
    re-parsing 13+ million CSV rows on every test session.
    """

    _segments: list[np.ndarray] | None = None
    _CACHE_PATH = _AMIT_ROOT / "_cached_segments.npz"

    @classmethod
    def load(cls) -> list[np.ndarray]:
        """Load and cache all valid motorcycle tracks from A01-A06."""
        if cls._segments is not None:
            return cls._segments

        # Try loading from binary cache first (single concatenated array)
        if cls._CACHE_PATH.exists():
            try:
                data = np.load(cls._CACHE_PATH, allow_pickle=False)
                if "offsets" in data:
                    flat = data["data"]
                    offsets = data["offsets"]
                    cls._segments = [flat[offsets[i]:offsets[i + 1]] for i in range(len(offsets) - 1)]
                else:
                    # Legacy .npz format: individual arr_N arrays
                    keys = sorted(data.files, key=lambda s: int(s.split("_")[1]))
                    cls._segments = [data[k] for k in keys]
                logger.info("AMITMotorcycleLoader: loaded %d tracks from cache", len(cls._segments))
                return cls._segments
            except (OSError, ValueError):
                logger.warning("AMIT cache corrupt, re-parsing CSV files")

        if not _AMIT_ROOT.exists():
            logger.warning("AMIT dataset not found at %s", _AMIT_ROOT)
            cls._segments = []
            return cls._segments

        segments: list[np.ndarray] = []
        csv_files = sorted(_AMIT_ROOT.rglob("*_TRJ.csv"))

        for csv_path in csv_files:
            vehicles = _load_amit_csv(csv_path)
            for frames_xy in vehicles.values():
                track = _build_motorcycle_track(frames_xy)
                if track is not None:
                    segments.append(track)

        cls._segments = segments
        logger.info("AMITMotorcycleLoader: loaded %d valid motorcycle tracks", len(segments))

        # Save binary cache as single concatenated array (fast load)
        if segments:
            try:
                offsets = np.zeros(len(segments) + 1, dtype=np.int64)
                for i, seg in enumerate(segments):
                    offsets[i + 1] = offsets[i] + len(seg)
                flat = np.concatenate(segments)
                np.savez_compressed(cls._CACHE_PATH, data=flat, offsets=offsets)
                logger.info("AMITMotorcycleLoader: saved cache to %s", cls._CACHE_PATH)
            except OSError as e:
                logger.warning("Could not save AMIT cache: %s", e)

        return cls._segments

    @classmethod
    def get_segment(cls, rng: np.random.Generator) -> np.ndarray | None:
        """Return a random motorcycle track, or None if none are available."""
        segs = cls.load()
        if not segs:
            return None
        idx = int(rng.integers(0, len(segs)))
        return segs[idx]


# -------------------------------------------------------------------------
# Road-network motorcycle loader (OSMnx/NetworkX)
# -------------------------------------------------------------------------

_ROAD_GRAPH_PATH = _PROJECT_ROOT / "data" / "hcmc_roads.graphml"

# Minimum edge count for a usable random walk
_MIN_WALK_NODES = 20

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


class RoadNetworkMotorcycleLoader:
    """
    Generates motorcycle trajectories by performing random walks on a
    real OpenStreetMap road network graph.

    The road network is pre-downloaded as a GraphML file
    (``data/hcmc_roads.graphml``).  On first use the graph is loaded
    and cached at class level.

    For each trajectory the loader:
      1. Finds the nearest *driveable* node to the observer's lat/lon.
      2. Performs a random walk on the graph (random neighbor selection).
      3. Interpolates the walk path to 10 Hz using linear interpolation.
      4. Returns an (N, 2) NumPy array of (east, north) positions in
         an ENU frame centred on the observer.
    """

    _graph: nx.MultiDiGraph | None = None

    @classmethod
    def _load_graph(cls) -> nx.MultiDiGraph | None:
        """Load and cache the road network graph from GraphML."""
        if cls._graph is not None:
            return cls._graph
        if not _ROAD_GRAPH_PATH.exists():
            logger.warning("Road network not found at %s", _ROAD_GRAPH_PATH)
            return None
        try:
            cls._graph = nx.read_graphml(str(_ROAD_GRAPH_PATH))
            logger.info(
                "RoadNetworkMotorcycleLoader: loaded graph with %d nodes, %d edges",
                cls._graph.number_of_nodes(),
                cls._graph.number_of_edges(),
            )
        except (OSError, nx.NetworkXError) as e:
            logger.warning("Failed to load road network: %s", e)
            return None
        return cls._graph

    @classmethod
    def _find_nearest_start_node(
        cls, graph: nx.MultiDiGraph, lat: float, lon: float,
        rng: np.random.Generator | None = None,
    ) -> str | None:
        """Find a well-connected start node for a random walk.

        Strategy: collect all candidate nodes within a radius, then
        randomly select one (weighted by inverse distance) so each
        ENGAGE click picks a different starting intersection.

        Candidates must have ``out_degree >= 2`` (real intersection,
        not a dead-end).  Cascading radius fallback:
          1. out_degree >= 2 within 0.01° (~1 km)
          2. out_degree >= 2 within 0.05° (~5 km)
          3. out_degree > 0 within 0.05° (~5 km)

        Returns the node string ID or None.
        """
        if rng is None:
            rng = np.random.default_rng()

        def _pick_random(candidates: list[str]) -> str:
            """Weighted random selection: inversely proportional to distance²."""
            if len(candidates) == 1:
                return candidates[0]
            dists = []
            for n in candidates:
                d = float(graph.nodes[n]["y"]), float(graph.nodes[n]["x"])
                dists.append((d[0] - lat) ** 2 + (d[1] - lon) ** 2)
            weights = np.array([1.0 / max(d, 1e-12) for d in dists])
            weights /= weights.sum()
            idx = int(rng.choice(len(candidates), p=weights))
            return candidates[idx]

        # Pass 1: intersection within ~1 km
        candidates: list[str] = []
        max_d2_pass1 = 0.01 ** 2
        for node, data in graph.nodes(data=True):
            if graph.out_degree(node) < 2:
                continue
            nlat = float(data["y"])
            nlon = float(data["x"])
            d2 = (nlat - lat) ** 2 + (nlon - lon) ** 2
            if d2 <= max_d2_pass1:
                candidates.append(node)
        if candidates:
            return _pick_random(candidates)

        # Pass 2: intersection within ~5 km
        candidates = []
        max_d2_pass2 = 0.05 ** 2
        for node, data in graph.nodes(data=True):
            if graph.out_degree(node) < 2:
                continue
            nlat = float(data["y"])
            nlon = float(data["x"])
            d2 = (nlat - lat) ** 2 + (nlon - lon) ** 2
            if d2 <= max_d2_pass2:
                candidates.append(node)
        if candidates:
            return _pick_random(candidates)

        # Pass 3: any node with outgoing edges within ~5 km (fallback)
        candidates = []
        for node, data in graph.nodes(data=True):
            if graph.out_degree(node) == 0:
                continue
            nlat = float(data["y"])
            nlon = float(data["x"])
            d2 = (nlat - lat) ** 2 + (nlon - lon) ** 2
            if d2 <= max_d2_pass2:
                candidates.append(node)
        if candidates:
            return _pick_random(candidates)
        return None

    @classmethod
    def _random_walk(
        cls,
        graph: nx.MultiDiGraph,
        start_node: str,
        rng: np.random.Generator,
        max_steps: int = 300,
        min_nodes: int = 10,
    ) -> list[tuple[float, float, float]]:
        """
        Perform a random walk on the graph starting from *start_node*.

        Returns a list of ``(lat, lon, speed_kmh)`` for each visited node.
        At each step a random outgoing neighbor is chosen.  The walk stops
        when ``max_steps`` is reached, or when the walker is truly stuck
        (no outgoing unvisited neighbors within the full backtrack window).

        Dead-end handling: on hitting a dead end, backtrack through the
        *entire* path (not just the last 5 nodes) to find the nearest
        node with unvisited outgoing neighbors.  This prevents premature
        termination in dense urban grids where dead ends are common.

        If the walk produces fewer than *min_nodes* nodes, returns an
        empty list so callers can distinguish "too short" from "succeeded".
        """
        path: list[tuple[float, float, float]] = []
        node_ids: list[str] = []  # parallel list of graph node IDs
        current = start_node
        visited: set[str] = set()

        for _ in range(max_steps):
            visited.add(current)
            data = graph.nodes[current]
            lat = float(data["y"])
            lon = float(data["x"])

            speed_kmh = 30.0  # default for start node
            path.append((lat, lon, speed_kmh))
            node_ids.append(current)

            # Forward neighbors not yet visited
            neighbors = list(graph.neighbors(current))
            unvisited = [n for n in neighbors if n not in visited]

            if unvisited:
                next_node = unvisited[int(rng.integers(0, len(unvisited)))]
            else:
                # Dead end: backtrack through ALL past nodes (not just 5)
                # to find the nearest one with unvisited outgoing neighbors.
                next_node = None
                for idx in range(len(node_ids) - 1, -1, -1):
                    past_id = node_ids[idx]
                    past_unvisited = [
                        n for n in graph.neighbors(past_id) if n not in visited
                    ]
                    if past_unvisited:
                        next_node = past_unvisited[
                            int(rng.integers(0, len(past_unvisited)))
                        ]
                        break
                if next_node is None:
                    break  # truly stuck — no node in the entire path has unvisited neighbors

            # Get speed limit from the edge
            edge_data = graph.get_edge_data(current, next_node)
            if edge_data:
                # For DiGraph, get_edge_data returns the attr dict directly.
                # For MultiDiGraph, it returns {edge_key: attr_dict}.
                if isinstance(edge_data, dict) and all(isinstance(v, dict) for v in edge_data.values()):
                    # MultiDiGraph: {0: {'maxspeed': '50', ...}}
                    first_edge = next(iter(edge_data.values()))
                else:
                    # DiGraph: {'maxspeed': '50', ...}
                    first_edge = edge_data
                raw_speed = first_edge.get("maxspeed", 30.0)
                try:
                    speed_kmh = float(raw_speed)
                except (TypeError, ValueError):
                    speed_kmh = 30.0
                # Update speed on current node (the edge we're about to take)
                path[-1] = (lat, lon, speed_kmh)

            current = next_node

        if len(path) < min_nodes:
            return []
        return path

    @classmethod
    def _interpolate_walk(
        cls,
        walk: list[tuple[float, float, float]],
        observer_lat: float,
        observer_lon: float,
        target_hz: float = _TARGET_HZ,
    ) -> np.ndarray | None:
        """
        Interpolate a random walk to uniform 10 Hz sampling.

        Each edge between consecutive nodes is traversed at the speed
        limit of the outgoing edge.  The resulting positions are
        converted to ENU (metres) relative to *observer*.

        Returns an (N, 2) NumPy array of (east, north) or None if
        the walk is too short.
        """
        if len(walk) < 2:
            return None

        dt = 1.0 / target_hz
        positions: list[tuple[float, float]] = []

        for i in range(len(walk) - 1):
            lat1, lon1, speed_kmh = walk[i]
            lat2, lon2, _ = walk[i + 1]

            # Compute edge length in metres (haversine)
            edge_m = _haversine_m(lat1, lon1, lat2, lon2)

            # Speed in m/s
            speed_ms = max(speed_kmh / 3.6, 0.5)  # minimum 0.5 m/s

            # Time to traverse this edge
            edge_time = edge_m / speed_ms

            # Number of interpolated points for this edge
            n_steps = max(1, round(edge_time / dt))

            for s in range(n_steps):
                frac = s / n_steps
                lat_i = lat1 + frac * (lat2 - lat1)
                lon_i = lon1 + frac * (lon2 - lon1)
                east, north = _lat_lon_to_enu(lat_i, lon_i, observer_lat, observer_lon)
                positions.append((east, north))

        # Add final point
        lat_f, lon_f, _ = walk[-1]
        east_f, north_f = _lat_lon_to_enu(lat_f, lon_f, observer_lat, observer_lon)
        positions.append((east_f, north_f))

        if len(positions) < _MIN_WALK_NODES:
            return None

        return np.array(positions, dtype=np.float64)

    @classmethod
    def get_segment(
        cls,
        rng: np.random.Generator,
        observer_lat: float = 10.7709,
        observer_lon: float = 106.7030,
    ) -> np.ndarray | None:
        """
        Generate a random road-network motorcycle trajectory.

        Returns an (N, 2) NumPy array of (east, north) positions in
        an ENU frame centred on the observer, or None if the road
        network is unavailable or the walk is too short.
        """
        graph = cls._load_graph()
        if graph is None:
            return None

        start_node = cls._find_nearest_start_node(graph, observer_lat, observer_lon, rng=rng)
        if start_node is None:
            logger.warning(
                "RoadNetworkMotorcycleLoader: no suitable start node near observer "
                "(%.4f, %.4f)", observer_lat, observer_lon,
            )
            return None

        sdata = graph.nodes[start_node]
        slat, slon = float(sdata["y"]), float(sdata["x"])
        out_deg = graph.out_degree(start_node)
        dist_m = _haversine_m(observer_lat, observer_lon, slat, slon)
        logger.info(
            "RoadNetworkMotorcycleLoader: start node %s at (%.6f, %.6f), "
            "out_degree=%d, distance=%.0fm from observer",
            start_node, slat, slon, out_deg, dist_m,
        )

        walk = cls._random_walk(graph, start_node, rng)
        logger.info("RoadNetworkMotorcycleLoader: walk produced %d nodes", len(walk))
        if not walk:
            logger.warning("RoadNetworkMotorcycleLoader: walk too short (< min_nodes)")
            return None

        segment = cls._interpolate_walk(walk, observer_lat, observer_lon)
        if segment is None:
            logger.warning("RoadNetworkMotorcycleLoader: interpolation produced too few points")
            return None

        logger.info(
            "RoadNetworkMotorcycleLoader: segment shape %s, "
            "E range [%.1f, %.1f]m, N range [%.1f, %.1f]m",
            segment.shape,
            segment[:, 0].min(), segment[:, 0].max(),
            segment[:, 1].min(), segment[:, 1].max(),
        )
        return segment
