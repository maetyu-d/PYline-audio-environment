import math, random
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


# Tutorial 02: one impulse with a decay envelope.
# Params:
# - amp: click level
# - tone_hz: optional tiny pitched tick (transposes)
# - decay: seconds
def render(sr, duration, t0, params=None):
    params = params or {}
    n = max(1, int(sr * max(0.001, float(duration))))
    amp = float(params.get("amp", 0.7))
    decay = max(0.001, float(params.get("decay", min(0.15, duration))))
    tone = float(params.get("tone_hz", 0.0))
    if tone > 0.0:
        tone *= TF()

    outL = [0.0]*n
    outR = [0.0]*n

    # one-sample impulse
    outL[0] = amp
    outR[0] = amp

    # exponential decay (simple one-pole)
    a = math.exp(-1.0/(sr*decay))
    y = 0.0
    ph = 0.0
    inc = 2.0*math.pi*tone/sr if tone>0 else 0.0
    for i in range(n):
        x = outL[i] + (random.random()*2-1)*0.02
        y = x + a*y
        v = y
        if tone>0:
            v += math.sin(ph)*0.15
            ph += inc
        outL[i]=v
        outR[i]=v
    return outL, outR
