# Frontend (React 19 + Vite)

## Setup

```bash
cd frontend
npm install          # First time
npm run dev          # Dev server on :5173
npm run build        # Production build
npm run lint         # ESLint check
```

## Project Structure

```
frontend/
├── src/
│   ├── main.jsx                 # Entry point
│   ├── App.jsx                  # Router setup
│   ├── App.css                  # Global styles
│   ├── index.css                # Reset + base styles
│   ├── pages/
│   │   ├── HomePage.jsx         # Landing page
│   │   ├── TrackingPage.jsx     # Real-time tracking view
│   │   ├── StaticCalcPage.jsx   # Phase 1 calculator
│   │   └── ComparisonPage.jsx   # Filter comparison
│   ├── components/
│   │   ├── charts/
│   │   │   ├── AltitudeChart.jsx
│   │   │   └── ErrorMetricsChart.jsx
│   │   ├── controls/
│   │   │   ├── SimulationPanel.jsx
│   │   │   └── LayerControl.jsx
│   │   ├── map/
│   │   │   ├── TrackingMap.jsx
│   │   │   ├── TargetMarker.jsx
│   │   │   └── TrajectoryPolyline.jsx
│   │   └── ui/
│   │       ├── CoordDisplay.jsx
│   │       └── StatusBar.jsx
│   ├── store/
│   │   └── trackingStore.js    # Zustand store
│   └── hooks/
│       └── useWebSocket.js     # WebSocket connection hook
├── vite.config.js              # Proxy config + build
├── eslint.config.js            # Flat config ESLint
├── package.json
└── index.html
```

## Tech Stack

| Library | Purpose |
|---------|---------|
| React 19 | UI framework |
| Vite 8 | Build tool + dev server |
| Zustand | State management (lightweight) |
| Leaflet | Map rendering (OpenStreetMap) |
| Recharts | Charts (altitude, error metrics) |
| React Router | Page routing |

## Key Components

### TrackingMap (Leaflet)
- OpenStreetMap tile layer
- Observer marker (green)
- Target markers (red for raw, blue for Kalman, purple for alpha-beta)
- Trajectory polylines (3 layers, independently toggleable)
- Uncertainty circle around Kalman estimate

### useWebSocket Hook
- Connects to `/ws/tracking/{session_id}` (proxied through Vite to ws://localhost:8000)
- Parses incoming JSON, updates Zustand store
- Handles reconnection and cleanup

### trackingStore (Zustand)
- Ring buffer: `MAX_HISTORY = 500` points per layer
- State: observer position, target positions (raw/kalman/alphabeta), uncertainty, FPS
- Actions: addFrame, clearHistory, setFps

### LayerControl
- Toggle visibility of raw/kalman/alphabeta layers
- Toggle uncertainty circle
- Toggle observer marker

## Vite Proxy Config

```js
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
```

## Linting

- ESLint flat config (`eslint.config.js`)
- `no-unused-vars` ignores names starting with uppercase/underscore
- Run: `npm run lint`

## Build

```bash
npm run build  # Output: frontend/dist/
```

Build warning about chunk size (588 kB) is expected due to Leaflet + Recharts.

## All .jsx (NOT TypeScript)

Despite `@types/react` being a dev dependency, the project uses plain JSX with no TypeScript compilation. No `tsconfig.json` exists.
