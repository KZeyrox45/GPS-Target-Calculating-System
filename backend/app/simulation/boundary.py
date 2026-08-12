"""
boundary.py - Simulation Area Boundary Constraint
==================================================
Keeps simulated targets within a circular region centred on the observer.

Uses soft potential-field repulsion: when a target approaches the boundary,
its heading is gradually biased toward the interior and its speed is reduced.
This avoids the unnatural "billiard-ball oscillation" caused by hard
specular reflection (the previous implementation).

Why a circular boundary?
  - Simple, computationally trivial (one distance check per step).
  - Avoids the hard-edge artefact of a rectangular box (corners cause
    unnatural clustering).
  - Radius can be set to match the laser rangefinder's maximum reliable
    range (default 400 m), so targets always stay within sensor coverage.

Reference: Helbing & Molnár (1995) Social Force Model uses exponential
repulsion from obstacles.  Krajzewicz et al. (2012) SUMO uses soft speed
reduction near boundaries.
"""

import math


class SimulationBoundary:
    """
    Soft circular boundary centred at (0, 0) in ENU metres.

    When a target enters the repulsion zone (80% of radius), its heading
    is gradually biased toward the centre and its speed is reduced.  If the
    target still exceeds the boundary, it is clamped to the surface with a
    gentle heading correction (not hard specular reflection).

    Usage::

        boundary = SimulationBoundary(radius_m=400.0)
        east, north, heading = boundary.constrain(east, north, heading)
    """

    def __init__(self, radius_m: float = 400.0):
        """
        Args:
            radius_m: Maximum allowed distance from observer (metres).
                      Should be <= laser rangefinder max range.
        """
        if radius_m <= 0:
            raise ValueError(f"radius_m must be positive, got {radius_m}")
        self.radius_m = radius_m
        self._soft_zone = 0.8 * radius_m  # repulsion starts at 80% of radius

    def constrain(
        self,
        east: float,
        north: float,
        heading: float,
    ) -> tuple[float, float, float]:
        """
        Apply soft boundary constraint.

        Args:
            east:    Current East position (metres).
            north:   Current North position (metres).
            heading: Current heading in radians (measured from North, CW).

        Returns:
            (east, north, heading) - possibly corrected toward interior.
        """
        dist = math.sqrt(east ** 2 + north ** 2)

        if dist <= self._soft_zone:
            return east, north, heading  # well inside - no action needed

        # --- Compute repulsion strength (0 at soft_zone, 1 at boundary) ---
        repulsion = (dist - self._soft_zone) / (self.radius_m - self._soft_zone)
        repulsion = min(repulsion, 1.0)

        # --- Bias heading toward centre ---
        # Direction from current position toward origin (interior)
        to_center = math.atan2(-east, -north)  # heading convention: from North CW

        # Angular difference (shortest path)
        diff = (to_center - heading + math.pi) % (2 * math.pi) - math.pi

        # Apply partial heading correction (stronger near boundary)
        heading_correction = 0.4 * repulsion * diff
        heading = heading + heading_correction

        # --- Clamp position if beyond boundary ---
        if dist > self.radius_m:
            scale = self.radius_m / dist
            east  = east  * scale
            north = north * scale

        return east, north, heading
