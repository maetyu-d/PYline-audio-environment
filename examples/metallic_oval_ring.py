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
    t=np.linspace(0.0, duration, n, endpoint=False, dtype=np.float32)

    freqs=[float(f) * TF() for f in params.get("freqs", [430,612,905,1201])]
    y=np.zeros(n, dtype=np.float32)
    for f in freqs:
        y += np.sin(2*np.pi*np.float32(f)*t).astype(np.float32)
    y *= np.float32(0.25)

    # oval amplitude modulation
    oval = (np.sin(2*np.pi*np.float32(0.25)*t)**2 + np.cos(2*np.pi*np.float32(0.17)*t)**2).astype(np.float32)
    y *= (oval**np.float32(params.get("oval_pow", 1.2))).astype(np.float32)

    L = y*(np.float32(0.55)+np.float32(0.45)*np.sin(2*np.pi*np.float32(0.11)*t)).astype(np.float32)
    R = y*(np.float32(0.55)+np.float32(0.45)*np.cos(2*np.pi*np.float32(0.11)*t)).astype(np.float32)
    return np.stack([L,R], axis=0)
