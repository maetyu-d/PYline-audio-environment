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
    """Oval-ish breather: pulse thresholding through an 'oval' amplitude mask."""
    params=params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    n=max(1, int(round(duration*sr)))
    t=np.arange(n, dtype=np.float32)/float(sr) + np.float32(t0)

    rate0=float(params.get("rate0", 70.0))
    rate1=float(params.get("rate1", 20.0))
    lfo=float(params.get("lfo", 0.30))
    phase=np.cumsum((rate0 + rate1*np.sin(2*np.pi*np.float32(lfo)*t)).astype(np.float32))/np.float32(sr)
    pulses=(np.sin(2*np.pi*phase) > np.float32(0.99)).astype(np.float32)

    oval=(np.sin(2*np.pi*np.float32(0.40)*t)**2 + 0.7*np.cos(2*np.pi*np.float32(0.27)*t)**2).astype(np.float32)
    sig=pulses*oval*np.float32(params.get("amp", 0.35))
    k=np.ones(40, dtype=np.float32)/np.float32(40.0)
    sig=np.convolve(sig, k, mode="same").astype(np.float32)

    L=sig*(0.7+0.3*np.sin(2*np.pi*np.float32(0.20)*t)).astype(np.float32)
    R=sig*(0.7+0.3*np.cos(2*np.pi*np.float32(0.20)*t)).astype(np.float32)
    return np.stack([L,R], axis=0).astype(np.float32)
