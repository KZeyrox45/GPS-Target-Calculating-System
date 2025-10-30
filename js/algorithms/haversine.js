// haversine.js
'use strict';

const EARTH_RADIUS_KM = 6371.0;
const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;

/**
 * Tính tọa độ điểm đích bằng công thức Haversine
 */
function haversine(lat1, lon1, azimuth, distanceKm) {
  const φ1 = lat1 * DEG_TO_RAD;
  const λ1 = lon1 * DEG_TO_RAD;
  const θ = azimuth * DEG_TO_RAD;
  const δ = distanceKm / EARTH_RADIUS_KM;

  const φ2 = Math.asin(
    Math.sin(φ1) * Math.cos(δ) +
    Math.cos(φ1) * Math.sin(δ) * Math.cos(θ)
  );

  const λ2 = λ1 + Math.atan2(
    Math.sin(θ) * Math.sin(δ) * Math.cos(φ1),
    Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2)
  );

  return {
    lat: φ2 * RAD_TO_DEG,
    lon: ((λ2 * RAD_TO_DEG + 540) % 360) - 180
  };
}

// Export cho browser
if (typeof window !== 'undefined') {
  window.Algorithms = window.Algorithms || {};
  window.Algorithms.haversine = haversine;
}