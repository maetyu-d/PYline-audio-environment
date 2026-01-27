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
    """Microtonal stepped melody (non-12TET-ish). Stereo + app signature."""
    params = params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    n=max(1, int(round(sr*duration)))

    rng = np.random.default_rng(int((t0*1e6)) & 0xffffffff)
    steps = np.array(params.get("steps", [0.0, 1.5, 3.2, 5.1, 7.0]), dtype=np.float32)
    base = float(params.get("base", 220.0)) * TF()
    step_len = max(16, int(float(params.get("step_s", 0.5)) * sr))
    amp = float(params.get("amp", 0.30))

    y = np.zeros(n, dtype=np.float32)
    for i in range(0, n, step_len):
        L = min(step_len, n - i)
        st = float(rng.choice(steps))
        freq = base * (2.0 ** (st / 12.0))
        t = (np.arange(L, dtype=np.float32) / float(sr))
        env = np.exp(-t * float(params.get("decay", 1.5))).astype(np.float32)
        y[i:i+L] += (np.sin(2*np.pi*np.float32(freq)*t).astype(np.float32) * env * np.float32(amp))

    y = np.tanh(y).astype(np.float32)
    # gentle stereo movement
    t = (np.arange(n, dtype=np.float32)/float(sr)) + np.float32(t0)
    L = y * (0.75 + 0.25*np.sin(2*np.pi*np.float32(0.12)*t)).astype(np.float32)
    R = y * (0.75 + 0.25*np.cos(2*np.pi*np.float32(0.12)*t)).astype(np.float32)
    return np.stack([L,R], axis=0).astype(np.float32)
