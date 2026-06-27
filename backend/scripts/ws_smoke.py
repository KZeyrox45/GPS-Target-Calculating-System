"""WS smoke test — run standalone to verify the full data pipeline."""
import asyncio
import json
import sys
import urllib.request


def create_session() -> str:
    body = json.dumps({
        "target_type": "pedestrian",
        "algorithm": "both",
        "duration_s": 5,
        "update_rate_hz": 5,
        "seed": 42,
    }).encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/simulation/start",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    print(f"[REST] Session: {data['session_id']}")
    print(f"[REST] WS URL : {data['ws_url']}")
    return data["session_id"]


async def stream(session_id: str) -> None:
    import websockets
    uri = f"ws://localhost:8000/ws/tracking/{session_id}"
    print(f"[WS]  Connecting to {uri}")
    async with websockets.connect(uri) as ws:
        count = 0
        async for raw in ws:
            frame = json.loads(raw)
            if frame.get("type") == "simulation_end":
                print("[WS]  simulation_end received")
                break
            m = frame["metrics"]
            print(
                f"  step={frame['step']:3d}"
                f"  kf_err={m['kalman_error']:.2f}m"
                f"  ab_err={m['alpha_beta_error']:.2f}m"
                f"  kf_rmse={m['kalman_rmse']:.2f}m"
            )
            count += 1
            if count >= 8:
                print("[WS]  8 frames received — stopping early")
                break
    print("[WS]  Done.")


def main():
    try:
        sid = create_session()
        asyncio.run(stream(sid))
        print("\nSmoke test PASSED")
    except Exception as exc:
        print(f"\nSmoke test FAILED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
