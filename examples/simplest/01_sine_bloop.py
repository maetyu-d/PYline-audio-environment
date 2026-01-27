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


def render(sr, duration, t0, params=None):
    params = params or {}
    n = int(sr * duration)
    outL = []
    outR = []
    base = float(params.get("base_hz", 220.0)) * TF()
    wob = float(params.get("wobble", 0.7))
    det = float(params.get("detune_hz", 0.8)) * TF()
    f0 = base + 110.0 * math.sin(t0 * wob)  # context-aware by timeline position

    for i in range(n):
        t = i / sr
        env = math.exp(-6.0*t) * (1.0 - math.exp(-90.0*t))
        a = math.sin(2*math.pi*f0*t)
        b = math.sin(2*math.pi*(f0+det)*t)
        s = 0.6*a + 0.4*b
        v = env * s
        outL.append(v)
        outR.append(v)
    return outL, outR