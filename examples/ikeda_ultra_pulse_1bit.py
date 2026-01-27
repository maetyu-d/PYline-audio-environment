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
    bpm = max(1.0, _bpm(params, 180.0))
    density = float(params.get("density", 0.35))
    levels = int(params.get("levels", 16))
    hi = float(params.get("hi", 0.95))
    lo = float(params.get("lo", -0.95))

    n = max(1, int(round(duration*sr)))
    t = (np.arange(n, dtype=np.float32)/float(sr)) + np.float32(t0)

    spb = 60.0/bpm
    step = spb/8.0  # 32nd
    phase = (t/step) % 1.0
    pulse = (phase < 0.03).astype(np.float32)

    cell = np.floor(t/step).astype(np.int64)
    drop = ((cell*1103515245 + 12345) & 0xffffffff) / np.float32(2**32)
    keep = (drop < np.float32(density)).astype(np.float32)

    x = pulse * keep
    pol = ((cell & 1)*2 - 1).astype(np.float32)
    sig = x * pol * np.float32(0.9)

    if levels > 1:
        sig = np.round((sig+1.0)*0.5*(levels-1))/(levels-1)
        sig = sig*2.0 - 1.0

    sig = np.clip(sig, lo, hi).astype(np.float32)
    return np.stack([sig, sig], axis=0)
