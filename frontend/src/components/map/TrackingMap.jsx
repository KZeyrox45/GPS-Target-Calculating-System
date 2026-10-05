import React, { useRef, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Circle, useMap } from 'react-leaflet';
import TargetMarker from './TargetMarker';
import TrajectoryPolyline from './TrajectoryPolyline';
import RoadNetwork from './RoadNetwork';
import useTrackingStore from '../../store/trackingStore';
import { cssVar } from '../../utils/themeColors';

// Deadband and throttled camera tracking to prevent animation backlog
function MapAutoCenter() {
  const map = useMap();
  const currentFrame = useTrackingStore((s) => s.currentFrame);

  const hasCentered = useRef(false);
  const lastPanTime = useRef(0);

  useEffect(() => {
    if (!currentFrame) return;
    const pos = currentFrame.kalman ?? currentFrame.ground_truth;
    if (!pos) return;
    const { lat, lon } = pos;

    if (!hasCentered.current) {
      map.setView([lat, lon], map.getZoom(), { animate: false });
      hasCentered.current = true;
      lastPanTime.current = performance.now();
      return;
    }

    // Do not fight active user interaction (panning / dragging)
    if (map.dragging && map.dragging.moving()) return;

    const now = performance.now();
    // Throttle camera updates to at most once per 600 ms
    if (now - lastPanTime.current < 600) return;

    const center = map.getCenter();
    const dist = map.distance(center, [lat, lon]);

    // Deadband: only pan if target drifted more than 50 m from viewport center
    if (dist > 50) {
      lastPanTime.current = now;
      map.panTo([lat, lon], {
        animate: true,
        duration: 0.25,
        easeLinearity: 0.5,
        noMoveStart: true,
      });
    }
  }, [currentFrame, map]);

  return null;
}

// Range rings around observer position
const RangeRings = React.memo(function RangeRings({ center, radii = [200, 400, 600] }) {
  if (!center) return null;
  return radii.map(r => (
    <Circle
      key={r}
      center={center}
      radius={r}
      pathOptions={{
        color: 'rgba(34, 197, 94, 0.35)',
        weight: 1.5,
        dashArray: '6 4',
        fillColor: 'transparent',
      }}
    />
  ));
});

// Robust container resize observer with requestAnimationFrame debouncing
function MapResizer() {
  const map = useMap();
  useEffect(() => {
    const container = map.getContainer();
    if (!container) return;

    let rafId = null;
    const handleResize = () => {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        map.invalidateSize({ debounceMoveend: true });
      });
    };

    handleResize();
    const observer = new ResizeObserver(handleResize);
    observer.observe(container);

    return () => {
      observer.disconnect();
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [map]);

  return null;
}

export default function TrackingMap({ observerPos }) {
  const currentFrame = useTrackingStore((s) => s.currentFrame);
  const showGroundTruth = useTrackingStore((s) => s.showGroundTruth);
  const showRaw = useTrackingStore((s) => s.showRaw);
  const showKalman = useTrackingStore((s) => s.showKalman);
  const showAlphaBeta = useTrackingStore((s) => s.showAlphaBeta);
  const showRoads = useTrackingStore((s) => s.showRoads);
  const groundTruthHistory = useTrackingStore((s) => s.groundTruthHistory);
  const rawHistory = useTrackingStore((s) => s.rawHistory);
  const kalmanHistory = useTrackingStore((s) => s.kalmanHistory);
  const alphaBetaHistory = useTrackingStore((s) => s.alphaBetaHistory);

  const center = useMemo(() => observerPos || [10.7743, 106.7031], [observerPos]);

  return (
    <div style={{ position: 'relative', flex: 1, minHeight: 0 }}>
      <MapContainer
        center={center}
        zoom={16}
        preferCanvas={true}
        style={{ width: '100%', height: '100%' }}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          maxZoom={19}
          keepBuffer={4}
        />

        <RoadNetwork center={center} showRoads={showRoads} />

        {observerPos && (
          <>
            <TargetMarker position={observerPos} type="observer" label="OBS" />
            <RangeRings center={observerPos} />
          </>
        )}

        {showGroundTruth && (
          <TrajectoryPolyline positions={groundTruthHistory} color={cssVar('--color-truth', '#22c55e')} weight={3} />
        )}
        {showRaw && (
          <TrajectoryPolyline positions={rawHistory} color={cssVar('--color-raw', '#eab308')} weight={2} dashArray="6 6" />
        )}
        {showKalman && (
          <TrajectoryPolyline positions={kalmanHistory} color={cssVar('--color-kalman', '#38bdf8')} weight={3.5} />
        )}
        {showAlphaBeta && (
          <TrajectoryPolyline positions={alphaBetaHistory} color={cssVar('--color-alphabeta', '#a78bfa')} weight={2.5} dashArray="8 5" />
        )}

        {currentFrame && showGroundTruth && (
          <TargetMarker position={[currentFrame.ground_truth.lat, currentFrame.ground_truth.lon]} type="truth" label="TRUTH" />
        )}
        {currentFrame && showKalman && (
          <TargetMarker position={[currentFrame.kalman.lat, currentFrame.kalman.lon]} type="kalman" label={`KF ${currentFrame.metrics.kalman_error?.toFixed(1)}m`} />
        )}
        {currentFrame && showAlphaBeta && (
          <TargetMarker position={[currentFrame.alpha_beta.lat, currentFrame.alpha_beta.lon]} type="alpha_beta" label={`AB ${currentFrame.metrics.alpha_beta_error?.toFixed(1)}m`} />
        )}

        <MapAutoCenter />
        <MapResizer />
      </MapContainer>

      {/* Tactical grid overlay */}
      <div className="tactical-grid-overlay" />

      {/* Range rings legend */}
      {observerPos && (
        <div style={{
          position: 'absolute', bottom: 32, left: 8, zIndex: 1000,
          background: 'rgba(0,0,0,0.65)', borderRadius: 4, padding: '4px 8px',
          fontSize: '0.65rem', color: '#ccc', lineHeight: 1.5, pointerEvents: 'none',
        }}>
          <div style={{ fontWeight: 600, marginBottom: 2, color: '#aaa' }}>Range Rings</div>
          {[200, 400, 600].map(r => (
            <div key={r} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{
                display: 'inline-block', width: 14, height: 0,
                borderTop: '1.5px dashed rgba(34,197,94,0.6)',
              }} />
              <span>{r}m</span>
            </div>
          ))}
        </div>
      )}

      {/* Compass rose */}
      <div className="compass-rose">
        <span className="n">N</span>
        <span className="s">S</span>
        <span className="e">E</span>
        <span className="w">W</span>
        <div className="center-dot" />
      </div>
    </div>
  );
}
