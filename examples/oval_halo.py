import numpy as np
import math

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
    """Oval-ish halo: slow drifting sine with oval envelope (fixed)."""
    params=params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    n=max(1, int(round(duration*sr)))
    t=np.arange(n, dtype=np.float32)/float(sr) + np.float32(t0)

    a=0.5+0.5*np.sin(2*np.pi*np.float32(0.30)*t)
    b=0.5+0.5*np.cos(2*np.pi*np.float32(0.20)*t)
    env=(a*b)**np.float32(params.get("env_pow", 0.8))

    base=float(params.get("base", 220.0))*TF()
    drift=float(params.get("drift", 40.0))
    f=(base + drift*np.sin(2*np.pi*np.float32(0.10)*t)).astype(np.float32)
    phase=np.cumsum(f)/np.float32(sr)
    wave=np.sin(2*np.pi*phase).astype(np.float32)

    sig=wave*env*np.float32(params.get("amp", 0.25))
    L=sig*(0.6+0.4*np.sin(2*np.pi*np.float32(0.15)*t)).astype(np.float32)
    R=sig*(0.6+0.4*np.cos(2*np.pi*np.float32(0.15)*t)).astype(np.float32)
    return np.stack([L,R], axis=0).astype(np.float32)
