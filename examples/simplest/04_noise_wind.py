import random, math

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
    seed = int(params.get("seed", 2))
    tilt = float(params.get("tilt", 0.98))  # 0.9..0.999; higher = more low freq
    amp = float(params.get("amp", 0.5))
    random.seed(seed + int(t0*10))

    y = 0.0
    out = []
    for i in range(n):
        # one-pole lowpass noise = wind-ish
        x = random.uniform(-1, 1)
        y = tilt*y + (1-tilt)*x
        # slow gust
        t = i/sr
        g = 0.5 + 0.5*math.sin(2*math.pi*(0.12 + 0.02*math.sin(t0*0.1))*t)
        out.append(amp * g * y)
    return out