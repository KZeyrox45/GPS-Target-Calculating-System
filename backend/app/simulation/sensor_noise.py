"""
sensor_noise.py — Realistic Sensor Noise Models
================================================
Provides random noise generators that simulate real-world sensor imperfections.
These are used exclusively by the simulation engine — real hardware bypasses this.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class NoiseConfig:
    """
    Noise parameters for each sensor modality.
    All values are 1-sigma (standard deviation).
    """
    # GPS observer position noise
    gps_lat_sigma_m: float = 5.0
    gps_lon_sigma_m: float = 5.0
    gps_alt_sigma_m: float = 10.0

    # IMU / compass angular noise
    compass_azimuth_sigma_deg: float = 0.3
    compass_elevation_sigma_deg: float = 0.2

    # Laser rangefinder noise
    laser_range_sigma_m: float = 0.5


class SensorNoiseModel:
    """
    Generates correlated, realistic sensor noise for simulation.

    Uses a seeded numpy RNG for reproducible runs.
    """

    # Preset configurations per target type
    PRESETS = {
        "pedestrian": NoiseConfig(
            gps_lat_sigma_m=5.0, gps_lon_sigma_m=5.0, gps_alt_sigma_m=8.0,
            compass_azimuth_sigma_deg=0.3, compass_elevation_sigma_deg=0.2,
            laser_range_sigma_m=0.3,
        ),
        "motorcycle": NoiseConfig(
            gps_lat_sigma_m=5.0, gps_lon_sigma_m=5.0, gps_alt_sigma_m=8.0,
            compass_azimuth_sigma_deg=0.4, compass_elevation_sigma_deg=0.25,
            laser_range_sigma_m=0.5,
        ),
        "drone": NoiseConfig(
            gps_lat_sigma_m=5.0, gps_lon_sigma_m=5.0, gps_alt_sigma_m=8.0,
            compass_azimuth_sigma_deg=0.5, compass_elevation_sigma_deg=0.4,
            laser_range_sigma_m=1.0,
        ),
    }

    def __init__(self, config: NoiseConfig | None = None, seed: int | None = None):
        self.config = config or NoiseConfig()
        self.rng = np.random.default_rng(seed)

    @classmethod
    def from_target_type(cls, target_type: str, seed: int | None = None) -> "SensorNoiseModel":
        config = cls.PRESETS.get(target_type, NoiseConfig())
        return cls(config=config, seed=seed)

    def apply_gps_noise(self, lat_m: float, lon_m: float, alt_m: float):
        """Add Gaussian noise to observer GPS position (in metres)."""
        return (
            lat_m + self.rng.normal(0, self.config.gps_lat_sigma_m),
            lon_m + self.rng.normal(0, self.config.gps_lon_sigma_m),
            alt_m + self.rng.normal(0, self.config.gps_alt_sigma_m),
        )

    def apply_azimuth_noise(self, azimuth_deg: float) -> float:
        """Add Gaussian noise to compass azimuth measurement."""
        return azimuth_deg + self.rng.normal(0, self.config.compass_azimuth_sigma_deg)

    def apply_elevation_noise(self, elevation_deg: float) -> float:
        """Add Gaussian noise to IMU elevation measurement."""
        return elevation_deg + self.rng.normal(0, self.config.compass_elevation_sigma_deg)

    def apply_range_noise(self, range_m: float) -> float:
        """Add Gaussian noise to laser rangefinder measurement."""
        return max(0.1, range_m + self.rng.normal(0, self.config.laser_range_sigma_m))
