import React from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import TargetMarker from './TargetMarker';
import TrajectoryPolyline from './TrajectoryPolyline';
import useTrackingStore from '../../store/trackingStore';

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
      // First frame — always centre immediately
      map.setView([lat, lon], map.getZoom(), { animate: true, duration: 0.3 });
      hasCentered.current = true;
      return;
    }

    // Subsequent frames — soft pan when >20m away
    const center = map.getCenter();
    const dist = map.distance(center, [lat, lon]);
    if (dist > 20) map.panTo([lat, lon], { animate: true, duration: 0.5 });
  }, [currentFrame, map]);

  return null;
}

export default function TrackingMap({ observerPos }) {
  const {
    currentFrame, showGroundTruth, showRaw, showKalman, showAlphaBeta,
    groundTruthHistory, rawHistory, kalmanHistory, alphaBetaHistory,
  } = useTrackingStore();

  const center = observerPos || [10.762622, 106.660172];

  return (
    <MapContainer
      center={center}
      zoom={16}
      style={{ flex: 1, minHeight: 0 }}
      zoomControl={true}
    >
      {/* Dark OSM tile layer */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        maxZoom={19}
      />

      {/* Observer marker (fixed) */}
      {observerPos && (
        <TargetMarker
          position={observerPos}
          type="observer"
          label="👁️ Observer"
        />
      )}

      {/* Trajectory polylines */}
      {showGroundTruth && (
        <TrajectoryPolyline positions={groundTruthHistory} color="var(--color-truth)" weight={2} />
      )}
      {showRaw && (
        <TrajectoryPolyline positions={rawHistory} color="var(--color-raw)" weight={1.5} dashArray="4 6" />
      )}
      {showKalman && (
        <TrajectoryPolyline positions={kalmanHistory} color="var(--color-kalman)" weight={2.5} />
      )}
      {showAlphaBeta && (
        <TrajectoryPolyline positions={alphaBetaHistory} color="var(--color-alphabeta)" weight={2} dashArray="6 4" />
      )}

      {/* Live target markers */}
      {currentFrame && showGroundTruth && (
        <TargetMarker position={[currentFrame.ground_truth.lat, currentFrame.ground_truth.lon]} type="truth" label="Ground Truth" />
      )}
      {currentFrame && showKalman && (
        <TargetMarker position={[currentFrame.kalman.lat, currentFrame.kalman.lon]} type="kalman" label={`Kalman (${currentFrame.metrics.kalman_error?.toFixed(1)}m err)`} />
      )}
      {currentFrame && showAlphaBeta && (
        <TargetMarker position={[currentFrame.alpha_beta.lat, currentFrame.alpha_beta.lon]} type="alpha_beta" label={`α-β (${currentFrame.metrics.alpha_beta_error?.toFixed(1)}m err)`} />
      )}

      <MapAutoCenter />
    </MapContainer>
  );
}
