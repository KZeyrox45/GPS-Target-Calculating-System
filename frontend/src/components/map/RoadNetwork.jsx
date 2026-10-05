import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Polyline } from 'react-leaflet';

// In-memory cache across component mounts
const ROAD_CACHE = new Map();

/**
 * RoadNetwork - Fetches and displays OpenStreetMap road data via Overpass API.
 * Uses MultiPolyline rendering (2 layers total instead of hundreds of components)
 * and in-memory/session caching with strict request timeouts.
 */
export default function RoadNetwork({ center, showRoads = true }) {
  const [roads, setRoads] = useState({ primary: [], regular: [] });
  const abortCtrlRef = useRef(null);

  useEffect(() => {
    if (!showRoads || !center) return;

    const [lat, lon] = center;
    const cacheKey = `${lat.toFixed(3)},${lon.toFixed(3)}`;

    // Abort any pending fetch
    if (abortCtrlRef.current) {
      abortCtrlRef.current.abort();
    }
    const controller = new AbortController();
    abortCtrlRef.current = controller;
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const radius = 800; // metres
    const query = `
      [out:json][timeout:5];
      (
        way["highway"~"^(primary|secondary|tertiary|residential|unclassified|living_street|service)$"](around:${radius},${lat},${lon});
      );
      out body;
      >;
      out skel qt;
    `;

    const endpoints = [
      'https://overpass-api.de/api/interpreter',
      'https://overpass.kumi.systems/api/interpreter',
    ];

    const fetchFromEndpoint = async (url) => {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `data=${encodeURIComponent(query)}`,
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    };

    const loadRoads = async () => {
      // Check memory cache first
      if (ROAD_CACHE.has(cacheKey)) {
        setRoads(ROAD_CACHE.get(cacheKey));
        return;
      }

      // Check sessionStorage
      try {
        const stored = sessionStorage.getItem(`roads_${cacheKey}`);
        if (stored) {
          const parsed = JSON.parse(stored);
          ROAD_CACHE.set(cacheKey, parsed);
          setRoads(parsed);
          return;
        }
      } catch {
        // sessionStorage unavailable or restricted
      }

      let data = null;
      for (const endpoint of endpoints) {
        if (controller.signal.aborted) break;
        try {
          data = await fetchFromEndpoint(endpoint);
          if (data && data.elements) break;
        } catch {
          // try next mirror
        }
      }

      clearTimeout(timeoutId);
      if (!data || !data.elements || controller.signal.aborted) return;

      const nodes = {};
      for (const el of data.elements) {
        if (el.type === 'node') {
          nodes[el.id] = [el.lat, el.lon];
        }
      }

      const primary = [];
      const regular = [];
      let count = 0;

      for (const el of data.elements) {
        if (el.type !== 'way' || !el.nodes || el.nodes.length < 2) continue;
        if (count >= 150) break; // cap max ways to prevent DOM overload

        const coords = [];
        for (const nid of el.nodes) {
          const pt = nodes[nid];
          if (pt) coords.push(pt);
        }
        if (coords.length < 2) continue;

        const hw = el.tags?.highway;
        if (hw === 'primary' || hw === 'secondary') {
          primary.push(coords);
        } else {
          regular.push(coords);
        }
        count++;
      }

      const roadData = { primary, regular };
      ROAD_CACHE.set(cacheKey, roadData);
      try {
        sessionStorage.setItem(`roads_${cacheKey}`, JSON.stringify(roadData));
      } catch {
        // storage quota exceeded or disabled
      }

      setRoads(roadData);
    };

    loadRoads().catch(() => {
      // Fail closed gracefully: road overlay is visual context only
    });

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [center, showRoads]);

  const primaryPathOptions = useMemo(() => ({
    color: '#94a3b8',
    weight: 2.5,
    opacity: 0.45,
  }), []);

  const regularPathOptions = useMemo(() => ({
    color: '#64748b',
    weight: 1.5,
    opacity: 0.35,
  }), []);

  if (!showRoads) return null;

  return (
    <>
      {roads.primary.length > 0 && (
        <Polyline positions={roads.primary} pathOptions={primaryPathOptions} />
      )}
      {roads.regular.length > 0 && (
        <Polyline positions={roads.regular} pathOptions={regularPathOptions} />
      )}
    </>
  );
}
