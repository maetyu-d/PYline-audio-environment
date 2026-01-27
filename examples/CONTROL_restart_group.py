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

# CONTROL RESTART GROUP
# Emits restart_group events at a fixed interval.
def events(sr, duration, t0, params=None):
    params = params or {}
    group = params.get("group", "Perc")
    every = float(params.get("every", 2.0))
    hard = bool(params.get("hard", False))
    jitter = float(params.get("jitter", 0.0))
    prob = float(params.get("prob", 1.0))

    evs = []
    t = 0.0
    dur = float(duration)
    if every <= 1e-9:
        every = dur + 1.0
    while t <= dur + 1e-9:
        evs.append({
            "type":"restart_group",
            "group": group,
            "at": float(t),
            "hard": hard,
            "jitter": jitter,
            "prob": prob
        })
        t += every
    return evs
