"""
boundary.py — Simulation Area Boundary Constraint
==================================================
Keeps simulated targets within a circular region centred on the observer.
Targets that reach the boundary are reflected back (specular reflection on
the heading angle), preventing the unbounded drift that caused objects to
"walk through walls" in the original implementation.

Why a circular boundary?
  - Simple, computationally trivial (one distance check per step).
  - Avoids the hard-edge artefact of a rectangular box (corners cause
    unnatural clustering).
  - Radius can be set to match the laser rangefinder's maximum reliable
    range (default 500 m), so targets always stay within sensor coverage.
"""

import math


class SimulationBoundary:
    """
    Soft circular boundary centred at (0, 0) in ENU metres.

    When a trajectory step would place the target outside `radius_m`, the
    target is nudged back to the boundary surface and its heading is
    reflected away from the boundary (like light reflecting off a mirror).

    Usage::

        boundary = SimulationBoundary(radius_m=400.0)
        east, north, heading = boundary.constrain(east, north, heading)
    """

    def __init__(self, radius_m: float = 400.0):
        """
        Args:
            radius_m: Maximum allowed distance from observer (metres).
                      Should be ≤ laser rangefinder max range.
        """
        if radius_m <= 0:
            raise ValueError(f"radius_m must be positive, got {radius_m}")
        self.radius_m = radius_m

    def constrain(
        self,
        east: float,
        north: float,
        heading: float,
    ) -> tuple[float, float, float]:
        """
        Apply boundary constraint.

        Args:
            east:    Current East position (metres).
            north:   Current North position (metres).
            heading: Current heading in radians (measured from North, CW).

        Returns:
            (east, north, heading) — possibly reflected back inside boundary.
        """
        dist = math.sqrt(east ** 2 + north ** 2)

        if dist <= self.radius_m:
            return east, north, heading  # inside — no action needed

        # --- 1. Clamp position back onto the boundary circle ---
        scale = self.radius_m / dist
        east  = east  * scale
        north = north * scale

        # --- 2. Reflect heading away from the boundary ---
        #
        # The outward normal at (east, north) on the circle points in the
        # radial direction: n̂ = (east, north) / dist
        #
        # The heading vector in ENU is: v = (sin(h), cos(h))  [East, North]
        #
        # Reflected heading vector: v' = v - 2·(v·n̂)·n̂
        #
        nx = east  / self.radius_m   # outward normal x (East)
        ny = north / self.radius_m   # outward normal y (North)

        vx = math.sin(heading)   # heading vector East component
        vy = math.cos(heading)   # heading vector North component

        dot = vx * nx + vy * ny  # projection onto outward normal
        rx  = vx - 2 * dot * nx  # reflected East
        ry  = vy - 2 * dot * ny  # reflected North

        new_heading = math.atan2(rx, ry)  # back to heading convention
        return east, north, new_heading
