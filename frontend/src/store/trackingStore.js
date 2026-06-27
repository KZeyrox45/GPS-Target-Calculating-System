/**
 * trackingStore.js — Global state for the tracking system
 * Uses Zustand for lightweight, boilerplate-free state management.
 */
import { create } from 'zustand';

const MAX_HISTORY = 500;   // Maximum trajectory points kept in memory

const useTrackingStore = create((set) => ({
  // ── Connection state ──────────────────────────────────────────────────
  connected: false,
  sessionId: null,
  setConnected: (v) => set({ connected: v }),
  setSessionId: (id) => set({ sessionId: id }),

  // ── Current frame (latest tracking data) ─────────────────────────────
  currentFrame: null,
  setFrame: (frame) => set({ currentFrame: frame }),

  // ── Trajectory history (ring buffer) ─────────────────────────────────
  groundTruthHistory:  [],   // [{lat, lon}, ...]
  rawHistory:          [],
  kalmanHistory:       [],
  alphaBetaHistory:    [],

  appendHistories: (frame) => {
    const append = (arr, point) => {
      const next = [...arr, point];
      return next.length > MAX_HISTORY ? next.slice(next.length - MAX_HISTORY) : next;
    };
    set((s) => ({
      groundTruthHistory: append(s.groundTruthHistory, {
        lat: frame.ground_truth.lat,
        lon: frame.ground_truth.lon,
        alt: frame.ground_truth.alt ?? frame.ground_truth.up ?? 0,
      }),
      rawHistory: append(s.rawHistory, {
        lat: frame.raw_measurement.lat, lon: frame.raw_measurement.lon,
      }),
      kalmanHistory: append(s.kalmanHistory, {
        lat: frame.kalman.lat,
        lon: frame.kalman.lon,
        kf_up: frame.kalman.up ?? frame.kalman.alt ?? 0,
      }),
      alphaBetaHistory: append(s.alphaBetaHistory, {
        lat: frame.alpha_beta.lat, lon: frame.alpha_beta.lon,
      }),
    }));
  },

  clearHistory: () => set({
    groundTruthHistory: [], rawHistory: [],
    kalmanHistory: [], alphaBetaHistory: [],
  }),

  // ── Metrics history (for charts) ─────────────────────────────────────
  metricsHistory: [],   // [{step, kalman_rmse, alpha_beta_rmse, raw_error}, ...]

  appendMetrics: (frame) => {
    const entry = {
      step: frame.step,
      kalman_rmse:     frame.metrics.kalman_rmse,
      alpha_beta_rmse: frame.metrics.alpha_beta_rmse,
      raw_error:       frame.metrics.raw_error,
    };
    set((s) => ({
      metricsHistory: [
        ...s.metricsHistory.slice(-(MAX_HISTORY - 1)),
        entry,
      ],
    }));
  },

  clearMetrics: () => set({ metricsHistory: [] }),

  // ── Simulation config (mirrors SimulationStartRequest) ───────────────
  simConfig: {
    observer_lat: 10.762622,
    observer_lon: 106.660172,
    observer_alt: 10.0,
    target_type: 'pedestrian',
    algorithm: 'both',
    duration_s: 120.0,
    update_rate_hz: 10.0,
    alpha: 0.4,
    seed: null,
    boundary_radius_m: 400,
  },
  setSimConfig: (patch) => set((s) => ({
    simConfig: { ...s.simConfig, ...patch },
  })),

  // ── Simulation running state ──────────────────────────────────────────
  isRunning: false,
  setIsRunning: (v) => set({ isRunning: v }),
  simulationEnded: false,
  setSimulationEnded: (v) => set({ simulationEnded: v }),

  // ── Visible layers toggle ─────────────────────────────────────────────
  showGroundTruth: true,
  showRaw:         true,
  showKalman:      true,
  showAlphaBeta:   true,
  toggleLayer: (name) => set((s) => ({ [name]: !s[name] })),

  // ── FPS counter ───────────────────────────────────────────────────────
  fps: 0,
  setFps: (v) => set({ fps: v }),

  // ── Full reset ────────────────────────────────────────────────────────
  reset: () => set({
    connected: false, sessionId: null, currentFrame: null,
    groundTruthHistory: [], rawHistory: [], kalmanHistory: [], alphaBetaHistory: [],
    metricsHistory: [], isRunning: false, simulationEnded: false, fps: 0,
  }),
}));

export default useTrackingStore;
