/**
 * Resolve a CSS custom property to its concrete value.
 * Leaflet SVG attributes and Chart.js canvas options cannot interpret
 * var() references, so colors must be resolved before use.
 */
export function cssVar(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}
