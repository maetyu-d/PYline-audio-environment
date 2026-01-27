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
    params = params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    n=max(1, int(round(duration*sr)))
    rng=np.random.default_rng(int((t0*1e6)) & 0xffffffff)

    y=(rng.random(n, dtype=np.float32)-0.5)*np.float32(0.02)

    edits = int(params.get("edits", 12))
    for _ in range(max(1, edits)):
        start = int(rng.integers(0, max(1, n-64)))
        length = int(rng.integers(200, 1200))
        end = min(n, start+length)
        y[start:end] *= 0.0
        y[start] += np.float32(rng.uniform(0.7, 1.2))

    # smooth tiny
    win = int(params.get("smooth", 40))
    win = max(1, min(win, 2048))
    k = (np.ones(win, dtype=np.float32)/np.float32(win))
    y = np.convolve(y, k, mode="same").astype(np.float32)*np.float32(params.get("amp", 0.5))

    y = np.tanh(y*2.0).astype(np.float32)
    return np.stack([y,y], axis=0)
