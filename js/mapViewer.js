/**
 * MAP VIEWER MODULE
 * ==================
 * Quản lý Leaflet map và tương tác với UI
 * 
 * Chức năng chính:
 * - Khởi tạo và quản lý Leaflet map
 * - Thêm/cập nhật markers (quan sát viên, mục tiêu)
 * - Vẽ đường nối giữa các điểm
 * - Xử lý event handlers cho UI
 * - Mode switching (Decimal ↔ DMS)
 */

'use strict';

// ==================== GLOBAL VARIABLES ====================

/**
 * Leaflet map instance
 * @type {L.Map}
 */
let map = null;

/**
 * Markers references
 */
let observerMarker = null;
let targetMarker = null;

/**
 * Line connecting observer and target
 * @type {L.Polyline}
 */
let bearingLine = null;

/**
 * Current input mode: 'decimal' hoặc 'dms'
 * @type {string}
 */
let currentMode = 'decimal';

/**
 * Custom marker icons
 */
const RedIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const BlueIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// ==================== MAP INITIALIZATION ====================

/**
 * Khởi tạo Leaflet map
 * 
 * @param {string} containerId - ID của div container
 * @param {number} lat - Vĩ độ trung tâm ban đầu
 * @param {number} lon - Kinh độ trung tâm ban đầu
 * @param {number} zoom - Mức zoom (default: 13)
 * @returns {L.Map} Map instance
 * 
 * @example
 * const myMap = initializeMap('map', 10.762622, 106.660172, 13);
 */
function initializeMap(containerId, lat, lon, zoom = 13) {
  try {
    // Tạo map instance
    map = L.map(containerId, {
      center: [lat, lon],
      zoom: zoom,
      zoomControl: true,
      attributionControl: true
    });
    
    // Thêm OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Thêm marker quan sát viên tại vị trí ban đầu
    observerMarker = L.marker([lat, lon], { 
      icon: RedIcon,
      title: 'Vị trí Quan sát viên'
    }).addTo(map);
    
    observerMarker.bindPopup(`
      <div style="font-size: 14px;">
        <strong>🔴 Quan sát viên</strong><br>
        Vĩ độ: ${lat.toFixed(6)}°<br>
        Kinh độ: ${lon.toFixed(6)}°
      </div>
    `);
    
    // Setup event handlers
    setupEventHandlers();
    
    console.log('Map initialized successfully');
    return map;
    
  } catch (error) {
    console.error('Error initializing map:', error);
    showError('Không thể khởi tạo bản đồ. Vui lòng kiểm tra kết nối Internet.');
    return null;
  }
}

// ==================== MARKER MANAGEMENT ====================

/**
 * Cập nhật vị trí marker quan sát viên
 * 
 * @param {number} lat - Vĩ độ mới
 * @param {number} lon - Kinh độ mới
 */
function updateObserverMarker(lat, lon) {
  if (observerMarker) {
    observerMarker.setLatLng([lat, lon]);
    observerMarker.setPopupContent(`
      <div style="font-size: 14px;">
        <strong>🔴 Quan sát viên</strong><br>
        Vĩ độ: ${lat.toFixed(6)}°<br>
        Kinh độ: ${lon.toFixed(6)}°
      </div>
    `);
  }
}

/**
 * Thêm hoặc cập nhật marker mục tiêu
 * 
 * @param {number} lat - Vĩ độ mục tiêu
 * @param {number} lon - Kinh độ mục tiêu
 * @param {number} distance - Khoảng cách từ quan sát viên
 * @param {number} azimuth - Góc phương vị
 */
function updateTargetMarker(lat, lon, distance, azimuth) {
  if (targetMarker) {
    // Cập nhật marker hiện tại
    targetMarker.setLatLng([lat, lon]);
    targetMarker.setPopupContent(`
      <div style="font-size: 14px;">
        <strong>🎯 Mục tiêu</strong><br>
        Vĩ độ: ${lat.toFixed(6)}°<br>
        Kinh độ: ${lon.toFixed(6)}°<br>
        <hr style="margin: 8px 0;">
        Khoảng cách: ${distance.toFixed(2)} km<br>
        Phương vị: ${azimuth.toFixed(1)}°
      </div>
    `);
    targetMarker.setOpacity(1);
  } else {
    // Tạo marker mới
    targetMarker = L.marker([lat, lon], { 
      icon: BlueIcon,
      title: 'Vị trí Mục tiêu'
    }).addTo(map);
    
    targetMarker.bindPopup(`
      <div style="font-size: 14px;">
        <strong>🎯 Mục tiêu</strong><br>
        Vĩ độ: ${lat.toFixed(6)}°<br>
        Kinh độ: ${lon.toFixed(6)}°<br>
        <hr style="margin: 8px 0;">
        Khoảng cách: ${distance.toFixed(2)} km<br>
        Phương vị: ${azimuth.toFixed(1)}°
      </div>
    `);
  }
  
  // Mở popup tự động
  targetMarker.openPopup();
}

/**
 * Vẽ đường nối giữa quan sát viên và mục tiêu
 * 
 * @param {number} obsLat - Vĩ độ quan sát viên
 * @param {number} obsLon - Kinh độ quan sát viên
 * @param {number} tgtLat - Vĩ độ mục tiêu
 * @param {number} tgtLon - Kinh độ mục tiêu
 */
function drawBearingLine(obsLat, obsLon, tgtLat, tgtLon) {
  // Xóa đường cũ nếu có
  if (bearingLine) {
    map.removeLayer(bearingLine);
  }
  
  // Vẽ đường mới
  bearingLine = L.polyline(
    [[obsLat, obsLon], [tgtLat, tgtLon]], 
    {
      color: '#ef4444',
      weight: 3,
      opacity: 0.7,
      dashArray: '10, 5',
      lineJoin: 'round'
    }
  ).addTo(map);
  
  // Thêm tooltip ở giữa đường
  const midLat = (obsLat + tgtLat) / 2;
  const midLon = (obsLon + tgtLon) / 2;
  
  bearingLine.bindTooltip('Đường ngắm', {
    permanent: false,
    direction: 'center',
    className: 'bearing-line-tooltip'
  });
}

/**
 * Tự động zoom và center map để hiển thị cả 2 markers
 * 
 * @param {number} obsLat - Vĩ độ quan sát viên
 * @param {number} obsLon - Kinh độ quan sát viên
 * @param {number} tgtLat - Vĩ độ mục tiêu
 * @param {number} tgtLon - Kinh độ mục tiêu
 */
function fitMapToBounds(obsLat, obsLon, tgtLat, tgtLon) {
  const bounds = L.latLngBounds(
    [[obsLat, obsLon], [tgtLat, tgtLon]]
  );
  
  map.fitBounds(bounds, {
    padding: [50, 50],
    maxZoom: 15,
    animate: true,
    duration: 0.5
  });
}

// ==================== UI EVENT HANDLERS ====================

/**
 * Setup tất cả event handlers cho UI
 */
function setupEventHandlers() {
  // Mode toggle button
  const toggleBtn = document.getElementById('toggleModeBtn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', handleModeToggle);
  }
  
  // Calculate button
  const calcBtn = document.getElementById('calculateBtn');
  if (calcBtn) {
    calcBtn.addEventListener('click', handleCalculate);
  }
  
  // Copy button
  const copyBtn = document.getElementById('copyBtn');
  if (copyBtn) {
    copyBtn.addEventListener('click', handleCopyCoordinates);
  }
  
  // Enter key to calculate
  const inputs = document.querySelectorAll('input[type="number"]');
  inputs.forEach(input => {
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        handleCalculate();
      }
    });
  });
  
  console.log('Event handlers setup complete');
}

/**
 * Xử lý khi toggle giữa Decimal và DMS mode
 */
function handleModeToggle() {
  const decimalInputs = document.getElementById('decimalInputs');
  const dmsInputs = document.getElementById('dmsInputs');
  const modeText = document.getElementById('modeText');
  
  if (currentMode === 'decimal') {
    // Chuyển sang DMS
    // Lấy giá trị decimal hiện tại
    const latDec = parseFloat(document.getElementById('latDecimal').value);
    const lonDec = parseFloat(document.getElementById('lonDecimal').value);
    
    // Chuyển đổi sang DMS
    const latDMS = window.CoordinateCalculator.decimalToDMS(latDec);
    const lonDMS = window.CoordinateCalculator.decimalToDMS(lonDec);
    
    // Cập nhật DMS inputs
    document.getElementById('latDeg').value = latDMS.degrees;
    document.getElementById('latMin').value = latDMS.minutes;
    document.getElementById('latSec').value = latDMS.seconds;
    document.getElementById('lonDeg').value = lonDMS.degrees;
    document.getElementById('lonMin').value = lonDMS.minutes;
    document.getElementById('lonSec').value = lonDMS.seconds;
    
    // Toggle display
    decimalInputs.style.display = 'none';
    dmsInputs.style.display = 'flex';
    modeText.textContent = 'DMS';
    currentMode = 'dms';
    
  } else {
    // Chuyển sang Decimal
    // Lấy giá trị DMS hiện tại
    const latDeg = parseFloat(document.getElementById('latDeg').value);
    const latMin = parseFloat(document.getElementById('latMin').value);
    const latSec = parseFloat(document.getElementById('latSec').value);
    const lonDeg = parseFloat(document.getElementById('lonDeg').value);
    const lonMin = parseFloat(document.getElementById('lonMin').value);
    const lonSec = parseFloat(document.getElementById('lonSec').value);
    
    // Chuyển đổi sang Decimal
    const latDec = window.CoordinateCalculator.dmsToDecimal(latDeg, latMin, latSec);
    const lonDec = window.CoordinateCalculator.dmsToDecimal(lonDeg, lonMin, lonSec);
    
    // Cập nhật Decimal inputs
    document.getElementById('latDecimal').value = latDec.toFixed(6);
    document.getElementById('lonDecimal').value = lonDec.toFixed(6);
    
    // Toggle display
    decimalInputs.style.display = 'flex';
    dmsInputs.style.display = 'none';
    modeText.textContent = 'Decimal';
    currentMode = 'decimal';
  }
}

/**
 * Xử lý khi nhấn nút Calculate
 */
function handleCalculate() {
  // Hide error và result cũ
  hideError();
  hideResult();
  
  // Lấy dữ liệu input
  let observerLat, observerLon;
  
  if (currentMode === 'decimal') {
    observerLat = parseFloat(document.getElementById('latDecimal').value);
    observerLon = parseFloat(document.getElementById('lonDecimal').value);
  } else {
    // DMS mode
    const latDeg = parseFloat(document.getElementById('latDeg').value);
    const latMin = parseFloat(document.getElementById('latMin').value);
    const latSec = parseFloat(document.getElementById('latSec').value);
    const lonDeg = parseFloat(document.getElementById('lonDeg').value);
    const lonMin = parseFloat(document.getElementById('lonMin').value);
    const lonSec = parseFloat(document.getElementById('lonSec').value);
    
    observerLat = window.CoordinateCalculator.dmsToDecimal(latDeg, latMin, latSec);
    observerLon = window.CoordinateCalculator.dmsToDecimal(lonDeg, lonMin, lonSec);
  }
  
  const azimuth = parseFloat(document.getElementById('azimuth').value);
  const distance = parseFloat(document.getElementById('distance').value);
  
  // Tính toán
  const result = window.CoordinateCalculator.calculateTarget({
    observerLat,
    observerLon,
    azimuth,
    distance
  });
  
  if (result.success) {
    // Hiển thị kết quả
    displayResult(result.data);
    
    // Cập nhật map
    updateObserverMarker(observerLat, observerLon);
    updateTargetMarker(
      result.data.target.lat,
      result.data.target.lon,
      distance,
      azimuth
    );
    drawBearingLine(
      observerLat,
      observerLon,
      result.data.target.lat,
      result.data.target.lon
    );
    fitMapToBounds(
      observerLat,
      observerLon,
      result.data.target.lat,
      result.data.target.lon
    );
    
  } else {
    // Hiển thị lỗi
    showError(result.error);
  }
}

/**
 * Xử lý copy tọa độ vào clipboard
 */
function handleCopyCoordinates() {
  const latText = document.getElementById('resultLat').textContent;
  const lonText = document.getElementById('resultLon').textContent;
  
  const coordinates = `${latText}, ${lonText}`;
  
  // Copy to clipboard
  navigator.clipboard.writeText(coordinates).then(() => {
    // Thay đổi text button tạm thời
    const copyBtn = document.getElementById('copyBtn');
    const originalHTML = copyBtn.innerHTML;
    copyBtn.innerHTML = '<span class="copy-icon">✅</span> Đã copy!';
    copyBtn.style.backgroundColor = '#d1fae5';
    copyBtn.style.color = '#065f46';
    copyBtn.style.borderColor = '#6ee7b7';
    
    // Reset sau 2 giây
    setTimeout(() => {
      copyBtn.innerHTML = originalHTML;
      copyBtn.style.backgroundColor = '';
      copyBtn.style.color = '';
      copyBtn.style.borderColor = '';
    }, 2000);
  }).catch(err => {
    console.error('Copy failed:', err);
    showError('Không thể copy tọa độ. Vui lòng thử lại.');
  });
}

// ==================== DISPLAY FUNCTIONS ====================

/**
 * Hiển thị kết quả tính toán
 * 
 * @param {object} data - Dữ liệu kết quả từ calculateTarget()
 */
function displayResult(data) {
  const resultSection = document.getElementById('resultSection');
  const resultLat = document.getElementById('resultLat');
  const resultLon = document.getElementById('resultLon');
  const resultDistance = document.getElementById('resultDistance');
  const resultAzimuth = document.getElementById('resultAzimuth');
  
  // Cập nhật nội dung
  resultLat.textContent = data.target.latFormatted;
  resultLon.textContent = data.target.lonFormatted;
  resultDistance.textContent = data.measurement.distanceFormatted;
  resultAzimuth.textContent = data.measurement.azimuthFormatted;
  
  // Hiển thị result section
  resultSection.style.display = 'block';
  
  // Smooth scroll to result (if needed)
  resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  
  console.log('Result displayed:', data);
}

/**
 * Ẩn kết quả
 */
function hideResult() {
  const resultSection = document.getElementById('resultSection');
  if (resultSection) {
    resultSection.style.display = 'none';
  }
}

/**
 * Hiển thị thông báo lỗi
 * 
 * @param {string} message - Nội dung lỗi
 */
function showError(message) {
  const errorDiv = document.getElementById('errorMessage');
  const errorText = document.getElementById('errorText');
  
  if (errorDiv && errorText) {
    errorText.textContent = message;
    errorDiv.style.display = 'flex';
    
    // Smooth scroll to error
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    console.warn('Error:', message);
  }
}

/**
 * Ẩn thông báo lỗi
 */
function hideError() {
  const errorDiv = document.getElementById('errorMessage');
  if (errorDiv) {
    errorDiv.style.display = 'none';
  }
}

// ==================== UTILITY FUNCTIONS ====================

/**
 * Lấy tọa độ hiện tại từ input (dù đang ở mode nào)
 * 
 * @returns {object} {lat, lon}
 */
function getCurrentCoordinates() {
  let lat, lon;
  
  if (currentMode === 'decimal') {
    lat = parseFloat(document.getElementById('latDecimal').value);
    lon = parseFloat(document.getElementById('lonDecimal').value);
  } else {
    const latDeg = parseFloat(document.getElementById('latDeg').value);
    const latMin = parseFloat(document.getElementById('latMin').value);
    const latSec = parseFloat(document.getElementById('latSec').value);
    const lonDeg = parseFloat(document.getElementById('lonDeg').value);
    const lonMin = parseFloat(document.getElementById('lonMin').value);
    const lonSec = parseFloat(document.getElementById('lonSec').value);
    
    lat = window.CoordinateCalculator.dmsToDecimal(latDeg, latMin, latSec);
    lon = window.CoordinateCalculator.dmsToDecimal(lonDeg, lonMin, lonSec);
  }
  
  return { lat, lon };
}

/**
 * Load test case vào form
 * 
 * @param {object} testCase - Test case data
 */
function loadTestCase(testCase) {
  document.getElementById('latDecimal').value = testCase.observer.lat;
  document.getElementById('lonDecimal').value = testCase.observer.lon;
  document.getElementById('azimuth').value = testCase.azimuth;
  document.getElementById('distance').value = testCase.distance;
  
  // Switch to decimal mode if needed
  if (currentMode === 'dms') {
    document.getElementById('toggleModeBtn').click();
  }
  
  console.log('📋 Test case loaded:', testCase.name);
}

/**
 * Export kết quả ra format text
 * 
 * @param {object} data - Dữ liệu kết quả
 * @returns {string} Text formatted
 */
function exportResultAsText(data) {
  return `
=== TỌA ĐỘ MỤC TIÊU ===

QUAN SÁT VIÊN:
Vĩ độ:  ${data.observer.latFormatted}
Kinh độ: ${data.observer.lonFormatted}

MỤC TIÊU:
Vĩ độ:  ${data.target.latFormatted}
Kinh độ: ${data.target.lonFormatted}

THÔNG TIN ĐO ĐẠC:
Khoảng cách: ${data.measurement.distanceFormatted}
Phương vị:   ${data.measurement.azimuthFormatted}

SAI SỐ ƯỚC LƯỢNG: ${data.estimatedError.formatted}

---
Generated by Target Coordinate Calculator
${new Date().toLocaleString('vi-VN')}
  `.trim();
}

/**
 * Download kết quả dưới dạng file text
 * 
 * @param {object} data - Dữ liệu kết quả
 */
function downloadResult(data) {
  const text = exportResultAsText(data);
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `target_coordinates_${Date.now()}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  
  console.log('💾 Result downloaded');
}

// ==================== SAMPLE DATA & TESTING ====================

/**
 * Sample test cases cho debugging và demo
 */
const SAMPLE_TEST_CASES = [
  {
    name: 'TP.HCM - Đông Bắc 2.5km',
    observer: { lat: 10.762622, lon: 106.660172 },
    azimuth: 45,
    distance: 2.5
  },
  {
    name: 'Hà Nội - Bắc 5km',
    observer: { lat: 21.028511, lon: 105.804817 },
    azimuth: 0,
    distance: 5
  },
  {
    name: 'Đà Nẵng - Đông 3km',
    observer: { lat: 16.047079, lon: 108.206230 },
    azimuth: 90,
    distance: 3
  }
];

/**
 * Load random test case (for testing)
 */
function loadRandomTestCase() {
  const randomIndex = Math.floor(Math.random() * SAMPLE_TEST_CASES.length);
  const testCase = SAMPLE_TEST_CASES[randomIndex];
  loadTestCase(testCase);
  console.log('Random test case loaded');
}

// ==================== KEYBOARD SHORTCUTS ====================

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter = Calculate
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleCalculate();
    }
    
    // Ctrl/Cmd + M = Toggle Mode
    if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
      e.preventDefault();
      handleModeToggle();
    }
    
    // Ctrl/Cmd + C (when result visible) = Copy coordinates
    if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
      const resultSection = document.getElementById('resultSection');
      if (resultSection && resultSection.style.display === 'block') {
        e.preventDefault();
        handleCopyCoordinates();
      }
    }
  });
  
  console.log('Keyboard shortcuts enabled');
  console.log('  - Ctrl+Enter: Calculate');
  console.log('  - Ctrl+M: Toggle Mode');
  console.log('  - Ctrl+C: Copy Result');
}

// ==================== INITIALIZATION ====================

/**
 * Initialize everything when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
  console.log('MapViewer module initializing...');
  
  // Setup keyboard shortcuts
  setupKeyboardShortcuts();
  
  // Add helper functions to window for console debugging
  if (typeof window !== 'undefined') {
    window.MapViewer = {
      // Map functions
      updateObserverMarker,
      updateTargetMarker,
      drawBearingLine,
      fitMapToBounds,
      
      // UI functions
      displayResult,
      hideResult,
      showError,
      hideError,
      
      // Utility functions
      getCurrentCoordinates,
      loadTestCase,
      loadRandomTestCase,
      exportResultAsText,
      downloadResult,
      
      // Data
      SAMPLE_TEST_CASES,
      
      // References
      getMap: () => map,
      getObserverMarker: () => observerMarker,
      getTargetMarker: () => targetMarker
    };
    
    console.log('✅ MapViewer module loaded and ready');
  }
});

// ==================== EXPORT FOR TESTING ====================

/**
 * Export for Node.js testing (optional)
 */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initializeMap,
    updateObserverMarker,
    updateTargetMarker,
    drawBearingLine,
    fitMapToBounds,
    displayResult,
    showError,
    hideError,
    getCurrentCoordinates,
    loadTestCase,
    exportResultAsText,
    SAMPLE_TEST_CASES
  };
}

// ==================== CONSOLE HELPERS ====================

/**
 * Console helper để test nhanh
 * Chỉ available trong development mode
 */
if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
  console.log('');
  console.log('🛠️  DEVELOPMENT MODE - Console Helpers Available:');
  console.log('');
  console.log('MapViewer.loadRandomTestCase()  - Load random test case');
  console.log('MapViewer.loadTestCase(tc)      - Load specific test case');
  console.log('MapViewer.getCurrentCoordinates() - Get current input coords');
  console.log('MapViewer.SAMPLE_TEST_CASES      - View all test cases');
  console.log('');
  console.log('Example:');
  console.log('  MapViewer.loadTestCase(MapViewer.SAMPLE_TEST_CASES[0])');
  console.log('');
}

// ==================== END OF MODULE ====================