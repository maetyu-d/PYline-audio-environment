import numpy as np

def TF(semi=None):
    """Transpose factor: 2**(semitones/12). Reads CLIP_TRANSPOSE or _PARAMS['transpose']."""
    try:
        s = float(CLIP_TRANSPOSE if semi is None else semi)
    except Exception:
        try:
            s = float(_PARAMS.get("transpose", 0.0)) if semi is None else float(semi)
        except Exception:
            s = 0.0
    return 2.0 ** (s / 12.0)

def _bpm(params, default=120.0):
    try:
        return float(CLIP_BPM)
    except Exception:
        pass
    try:
        return float((params or {}).get("bpm", default))
    except Exception:
        return float(default)

def render(sr, duration, t0, params=None):
    sr=int(sr); n=max(1, int(float(duration)*sr))
    z=np.zeros(n, dtype=np.float32)
    return np.stack([z,z], axis=0)

# CONTROL ENVELOPE: emits continuous parameter curves.
# Returns: [{"track":"Track 1","param":"gain","points":[[t,val], ...]}]
def control(sr, duration, t0, params=None):
    params = params or {}
    track = params.get("track", "Track 1")
    g0 = float(params.get("g0", 0.0))
    g1 = float(params.get("g1", 1.0))
    t1 = float(params.get("t1", max(0.01, float(duration)*0.5)))
    pts = [[0.0, g0], [t1, g1], [float(duration), g1]]
    return [{"track": track, "param": "gain", "points": pts}]
