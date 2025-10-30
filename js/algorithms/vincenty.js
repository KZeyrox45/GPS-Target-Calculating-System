// vincenty.js
'use strict';

const a = 6378.137; // bán trục lớn (km)
const f = 1 / 298.257223563; // dẹt của Trái Đất
const b = a * (1 - f);
const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;

/**
 * Vincenty Inverse (tính ngược) không cần, nhưng Forward (tính tiến) để tìm điểm đích
 */
function vincenty(lat1, lon1, azimuth, distanceKm) {
  const φ1 = lat1 * DEG_TO_RAD;
  const λ1 = lon1 * DEG_TO_RAD;
  const α1 = azimuth * DEG_TO_RAD;
  const s = distanceKm;

  const sinα1 = Math.sin(α1);
  const cosα1 = Math.cos(α1);

  const tanU1 = (1 - f) * Math.tan(φ1);
  const cosU1 = 1 / Math.sqrt(1 + tanU1 * tanU1);
  const sinU1 = tanU1 * cosU1;

  const σ1 = Math.atan2(tanU1, cosα1);
  const sinα = cosU1 * sinα1;
  const cosSqα = 1 - sinα * sinα;
  const uSq = cosSqα * (a * a - b * b) / (b * b);
  const A = 1 + uSq / 16384 * (4096 + uSq * (-768 + uSq * (320 - 175 * uSq)));
  const B = uSq / 1024 * (256 + uSq * (-128 + uSq * (74 - 47 * uSq)));

  let σ = s / (b * A);
  let σʹ, cos2σm, sinσ, cosσ;

  do {
    cos2σm = Math.cos(2 * σ1 + σ);
    sinσ = Math.sin(σ);
    cosσ = Math.cos(σ);
    const Δσ = B * sinσ * (cos2σm + B / 4 * (cosσ * (-1 + 2 * cos2σm * cos2σm) -
      B / 6 * cos2σm * (-3 + 4 * sinσ * sinσ) * (-3 + 4 * cos2σm * cos2σm)));
    σʹ = σ;
    σ = s / (b * A) + Δσ;
  } while (Math.abs(σ - σʹ) > 1e-12);

  const φ2 = Math.atan2(sinU1 * cosσ + cosU1 * sinσ * cosα1,
    (1 - f) * Math.sqrt(sinα * sinα + (sinU1 * sinσ - cosU1 * cosσ * cosα1) * (sinU1 * sinσ - cosU1 * cosσ * cosα1)));

  const λ = Math.atan2(sinσ * sinα1, cosU1 * cosσ - sinU1 * sinσ * cosα1);
  const C = f / 16 * cosSqα * (4 + f * (4 - 3 * cosSqα));
  const L = λ - (1 - C) * f * sinα * (σ + C * sinσ * (cos2σm + C * cosσ * (-1 + 2 * cos2σm * cos2σm)));

  const λ2 = ((λ1 + L + 3 * Math.PI) % (2 * Math.PI)) - Math.PI;

  return {
    lat: φ2 * RAD_TO_DEG,
    lon: λ2 * RAD_TO_DEG
  };
}

if (typeof window !== 'undefined') {
  window.Algorithms = window.Algorithms || {};
  window.Algorithms.vincenty = vincenty;
}