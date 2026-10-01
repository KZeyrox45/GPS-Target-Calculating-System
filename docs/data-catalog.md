# Data Catalog — Datasets in `data/`

Generated: 2025-11-23. Source: grep coverage of `backend/`, `frontend/`, `tests/` + `git ls-files` + `git lfs ls-files`.

## Active Datasets (Used in Production)

| Dataset | Path | Size | Usage |
|---------|------|------|-------|
| Geolife Trajectories 1.3 | `data/Geolife Trajectories 1.3/` | 1.7 GB (18,670 `.plt` + 69 `labels.txt`) | `GeolifeWalkLoader` — pedestrian realistic mode, 252 valid walk segments |
| Geolife cache | `data/Geolife Trajectories 1.3/Data/_cached_segments.npz` | 4.1 MB (LFS) | Cached segments for fast load |
| HCMC Road Network | `data/hcmc_roads.graphml` | 103 MB (LFS) | `RoadNetworkMotorcycleLoader` — motorcycle default (both synthetic + realistic), 337K nodes |

## Orphaned / Reference-Only (Not Used at Runtime)

| Dataset | Size | Status | Recommendation |
|---------|------|--------|----------------|
| AMIT (6 intersections, 63 CSV + JPG/DOCX/PDF) | 1.1 GB | Loader class exists but engine never instantiates it — road network replaced it | Keep or remove per supervisor decision; if kept, keep the **entire** dataset together. To slim: keep only `_TRJ.csv` + `_cached_segments.npz`, remove `*_background.jpg`, `*_linemarking.csv`, `*_signal.csv`, `*.docx` auxiliaries (never read) |
| arXiv-2103.13313v1 (DJI Matrice 100 paper) | 32 MB | Reference only — kinematic limits `V_MAX_H 15 m/s` cited in code comment, paper not parsed | Move to `docs/references/` or keep as-is; not needed for runtime |
| arXiv-2007.08463v1 (openDD paper) | 2.0 MB | Reference only — not imported anywhere | Same as above |
| UAVTrajectory.py (BlueSky template) | 7 KB | Never imported, hardcoded Windows path, requires `bluesky` not in deps | Remove or move to `docs/snippets/` as example |

## Recommendation for GitHub Push

- **Keep as tracked:** Geolife + HCMC road network + their LFS caches (required for `uv run pytest` offline).
- **Decide per dataset:** AMIT — keep the full folder if you want reviewers to experiment, or prune to save 1.1 GB and provide as a separate Release asset.
- **Move or prune:** arXiv bundles → `docs/references/`; `UAVTrajectory.py` → remove.

> Note: Geolife `.plt` files (18,670) are stored as regular Git blobs (1.7 GB), not LFS. This makes clones heavy. Adding `*.plt filter=lfs` to `.gitattributes` would fix future commits but requires history migration for existing files.

## Evidence

Simulation evidence CSV/JSON from `report-weekly/Images/sim/` has been copied to `docs/evidence/` (18 CSV + 2 JSON) for GitHub-tracked provenance. `Simulation_Results/` remains local-only (simulation comparison traces).
