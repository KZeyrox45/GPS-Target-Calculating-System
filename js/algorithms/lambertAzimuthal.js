// lambertAzimuthal.js
'use strict';

const EARTH_RADIUS_KM = 6371.0;
const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;

/**
 * Lambert Azimuthal Equal-Area: dùng để tính toán trên bản đồ phẳng
 */
function lambertAzimuthal(lat1, lon1, azimuth, distanceKm) {
  const φ1 = lat1 * DEG_TO_RAD;
  const λ1 = lon1 * DEG_TO_RAD;
  const θ = azimuth * DEG_TO_RAD;

  // Khoảng cách trên bản đồ phẳng
  const ρ = 2 * EARTH_RADIUS_KM * Math.asin(distanceKm / (2 * EARTH_RADIUS_KM));

  // Tính tọa độ phẳng
  const x = ρ * Math.sin(θ);
  const y = ρ * Math.cos(θ);

  // Chiếu ngược về tọa độ cầu
  const sinφ1 = Math.sin(φ1);
  const cosφ1 = Math.cos(φ1);

  const c = Math.sqrt(x * x + y * y);
  const sinc = Math.sin(c / EARTH_RADIUS_KM);
  const cosc = Math.cos(c / EARTH_RADIUS_KM);

  const φ2 = Math.asin(cosc * sinφ1 + (y * sinc * cosφ1) / c);
  const λ2 = λ1 + Math.atan2(x * sinc, c * cosc * cosφ1 - y * sinc * sinφ1);

  return {
    lat: φ2 * RAD_TO_DEG,
    lon: ((λ2 * RAD_TO_DEG + 540) % 360) - 180
  };
}

if (typeof window !== 'undefined') {
  window.Algorithms = window.Algorithms || {};
  window.Algorithms.lambertAzimuthal = lambertAzimuthal;
}