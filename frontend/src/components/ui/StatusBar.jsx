import React from 'react';
import useTrackingStore from '../../store/trackingStore';

export default function StatusBar() {
  const { connected, isRunning, fps, sessionId, simulationEnded } = useTrackingStore();

  const showWsStatus = sessionId !== null && sessionId !== undefined;

  return (
    <div className="flex items-center gap-2">
      {isRunning && (
        <span className="badge badge-running">
          <span className="badge-dot pulse" />
          {fps} Hz
        </span>
      )}
      {showWsStatus && (
        <span className={`badge ${connected ? 'badge-connected' : simulationEnded ? 'badge-idle' : 'badge-disconnected'}`}>
          <span className="badge-dot" />
          {connected ? 'Connected' : simulationEnded ? 'Completed' : 'Disconnected'}
        </span>
      )}
    </div>
  );
}
