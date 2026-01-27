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
    """Oval-ish click cloud: sparse clicks smeared, shaped by an oval mask (fixed)."""
    params=params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    n=max(1, int(round(duration*sr)))
    t=np.arange(n, dtype=np.float32)/float(sr) + np.float32(t0)

    rng=np.random.default_rng(int((t0*1e6)) & 0xffffffff)
    clicks=np.zeros(n, dtype=np.float32)
    count=int(params.get("count", max(60, int(duration*120))))
    for _ in range(count):
        idx=int(rng.integers(0,n))
        clicks[idx]+=np.float32(rng.uniform(0.3,1.0))

    klen=max(16, int(sr*0.004))
    k=np.exp(-np.linspace(0,1,klen,endpoint=False,dtype=np.float32)*8.0).astype(np.float32)
    clicks=np.convolve(clicks, k, mode="same").astype(np.float32)

    oval=(np.sin(2*np.pi*np.float32(0.30)*t)**2 + 0.6*np.cos(2*np.pi*np.float32(0.19)*t)**2).astype(np.float32)
    sig=clicks*oval*np.float32(params.get("amp", 0.30))
    L=sig*(0.65+0.35*np.sin(2*np.pi*np.float32(0.16)*t)).astype(np.float32)
    R=sig*(0.65+0.35*np.cos(2*np.pi*np.float32(0.16)*t)).astype(np.float32)
    return np.stack([L,R], axis=0).astype(np.float32)
