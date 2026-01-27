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
    """Oval-ish grain arcs: gaussian windowed sine grains across the clip (fixed)."""
    params=params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    n=max(1, int(round(duration*sr)))
    t=np.arange(n, dtype=np.float32)/float(sr) + np.float32(t0)
    rng=np.random.default_rng(int((t0*1e6)) & 0xffffffff)

    sig=np.zeros(n, dtype=np.float32)
    grains=int(params.get("grains", max(20, int(duration*60))))
    fmin=float(params.get("fmin", 300.0))*TF()
    fmax=float(params.get("fmax", 1200.0))*TF()
    for _ in range(grains):
        center=float(rng.uniform(0.0, duration))
        width=float(rng.uniform(0.003, 0.015))
        env=np.exp(-0.5*((t-(t0+center))/width)**2).astype(np.float32)
        f=float(rng.uniform(fmin, fmax))
        grain=np.sin(2*np.pi*np.float32(f)*(t)).astype(np.float32)
        sig += grain*env

    oval=(np.sin(2*np.pi*np.float32(0.20)*t)**2 + 0.8*np.cos(2*np.pi*np.float32(0.14)*t)**2).astype(np.float32)
    sig = sig*oval*np.float32(params.get("amp", 0.12))
    L=sig*(0.6+0.4*np.sin(2*np.pi*np.float32(0.18)*t)).astype(np.float32)
    R=sig*(0.6+0.4*np.cos(2*np.pi*np.float32(0.18)*t)).astype(np.float32)
    return np.stack([L,R], axis=0).astype(np.float32)
