/**
 * useWebSocket.js - WebSocket connection manager
 * Handles connect, auto-reconnect on drop, and message dispatch to the store.
 */
import { useRef, useCallback, useEffect } from 'react';
import useTrackingStore from '../store/trackingStore';

const RECONNECT_DELAY_MS = 2000;

export function useWebSocket() {
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const intentionalCloseRef = useRef(false);
  const connectRef = useRef(null);
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

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    clearTimeout(reconnectTimer.current);
    stopFpsCounter();
    if (wsRef.current) {
      const ws = wsRef.current;
      wsRef.current = null;
      ws.onclose = null;
      ws.close(1000, 'User stopped simulation');
    }
    setConnected(false);
    setIsRunning(false);
  }, [setConnected, setIsRunning, stopFpsCounter]);

  const scheduleReconnect = useCallback((sessionId) => {
    clearTimeout(reconnectTimer.current);
    reconnectTimer.current = setTimeout(() => {
      connectRef.current?.(sessionId);
    }, RECONNECT_DELAY_MS);
  }, []);

  const connect = useCallback((sessionId) => {
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return;
    clearTimeout(reconnectTimer.current);
    intentionalCloseRef.current = false;

    // Close any stale socket before opening a new one.
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    // Use a relative ws:// URL so Vite's proxy handles it.
    // Vite proxies /ws -> ws://localhost:8000, avoiding CORS on the WS upgrade.
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
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      // Simulation finished signal
      if (data.type === 'simulation_end') {
        intentionalCloseRef.current = true;
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
      if (wsRef.current !== ws) return;
      wsRef.current = null;
      setConnected(false);
      stopFpsCounter();
      console.log('[WS] Disconnected, code:', event.code);
      if (!intentionalCloseRef.current && event.code !== 1000) {
        console.log('[WS] Reconnecting in', RECONNECT_DELAY_MS, 'ms');
        scheduleReconnect(sessionId);
      }
    };

    ws.onerror = (err) => {
      console.error('[WS] Error:', err);
    };
  }, [setConnected, setFrame, appendHistories, appendMetrics, setIsRunning, setSimulationEnded, startFpsCounter, stopFpsCounter, scheduleReconnect]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  return { connect, disconnect };
}
