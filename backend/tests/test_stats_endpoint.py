"""
test_stats_endpoint.py - Tests for SimulationEngine.get_stats() and stats REST endpoint
========================================================================================
Verifies the /api/simulation/stats/{session_id} endpoint
and the underlying get_stats() method of SimulationEngine.
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.simulation.target_simulator import SimulationConfig, SimulationEngine

# ---------------------------------------------------------------------------
# Unit tests: SimulationEngine.get_stats()
# ---------------------------------------------------------------------------

class TestSimulationEngineGetStats:
    """Tests for the get_stats() method on SimulationEngine."""

    def _make_engine(self, target_type: str = "pedestrian", seed: int = 42) -> SimulationEngine:
        config = SimulationConfig(
            target_type=target_type,
            duration_s=5.0,
            update_rate_hz=10.0,
            seed=seed,
        )
        return SimulationEngine(config)

    @staticmethod
    def _run_engine(engine: SimulationEngine, n_steps: int) -> None:
        """Run engine for n_steps synchronously (bypasses asyncio.sleep pacing)."""
        async def _run():
            count = 0
            async for _ in engine.run():
                count += 1
                if count >= n_steps:
                    engine.stop()
        asyncio.run(_run())

    def test_get_stats_before_run_returns_zero_steps(self):
        engine = self._make_engine()
        stats = engine.get_stats()
        assert stats["steps"] == 0
        assert stats["kalman_rmse_m"] is None
        assert stats["alpha_beta_rmse_m"] is None
        assert stats["raw_rmse_m"] is None
        assert stats["duration_s"] == 0.0
        assert stats["target_type"] == "pedestrian"

    def test_get_stats_after_run_has_correct_step_count(self):
        engine = self._make_engine(target_type="pedestrian", seed=42)
        self._run_engine(engine, n_steps=10)
        stats = engine.get_stats()
        assert stats["steps"] == 10

    def test_get_stats_rmse_are_positive_floats(self):
        engine = self._make_engine(target_type="motorcycle", seed=7)
        self._run_engine(engine, n_steps=10)
        stats = engine.get_stats()
        assert stats["kalman_rmse_m"] > 0.0
        assert stats["alpha_beta_rmse_m"] > 0.0
        assert stats["raw_rmse_m"] > 0.0

    def test_get_stats_rmse_below_spec_threshold(self):
        """Running RMSE must stay below 5 m (thesis specification)."""
        engine = self._make_engine(target_type="pedestrian", seed=42)
        SPEC_THRESHOLD_M = 5.0
        self._run_engine(engine, n_steps=30)
        stats = engine.get_stats()
        assert stats["kalman_rmse_m"] < SPEC_THRESHOLD_M, (
            f"Kalman RMSE {stats['kalman_rmse_m']:.3f} >= {SPEC_THRESHOLD_M} m"
        )
        assert stats["alpha_beta_rmse_m"] < SPEC_THRESHOLD_M, (
            f"Alpha-beta RMSE {stats['alpha_beta_rmse_m']:.3f} >= {SPEC_THRESHOLD_M} m"
        )

    def test_get_stats_duration_matches_steps(self):
        engine = self._make_engine(target_type="drone", seed=99)
        self._run_engine(engine, n_steps=20)
        stats = engine.get_stats()
        expected_duration = 20 / 10.0
        assert abs(stats["duration_s"] - expected_duration) < 0.01

    def test_get_stats_target_type_preserved(self):
        for ttype in ("pedestrian", "motorcycle", "drone"):
            engine = self._make_engine(target_type=ttype)
            assert engine.get_stats()["target_type"] == ttype

    def test_get_stats_raw_rmse_greater_than_filtered(self):
        """Filtered RMSE should generally be less than raw measurement RMSE."""
        engine = self._make_engine(target_type="pedestrian", seed=42)
        self._run_engine(engine, n_steps=50)
        stats = engine.get_stats()
        assert stats["kalman_rmse_m"] < stats["raw_rmse_m"] or \
               stats["alpha_beta_rmse_m"] < stats["raw_rmse_m"], (
            "Neither filter reduced RMSE below raw measurement"
        )


# ---------------------------------------------------------------------------
# Integration tests: GET /api/simulation/stats/{session_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestStatsEndpoint:
    """Integration tests for the stats REST endpoint."""

    async def _start_session(self, client: AsyncClient, target_type: str = "pedestrian") -> str:
        payload = {
            "observer_lat": 10.762622,
            "observer_lon": 106.660172,
            "observer_alt": 10.0,
            "target_type": target_type,
            "algorithm": "both",
            "duration_s": 30.0,
            "update_rate_hz": 10.0,
            "seed": 42,
        }
        resp = await client.post("/api/simulation/start", json=payload)
        assert resp.status_code == 200
        return resp.json()["session_id"]

    async def test_stats_returns_404_for_unknown_session(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/simulation/stats/nonexistent-session-id")
        assert resp.status_code == 404
        assert "Session not found" in resp.json()["detail"]

    async def test_stats_returns_200_for_active_session(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            session_id = await self._start_session(client)
            resp = await client.get(f"/api/simulation/stats/{session_id}")
        assert resp.status_code == 200

    async def test_stats_response_has_required_fields(self):
        required_fields = {
            "steps", "kalman_rmse_m", "alpha_beta_rmse_m",
            "raw_rmse_m", "duration_s", "target_type",
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            session_id = await self._start_session(client, target_type="motorcycle")
            resp = await client.get(f"/api/simulation/stats/{session_id}")
        data = resp.json()
        assert required_fields.issubset(data.keys()), (
            f"Missing fields: {required_fields - data.keys()}"
        )

    async def test_stats_new_session_has_zero_steps(self):
        """Immediately after creation (before WS connection), steps should be 0."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            session_id = await self._start_session(client)
            resp = await client.get(f"/api/simulation/stats/{session_id}")
        data = resp.json()
        assert data["steps"] == 0
        assert data["kalman_rmse_m"] is None
        assert data["alpha_beta_rmse_m"] is None

    async def test_stats_target_type_matches_request(self):
        for ttype in ("pedestrian", "motorcycle", "drone"):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                session_id = await self._start_session(client, target_type=ttype)
                resp = await client.get(f"/api/simulation/stats/{session_id}")
            assert resp.json()["target_type"] == ttype


# ---------------------------------------------------------------------------
# Integration tests: GET /api/simulation/export/{session_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestExportEndpoint:
    """Integration tests for the CSV export REST endpoint."""

    async def _start_session(self, client: AsyncClient, target_type: str = "pedestrian") -> str:
        payload = {
            "observer_lat": 10.762622,
            "observer_lon": 106.660172,
            "observer_alt": 10.0,
            "target_type": target_type,
            "algorithm": "both",
            "duration_s": 30.0,
            "update_rate_hz": 10.0,
            "seed": 42,
        }
        resp = await client.post("/api/simulation/start", json=payload)
        assert resp.status_code == 200
        return resp.json()["session_id"]

    async def test_export_returns_404_for_unknown_session(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/simulation/export/nonexistent-session-id")
        assert resp.status_code == 404
        assert "Session not found" in resp.json()["detail"]

    async def test_export_active_session_no_frames_returns_204(self):
        """Immediately after creation, no frames recorded → 204 No Content."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            session_id = await self._start_session(client)
            resp = await client.get(f"/api/simulation/export/{session_id}")
        assert resp.status_code == 204

    async def test_export_content_type_is_csv_when_frames_present(self):
        """Once frames are buffered, response must have Content-Type text/csv."""
        import uuid

        from app.routers.simulation import _sessions
        from app.simulation.target_simulator import SimulationConfig, SimulationEngine

        config = SimulationConfig(target_type="pedestrian", seed=42,
                                   duration_s=5.0, update_rate_hz=10.0)
        engine = SimulationEngine(config)
        # Run 5 steps to populate frame buffer
        async def _run():
            count = 0
            async for _ in engine.run():
                count += 1
                if count >= 5:
                    engine.stop()
        await _run()

        sid = str(uuid.uuid4())
        _sessions[sid] = engine
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/api/simulation/export/{sid}")
            assert resp.status_code == 200
            assert "text/csv" in resp.headers["content-type"]
        finally:
            _sessions.pop(sid, None)

    async def test_export_csv_has_header_row(self):
        """CSV must contain expected column headers."""
        import uuid

        from app.routers.simulation import _sessions
        from app.simulation.target_simulator import SimulationConfig, SimulationEngine

        config = SimulationConfig(target_type="pedestrian", seed=42,
                                   duration_s=5.0, update_rate_hz=10.0)
        engine = SimulationEngine(config)
        async def _run():
            count = 0
            async for _ in engine.run():
                count += 1
                if count >= 3:
                    engine.stop()
        await _run()

        sid = str(uuid.uuid4())
        _sessions[sid] = engine
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/api/simulation/export/{sid}")
            assert resp.status_code == 200
            first_line = resp.text.splitlines()[0]
            assert "step" in first_line
            assert "kalman_east" in first_line
            assert "ab_east" in first_line
        finally:
            _sessions.pop(sid, None)

    async def test_export_csv_row_count_matches_steps(self):
        """Number of data rows must equal the number of simulation steps run."""
        import uuid

        from app.routers.simulation import _sessions
        from app.simulation.target_simulator import SimulationConfig, SimulationEngine

        n_steps = 8
        config = SimulationConfig(target_type="motorcycle", seed=7,
                                   duration_s=5.0, update_rate_hz=10.0)
        engine = SimulationEngine(config)
        async def _run():
            count = 0
            async for _ in engine.run():
                count += 1
                if count >= n_steps:
                    engine.stop()
        await _run()

        sid = str(uuid.uuid4())
        _sessions[sid] = engine
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get(f"/api/simulation/export/{sid}")
            assert resp.status_code == 200
            lines = [ln for ln in resp.text.splitlines() if ln.strip()]
            # 1 header + n_steps data rows
            assert len(lines) == n_steps + 1, f"Expected {n_steps + 1} lines, got {len(lines)}"
        finally:
            _sessions.pop(sid, None)
