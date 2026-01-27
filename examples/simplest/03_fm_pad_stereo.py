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
    """FM pad (stereo) with slow drift. Transpose-aware."""
    params = params or {}
    sr = int(sr)
    duration = float(duration)
    t0 = float(t0)
    n = max(1, int(round(sr * duration)))

    carrier = float(params.get("carrier_hz", 110.0)) * TF()
    ratio = float(params.get("ratio", 2.01))
    index = float(params.get("index", 3.5))
    drift = float(params.get("drift", 0.1))

    outL = [0.0] * n
    outR = [0.0] * n
    for i in range(n):
        t = i / sr
        env = (1.0 - math.exp(-t * 1.5)) * math.exp(-t * 0.35)

        f = carrier * (1.0 + 0.02 * math.sin((t0 + t) * drift * 2.0 * math.pi))
        mod = math.sin(2.0 * math.pi * (f * ratio) * t)

        sL = math.sin(2.0 * math.pi * f * t + index * mod)
        sR = math.sin(2.0 * math.pi * f * (t + 0.0007) + index * mod)

        outL[i] = env * sL * 0.9
        outR[i] = env * sR * 0.9
    return outL, outR
