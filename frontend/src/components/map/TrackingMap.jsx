import React from 'react';
import { MapContainer, TileLayer, Circle, useMap } from 'react-leaflet';
import TargetMarker from './TargetMarker';
import TrajectoryPolyline from './TrajectoryPolyline';
import RoadNetwork from './RoadNetwork';
import useTrackingStore from '../../store/trackingStore';
import { cssVar } from '../../utils/themeColors';

// Continuously re-centre map on Kalman-estimated position
function MapAutoCenter() {
  const map = useMap();
  const { currentFrame } = useTrackingStore();
  const hasCentered = React.useRef(false);

  React.useEffect(() => {
    if (!currentFrame) return;

    const frame = currentFrame;
    const pos = frame.kalman ?? frame.ground_truth;
    if (!pos) return;

    const { lat, lon } = pos;

    if (!hasCentered.current) {
      map.setView([lat, lon], map.getZoom(), { animate: true, duration: 0.3 });
      hasCentered.current = true;
      return;
    }

    const center = map.getCenter();
    const dist = map.distance(center, [lat, lon]);
    if (dist > 20) map.panTo([lat, lon], { animate: true, duration: 0.5 });
  }, [currentFrame, map]);

  return null;
}

// Range rings around observer position
function RangeRings({ center, radii = [200, 400, 600] }) {
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
}

export default function TrackingMap({ observerPos }) {
  const {
    currentFrame, showGroundTruth, showRaw, showKalman, showAlphaBeta, showRoads,
    groundTruthHistory, rawHistory, kalmanHistory, alphaBetaHistory,
  } = useTrackingStore();

  const center = observerPos || [10.7743, 106.7031];

  return (
    <div style={{ position: 'relative', flex: 1, minHeight: 0 }}>
      <MapContainer
        center={center}
        zoom={16}
        style={{ width: '100%', height: '100%' }}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          maxZoom={19}
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
