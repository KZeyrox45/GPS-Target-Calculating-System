// equirectangular.js
'use strict';

const EARTH_RADIUS_KM = 6371.0;
const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;

/**
 * Equirectangular Approximation (nhanh, gần đúng cho khoảng cách ngắn < 10km)
 */
function equirectangular(lat1, lon1, azimuth, distanceKm) {
  const φ1 = lat1 * DEG_TO_RAD;
  const λ1 = lon1 * DEG_TO_RAD;
  const θ = azimuth * DEG_TO_RAD;

  const R = EARTH_RADIUS_KM;
  const Δφ = (distanceKm * Math.cos(θ)) / R;
  const Δλ = (distanceKm * Math.sin(θ)) / (R * Math.cos(φ1));

  const φ2 = φ1 + Δφ;
  const λ2 = λ1 + Δλ;

  return {
    lat: φ2 * RAD_TO_DEG,
    lon: λ2 * RAD_TO_DEG
  };
}

if (typeof window !== 'undefined') {
  window.Algorithms = window.Algorithms || {};
  window.Algorithms.equirectangular = equirectangular;
}