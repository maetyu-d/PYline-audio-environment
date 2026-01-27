import math

# --- transpose helper (semitones) ---
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


import random

def render(sr, duration, t0, params=None):
    """Wind-ish filtered noise with slow gusting. Returns stereo with subtle offset."""
    params = params or {}
    sr = int(sr)
    duration = float(duration)
    t0 = float(t0)
    n = max(1, int(round(sr * duration)))

    seed = int(params.get("seed", 2))
    tilt = float(params.get("tilt", 0.98))  # 0.9..0.999; higher = more low freq
    amp = float(params.get("amp", 0.5))

    random.seed(seed + int(t0 * 10))

    y = 0.0
    out = [0.0] * n
    for i in range(n):
        x = random.uniform(-1.0, 1.0)
        y = tilt * y + (1.0 - tilt) * x
        t = i / sr
        g = 0.5 + 0.5 * math.sin(2.0 * math.pi * (0.12 + 0.02 * math.sin(t0 * 0.1)) * t)
        out[i] = amp * g * y

    # subtle stereo decorrelation via a tiny delay
    d = max(1, min(n - 1, int(sr * 0.0008))) if n > 1 else 0
    L = out
    R = out[:] if d == 0 else ([0.0] * d + out[:-d])
    return L, R
