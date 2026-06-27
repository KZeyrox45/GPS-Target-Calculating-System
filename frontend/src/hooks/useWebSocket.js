/**
 * useWebSocket.js — WebSocket connection manager
 * Handles connect, auto-reconnect on drop, and message dispatch to the store.
 */
import { useRef, useCallback } from 'react';
import useTrackingStore from '../store/trackingStore';

const RECONNECT_DELAY_MS = 2000;

export function useWebSocket() {
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const { setConnected, setFrame, appendHistories, appendMetrics, setFps, setIsRunning, setSimulationEnded } = useTrackingStore();

  // FPS measurement
  const fpsCountRef = useRef(0);
  const fpsTimerRef = useRef(null);

  const startFpsCounter = useCallback(() => {
    fpsTimerRef.current = setInterval(() => {
      setFps(fpsCountRef.current);
      fpsCountRef.current = 0;
    }, 1000);
  }, [setFps]);

  const stopFpsCounter = useCallback(() => {
    clearInterval(fpsTimerRef.current);
    setFps(0);
  }, [setFps]);

  const connect = useCallback((sessionId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // Use a relative ws:// URL so Vite's proxy handles it.
    // Vite proxies /ws → ws://localhost:8000, avoiding CORS on the WS upgrade.
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/tracking/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      startFpsCounter();
      console.log('[WS] Connected to session', sessionId);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // Simulation finished signal
      if (data.type === 'simulation_end') {
        setIsRunning(false);
        setSimulationEnded(true);
        stopFpsCounter();
        return;
      }

      fpsCountRef.current += 1;
      setFrame(data);
      appendHistories(data);
      appendMetrics(data);
    };

    ws.onclose = (event) => {
      setConnected(false);
      stopFpsCounter();
      console.log('[WS] Disconnected, code:', event.code);
    };

    ws.onerror = (err) => {
      console.error('[WS] Error:', err);
    };
  }, [setConnected, setFrame, appendHistories, appendMetrics, setFps, setIsRunning, setSimulationEnded, startFpsCounter, stopFpsCounter]);

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current);
    stopFpsCounter();
    if (wsRef.current) {
      wsRef.current.close(1000, 'User stopped simulation');
      wsRef.current = null;
    }
    setConnected(false);
    setIsRunning(false);
  }, [setConnected, setIsRunning, stopFpsCounter]);

  return { connect, disconnect };
}
