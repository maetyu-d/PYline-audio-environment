# CONTROL: Restart other track (fixed, app-compatible)
#
# Provides:
# - render(sr, duration, t0, params): silence (satisfies engine)
# - events(sr, duration, t0, params): emits restart event(s)
#
# Params:
# - track: target track name (default "Track 2")
# - at: trigger time in seconds relative to clip start (default 0.0)
# - from: restart point in target track local seconds (default 0.0)
# - hard: True/False (default False)
# - tail: tail fade seconds when hard=False (default 0.75)

import numpy as np

def render(sr, duration, t0, params=None):
    sr = int(sr)
    n = max(1, int(float(duration) * sr))
    z = np.zeros(n, dtype=np.float32)
    return np.stack([z, z], axis=0)

def events(sr, duration, t0, params=None):
    params = params or {}
    target = params.get("track", "Track 2")
    at = float(params.get("at", 0.0))
    frm = float(params.get("from", 0.0))
    hard = bool(params.get("hard", False))
    tail = float(params.get("tail", 0.75))

    # Clamp
    dur = float(duration)
    if at < 0.0: at = 0.0
    if at > dur: at = dur

    return [{
        "type": "restart_track",
        "track": target,
        "at": at,
        "from": frm,
        "hard": hard,
        "tail": tail
    }]
