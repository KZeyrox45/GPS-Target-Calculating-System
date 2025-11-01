/**
 * COORDINATE CALCULATOR MODULE
 * ============================
 * Core logic cho việc tính toán tọa độ mục tiêu
 * 
 * Chức năng chính:
 * - Chuyển đổi DMS ↔ Decimal
 * - Tính toán tọa độ mục tiêu từ azimuth + distance (Spherical/Haversine) và Ellipsoid (Vincenty)
 * - Validation dữ liệu đầu vào
 * - Tính khoảng cách giữa 2 điểm
 */

'use strict';

// ==================== CONSTANTS ====================

/**
 * Bán kính Trái Đất (km)
 * Sử dụng mean radius theo IUGG (International Union of Geodesy and Geophysics)
 */
const EARTH_RADIUS_KM = 6371.0;

/** WGS-84 ellipsoid params for Vincenty */
const WGS84 = {
  a: 6378137.0,                 // semi-major axis (m)
  f: 1 / 298.257223563           // flattening
};
WGS84.b = WGS84.a * (1 - WGS84.f);

/**
 * Hệ số chuyển đổi giữa Degrees và Radians
 */
const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;

/**
 * Giới hạn tọa độ
 */
const LAT_MIN = -90;
const LAT_MAX = 90;
const LON_MIN = -180;
const LON_MAX = 180;
const AZIMUTH_MIN = 0;
const AZIMUTH_MAX = 360;

// ==================== COORDINATE CONVERSION ====================

/**
 * Chuyển đổi tọa độ từ DMS (Degrees Minutes Seconds) sang Decimal Degrees
 * 
 * Công thức: decimal = degrees + (minutes / 60) + (seconds / 3600)
 * 
 * @param {number} degrees - Độ (có thể âm cho Nam/Tây)
 * @param {number} minutes - Phút (0-59)
 * @param {number} seconds - Giây (0-59.999)
 * @returns {number} Tọa độ dạng thập phân
 * 
 * @example
 * const lat = dmsToDecimal(10, 45, 45.44);
 * console.log(lat); // Output: 10.762622
 */
function dmsToDecimal(degrees, minutes, seconds) {
  // Xử lý trường hợp degrees âm (Nam hoặc Tây)
  const sign = degrees < 0 ? -1 : 1;
  const absDegrees = Math.abs(degrees);
  
  // Tính toán decimal
  const decimal = absDegrees + (minutes / 60) + (seconds / 3600);
  
  return sign * decimal;
}

/**
 * Chuyển đổi tọa độ từ Decimal Degrees sang DMS
 * 
 * @param {number} decimal - Tọa độ thập phân
 * @returns {object} Object chứa {degrees, minutes, seconds}
 * 
 * @example
 * const dms = decimalToDMS(10.762622);
 * console.log(dms); // {degrees: 10, minutes: 45, seconds: 45.44}
 */
function decimalToDMS(decimal) {
  // Xác định dấu
  const sign = decimal < 0 ? -1 : 1;
  const absolute = Math.abs(decimal);
  
  // Tính degrees (phần nguyên)
  const degrees = Math.floor(absolute);
  
  // Tính minutes
  const minutesFloat = (absolute - degrees) * 60;
  const minutes = Math.floor(minutesFloat);
  
  // Tính seconds
  const seconds = (minutesFloat - minutes) * 60;
  
  return {
    degrees: sign * degrees,
    minutes: minutes,
    seconds: parseFloat(seconds.toFixed(2))
  };
}

// ==================== GEODESIC CALCULATIONS ====================

/**
 * Spherical destination (current Phase 1 algorithm)
 */
function sphericalDestination(lat, lon, azimuthDeg, distanceKm) {
  const lat1 = lat * DEG_TO_RAD;
  const lon1 = lon * DEG_TO_RAD;
  const bearing = azimuthDeg * DEG_TO_RAD;
  const delta = distanceKm / EARTH_RADIUS_KM;
  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(delta) +
    Math.cos(lat1) * Math.sin(delta) * Math.cos(bearing)
  );
  const lon2 = lon1 + Math.atan2(
    Math.sin(bearing) * Math.sin(delta) * Math.cos(lat1),
    Math.cos(delta) - Math.sin(lat1) * Math.sin(lat2)
  );
  const targetLat = lat2 * RAD_TO_DEG;
  let targetLon = lon2 * RAD_TO_DEG;
  targetLon = ((targetLon + 540) % 360) - 180;
  return { lat: targetLat, lon: targetLon };
}

/**
 * Vincenty Direct (ellipsoid WGS-84)
 * Returns destination point given start lat, lon, initial bearing and distance.
 * Distance in km; internally converted to meters.
 */
function vincentyDestination(lat, lon, azimuthDeg, distanceKm) {
  const a = WGS84.a, b = WGS84.b, f = WGS84.f;
  const φ1 = lat * DEG_TO_RAD;
  const λ1 = lon * DEG_TO_RAD;
  const α1 = azimuthDeg * DEG_TO_RAD;
  const s = distanceKm * 1000.0;

  const sinα1 = Math.sin(α1), cosα1 = Math.cos(α1);
  const tanU1 = (1 - f) * Math.tan(φ1);
  const cosU1 = 1 / Math.sqrt(1 + tanU1 * tanU1);
  const sinU1 = tanU1 * cosU1;
  const σ1 = Math.atan2(tanU1, cosα1);
  const sinα = cosU1 * sinα1;
  const cos2α = 1 - sinα * sinα;
  const u2 = cos2α * (a*a - b*b) / (b*b);
  const A = 1 + (u2/16384) * (4096 + u2 * (-768 + u2 * (320 - 175*u2)));
  const B = (u2/1024) * (256 + u2 * (-128 + u2 * (74 - 47*u2)));

  let σ = s / (b * A);
  let σPrev;
  let cos2σm, sinσ, cosσ;
  const MAX_ITERS = 200;
  let iter = 0;
  do {
    cos2σm = Math.cos(2 * σ1 + σ);
    sinσ = Math.sin(σ);
    cosσ = Math.cos(σ);
    const Δσ = B * sinσ * (
      cos2σm + (B/4) * (
        cosσ * (-1 + 2 * cos2σm * cos2σm) -
        (B/6) * cos2σm * (-3 + 4 * sinσ * sinσ) * (-3 + 4 * cos2σm * cos2σm)
      )
    );
    σPrev = σ;
    σ = (s / (b * A)) + Δσ;
  } while (Math.abs(σ - σPrev) > 1e-12 && ++iter < MAX_ITERS);

  // Compute destination coordinates
  const tmp = sinU1 * sinσ - cosU1 * cosσ * cosα1;
  const φ2 = Math.atan2(
    sinU1 * cosσ + cosU1 * sinσ * cosα1,
    (1 - f) * Math.sqrt(sinα * sinα + tmp * tmp)
  );
  const λ = Math.atan2(
    sinσ * sinα1,
    cosU1 * cosσ - sinU1 * sinσ * cosα1
  );
  const C = (f / 16) * (cos2α) * (4 + f * (4 - 3 * cos2α));
  const L = λ - (1 - C) * f * sinα * (
    σ + C * sinσ * (cos2σm + C * cosσ * (-1 + 2 * cos2σm * cos2σm))
  );
  let λ2 = λ1 + L;

  // Normalize longitude to [-π, π]
  λ2 = ((λ2 + 3 * Math.PI) % (2 * Math.PI)) - Math.PI;

  return { lat: φ2 * RAD_TO_DEG, lon: λ2 * RAD_TO_DEG };
}

/**
 * Tính tọa độ điểm đích (destination point) sử dụng công thức Haversine
 * 
 * Công thức này tính toán trên mô hình cầu đơn giản của Trái Đất.
 * Phù hợp cho khoảng cách ngắn (< 100km) với độ chính xác chấp nhận được.
 * 
 * Công thức:
 * δ = d/R (angular distance)
 * φ₂ = asin(sin φ₁ ⋅ cos δ + cos φ₁ ⋅ sin δ ⋅ cos θ)
 * λ₂ = λ₁ + atan2(sin θ ⋅ sin δ ⋅ cos φ₁, cos δ − sin φ₁ ⋅ sin φ₂)
 * 
 * @param {number} lat - Vĩ độ điểm xuất phát (decimal degrees)
 * @param {number} lon - Kinh độ điểm xuất phát (decimal degrees)
 * @param {number} azimuthDeg - Góc phương vị từ Bắc (degrees, 0-360)
 * @param {number} distanceKm - Khoảng cách (kilometers)
 * @returns {object} Object chứa {lat, lon} của điểm đích
 * 
 * @example
 * const target = calculateTargetCoordinate(10.762622, 106.660172, 45, 2.5);
 * console.log(target); // {lat: 10.778945, lon: 106.677834}
 */
// Backwards-compatible wrapper: if algo omitted, use spherical.
function calculateTargetCoordinate(lat, lon, azimuthDeg, distanceKm, algo = 'spherical-haversine') {
  const fn = algo === 'vincenty' ? vincentyDestination : sphericalDestination;
  return fn(lat, lon, azimuthDeg, distanceKm);
}

/**
 * Tính khoảng cách giữa 2 điểm trên mặt cầu sử dụng công thức Haversine
 * 
 * Công thức:
 * a = sin²(Δφ/2) + cos φ₁ ⋅ cos φ₂ ⋅ sin²(Δλ/2)
 * c = 2 ⋅ atan2(√a, √(1−a))
 * d = R ⋅ c
 * 
 * Dùng để validation và kiểm tra độ chính xác của tính toán
 * 
 * @param {number} lat1 - Vĩ độ điểm 1 (degrees)
 * @param {number} lon1 - Kinh độ điểm 1 (degrees)
 * @param {number} lat2 - Vĩ độ điểm 2 (degrees)
 * @param {number} lon2 - Kinh độ điểm 2 (degrees)
 * @returns {number} Khoảng cách (kilometers)
 * 
 * @example
 * const dist = calculateDistance(10.762622, 106.660172, 10.778945, 106.677834);
 * console.log(dist.toFixed(2)); // ~2.50 km
 */
function calculateDistance(lat1, lon1, lat2, lon2) {
  // Chuyển sang radian
  const φ1 = lat1 * DEG_TO_RAD;
  const φ2 = lat2 * DEG_TO_RAD;
  const Δφ = (lat2 - lat1) * DEG_TO_RAD;
  const Δλ = (lon2 - lon1) * DEG_TO_RAD;
  
  // Công thức Haversine
  const a = 
    Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) *
    Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  
  // Khoảng cách
  const distance = EARTH_RADIUS_KM * c;
  
  return distance;
}

/**
 * Tính góc bearing (phương vị) từ điểm 1 đến điểm 2
 * 
 * @param {number} lat1 - Vĩ độ điểm 1 (degrees)
 * @param {number} lon1 - Kinh độ điểm 1 (degrees)
 * @param {number} lat2 - Vĩ độ điểm 2 (degrees)
 * @param {number} lon2 - Kinh độ điểm 2 (degrees)
 * @returns {number} Góc bearing (degrees, 0-360)
 */
function calculateBearing(lat1, lon1, lat2, lon2) {
  const φ1 = lat1 * DEG_TO_RAD;
  const φ2 = lat2 * DEG_TO_RAD;
  const Δλ = (lon2 - lon1) * DEG_TO_RAD;
  
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) -
            Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  
  const θ = Math.atan2(y, x);
  const bearing = (θ * RAD_TO_DEG + 360) % 360;
  
  return bearing;
}

// ==================== VALIDATION ====================

/**
 * Kiểm tra tính hợp lệ của dữ liệu đầu vào
 * 
 * Validation rules:
 * - Vĩ độ: -90 đến 90
 * - Kinh độ: -180 đến 180
 * - Azimuth: 0 đến 360
 * - Distance: > 0
 * - Warning: Distance > 100 km (độ chính xác giảm)
 * 
 * @param {object} data - Object chứa {lat, lon, azimuth, distance}
 * @returns {string} Thông báo lỗi hoặc chuỗi rỗng nếu hợp lệ
 * 
 * @example
 * const error = validateInput({
 *   lat: 10.762622,
 *   lon: 106.660172,
 *   azimuth: 45,
 *   distance: 2.5
 * });
 * if (error) console.error(error);
 */
function validateInput(data) {
  const { lat, lon, azimuth, distance } = data;
  
  // Kiểm tra vĩ độ
  if (lat < LAT_MIN || lat > LAT_MAX) {
    return `Vĩ độ phải trong khoảng ${LAT_MIN}° đến ${LAT_MAX}°`;
  }
  
  // Kiểm tra kinh độ
  if (lon < LON_MIN || lon > LON_MAX) {
    return `Kinh độ phải trong khoảng ${LON_MIN}° đến ${LON_MAX}°`;
  }
  
  // Kiểm tra azimuth
  if (azimuth < AZIMUTH_MIN || azimuth > AZIMUTH_MAX) {
    return `Góc azimuth phải trong khoảng ${AZIMUTH_MIN}° đến ${AZIMUTH_MAX}°`;
  }
  
  // Kiểm tra khoảng cách
  if (distance <= 0) {
    return 'Khoảng cách phải lớn hơn 0 km';
  }
  
  // Cảnh báo nếu khoảng cách lớn
  if (distance > 100) {
    return 'Cảnh báo: Khoảng cách lớn (>100km) có thể làm giảm độ chính xác tính toán trên mô hình cầu';
  }
  
  // Kiểm tra NaN
  if (isNaN(lat) || isNaN(lon) || isNaN(azimuth) || isNaN(distance)) {
    return 'Dữ liệu đầu vào không hợp lệ. Vui lòng kiểm tra lại các giá trị';
  }
  
  // Hợp lệ
  return '';
}

/**
 * Validate DMS components
 * 
 * @param {number} degrees - Độ
 * @param {number} minutes - Phút
 * @param {number} seconds - Giây
 * @param {string} type - 'lat' hoặc 'lon'
 * @returns {string} Thông báo lỗi hoặc chuỗi rỗng
 */
function validateDMS(degrees, minutes, seconds, type) {
  // Kiểm tra NaN
  if (isNaN(degrees) || isNaN(minutes) || isNaN(seconds)) {
    return 'Giá trị DMS không hợp lệ';
  }
  
  // Kiểm tra minutes và seconds
  if (minutes < 0 || minutes >= 60) {
    return 'Phút phải trong khoảng 0-59';
  }
  
  if (seconds < 0 || seconds >= 60) {
    return 'Giây phải trong khoảng 0-59.99';
  }
  
  // Kiểm tra degrees theo loại
  if (type === 'lat') {
    if (Math.abs(degrees) > 90) {
      return 'Độ vĩ độ phải trong khoảng -90 đến 90';
    }
  } else if (type === 'lon') {
    if (Math.abs(degrees) > 180) {
      return 'Độ kinh độ phải trong khoảng -180 đến 180';
    }
  }
  
  return '';
}

// ==================== FORMATTING UTILITIES ====================

/**
 * Format tọa độ decimal thành chuỗi đẹp
 * 
 * @param {number} decimal - Tọa độ decimal
 * @param {number} precision - Số chữ số thập phân (default: 6)
 * @returns {string} Chuỗi formatted
 * 
 * @example
 * formatDecimal(10.762622, 6); // "10.762622°"
 */
function formatDecimal(decimal, precision = 6) {
  return `${decimal.toFixed(precision)}°`;
}

/**
 * Format tọa độ DMS thành chuỗi đẹp
 * 
 * @param {object} dms - Object {degrees, minutes, seconds}
 * @returns {string} Chuỗi formatted
 * 
 * @example
 * formatDMS({degrees: 10, minutes: 45, seconds: 45.44}); 
 * // "10° 45' 45.44""
 */
function formatDMS(dms) {
  return `${dms.degrees}° ${dms.minutes}' ${dms.seconds}"`;
}

/**
 * Format khoảng cách với đơn vị phù hợp
 * 
 * @param {number} distanceKm - Khoảng cách (km)
 * @returns {string} Chuỗi formatted
 * 
 * @example
 * formatDistance(2.5); // "2.50 km"
 * formatDistance(0.5); // "500 m"
 */
function formatDistance(distanceKm) {
  if (distanceKm < 1) {
    return `${(distanceKm * 1000).toFixed(0)} m`;
  }
  return `${distanceKm.toFixed(2)} km`;
}

/**
 * Format azimuth với hướng (cardinal direction)
 * 
 * @param {number} azimuth - Góc azimuth (degrees)
 * @returns {string} Chuỗi formatted với hướng
 * 
 * @example
 * formatAzimuth(45); // "45.0° (NE - Đông Bắc)"
 */
function formatAzimuth(azimuth) {
  const directions = [
    { angle: 0, short: 'N', full: 'Bắc' },
    { angle: 45, short: 'NE', full: 'Đông Bắc' },
    { angle: 90, short: 'E', full: 'Đông' },
    { angle: 135, short: 'SE', full: 'Đông Nam' },
    { angle: 180, short: 'S', full: 'Nam' },
    { angle: 225, short: 'SW', full: 'Tây Nam' },
    { angle: 270, short: 'W', full: 'Tây' },
    { angle: 315, short: 'NW', full: 'Tây Bắc' },
    { angle: 360, short: 'N', full: 'Bắc' }
  ];
  
  // Tìm hướng gần nhất
  let closestDir = directions[0];
  let minDiff = Math.abs(azimuth - directions[0].angle);
  
  for (const dir of directions) {
    const diff = Math.abs(azimuth - dir.angle);
    if (diff < minDiff) {
      minDiff = diff;
      closestDir = dir;
    }
  }
  
  return `${azimuth.toFixed(1)}° (${closestDir.short} - ${closestDir.full})`;
}

// ==================== ERROR ESTIMATION ====================

/**
 * Ước lượng sai số tổng hợp từ các nguồn lỗi
 * 
 * Công thức: σ_total² = σ_GPS² + (d × σ_azimuth)² + σ_distance²
 * 
 * @param {number} distanceKm - Khoảng cách (km)
 * @param {number} gpsError - Sai số GPS (m, default: 10)
 * @param {number} azimuthError - Sai số azimuth (degrees, default: 0.5)
 * @param {number} distanceError - Sai số khoảng cách (m, default: 0.5)
 * @returns {number} Sai số ước lượng (meters)
 * 
 * @example
 * const error = estimateError(2.5); // ~13.5m cho khoảng cách 2.5km
 */
function estimateError(distanceKm, gpsError = 10, azimuthError = 0.5, distanceError = 0.5) {
  // Chuyển azimuth error sang radian
  const azimuthErrorRad = azimuthError * DEG_TO_RAD;
  
  // Sai số do azimuth (perpendicular error)
  const azimuthErrorMeters = distanceKm * 1000 * Math.sin(azimuthErrorRad);
  
  // Tổng hợp sai số (root sum square)
  const totalError = Math.sqrt(
    Math.pow(gpsError, 2) +
    Math.pow(azimuthErrorMeters, 2) +
    Math.pow(distanceError, 2)
  );
  
  return totalError;
}

// ==================== MAIN CALCULATION FUNCTION ====================

/**
 * Hàm main để tính toán tọa độ mục tiêu
 * Bao gồm validation, calculation và formatting
 * 
 * @param {object} input - Object chứa tất cả input data
 * @returns {object} Object chứa result hoặc error
 * 
 * @example
 * const result = calculateTarget({
 *   observerLat: 10.762622,
 *   observerLon: 106.660172,
 *   azimuth: 45,
 *   distance: 2.5
 * });
 * 
 * if (result.success) {
 *   console.log(result.data);
 * } else {
 *   console.error(result.error);
 * }
 */
function calculateTarget(input) {
  const { observerLat, observerLon, azimuth, distance } = input;
  const algorithm = input.algorithm || 'spherical-haversine';
  const compareWith = input.compareWith || [];
  
  // Validate input
  const validationError = validateInput({
    lat: observerLat,
    lon: observerLon,
    azimuth: azimuth,
    distance: distance
  });
  if (validationError) {
    return { success: false, error: validationError };
  }
  
  try {
    const primary = calculateTargetCoordinate(
      observerLat, observerLon, azimuth, distance, algorithm
    );
    
    // Verify bằng Haversine (khoảng cách & bearing)
    const verifyDistance = calculateDistance(
      observerLat, observerLon, primary.lat, primary.lon
    );
    const verifyBearing = calculateBearing(
      observerLat, observerLon, primary.lat, primary.lon
    );
    const estimatedError = estimateError(distance);
    
    // Optional comparisons
    const comparisons = [];
    for (const algo of compareWith) {
      const other = calculateTargetCoordinate(
        observerLat, observerLon, azimuth, distance, algo
      );
      const deltaMeters = calculateDistance(
        primary.lat, primary.lon, other.lat, other.lon
      ) * 1000.0;
      comparisons.push({
        algorithm: algo,
        target: other,
        deltaMeters,
        deltaFormatted: `${deltaMeters.toFixed(2)} m`
      });
    }
    
    return {
      success: true,
      data: {
        algorithm,
        algorithmsAvailable: listAlgorithms(),
        // Observer
        observer: {
          lat: observerLat,
          lon: observerLon,
          latFormatted: formatDecimal(observerLat),
          lonFormatted: formatDecimal(observerLon),
          dms: { lat: decimalToDMS(observerLat), lon: decimalToDMS(observerLon) }
        },
        // Target (primary)
        target: {
          lat: primary.lat,
          lon: primary.lon,
          latFormatted: formatDecimal(primary.lat),
          lonFormatted: formatDecimal(primary.lon),
          dms: { lat: decimalToDMS(primary.lat), lon: decimalToDMS(primary.lon) }
        },
        measurement: {
          azimuth,
          azimuthFormatted: formatAzimuth(azimuth),
          distance,
          distanceFormatted: formatDistance(distance)
        },
        verification: {
          distance: verifyDistance,
          bearing: verifyBearing,
          distanceError: Math.abs(verifyDistance - distance),
          bearingError: Math.abs(verifyBearing - azimuth)
        },
        estimatedError: { meters: estimatedError, formatted: `±${estimatedError.toFixed(1)}m` },
        comparisons
      }
    };
  } catch (error) {
    return { success: false, error: `Lỗi tính toán: ${error.message}` };
  }
}

// ==================== ALGORITHM REGISTRY ====================

const Algorithms = {
  'spherical-haversine': sphericalDestination,
  'vincenty': vincentyDestination
};
function listAlgorithms() { return Object.keys(Algorithms); }

// ==================== EXPORT FOR BROWSER ====================

/**
 * Export các functions để sử dụng trong HTML
 * Tạo global object CoordinateCalculator
 */
if (typeof window !== 'undefined') {
  window.CoordinateCalculator = {
    // Conversion functions
    dmsToDecimal,
    decimalToDMS,
    
    // Calculation functions
    calculateTargetCoordinate,
    calculateDistance,
    calculateBearing,
    calculateTarget,
    listAlgorithms,
    
    // Validation functions
    validateInput,
    validateDMS,
    
    // Formatting functions
    formatDecimal,
    formatDMS,
    formatDistance,
    formatAzimuth,
    
    // Error estimation
    estimateError,
    
    // Constants
    EARTH_RADIUS_KM,
    DEG_TO_RAD,
    RAD_TO_DEG
  };
  
  console.log('✅ CoordinateCalculator module loaded');
}

// ==================== NODEJS EXPORT (Optional) ====================

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    dmsToDecimal,
    decimalToDMS,
    calculateTargetCoordinate,
    calculateDistance,
    calculateBearing,
    calculateTarget,
    listAlgorithms,
    validateInput,
    validateDMS,
    formatDecimal,
    formatDMS,
    formatDistance,
    formatAzimuth,
    estimateError,
    EARTH_RADIUS_KM,
    DEG_TO_RAD,
    RAD_TO_DEG
  };
}