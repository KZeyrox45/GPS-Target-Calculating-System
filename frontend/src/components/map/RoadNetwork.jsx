import React from 'react';
import { useMap, Polyline } from 'react-leaflet';

/**
 * RoadNetwork - Fetches and displays OpenStreetMap road data via Overpass API.
 * Shows roads as semi-transparent gray polylines for visual context.
 */
export default function RoadNetwork({ center, showRoads = true }) {
  const [roads, setRoads] = React.useState([]);
  const map = useMap();
  const lastFetchRef = React.useRef(null);

  React.useEffect(() => {
    if (!showRoads || !center) return;

    const [lat, lon] = center;
    const radius = 800; // metres around observer

    // Debounce: skip if same center within 5s
    const key = `${lat.toFixed(4)},${lon.toFixed(4)}`;
    if (lastFetchRef.current === key) return;
    lastFetchRef.current = key;

    const query = `
      [out:json][timeout:10];
      (
        way["highway"~"^(primary|secondary|tertiary|residential|unclassified|living_street|pedestrian|service)$"](around:${radius},${lat},${lon});
      );
      out body;
      >;
      out skel qt;
    `;

    fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      body: `data=${encodeURIComponent(query)}`,
    })
      .then(res => res.json())
      .then(data => {
        // Build node lookup
        const nodes = {};
        (data.elements || []).forEach(el => {
          if (el.type === 'node') nodes[el.id] = [el.lat, el.lon];
        });
        // Extract ways as coordinate arrays
        const ways = (data.elements || [])
          .filter(el => el.type === 'way' && el.nodes)
          .map(way => ({
            positions: way.nodes.map(id => nodes[id]).filter(Boolean),
            highway: way.tags?.highway || 'residential',
          }))
          .filter(way => way.positions.length >= 2);
        setRoads(ways);
      })
      .catch(() => {
        // Silently fail - roads are cosmetic only
      });
  }, [center, showRoads, map]);

  if (!showRoads || roads.length === 0) return null;

  return (
    <>
      {roads.map((way, i) => (
        <Polyline
          key={i}
          positions={way.positions}
          pathOptions={{
            color: '#888',
            weight: way.highway === 'primary' || way.highway === 'secondary' ? 2.5 : 1.5,
            opacity: 0.45,
            dashArray: way.highway === 'pedestrian' ? '4 4' : undefined,
          }}
        />
      ))}
    </>
  );
}
