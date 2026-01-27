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


# Tutorial 01: the simplest pitched clip.
# - Follows CLIP_TRANSPOSE via TF()
# - Params: freq (Hz), amp (0..1)
def render(sr, duration, t0, params=None):
    params = params or {}
    n = max(1, int(sr * max(0.001, float(duration))))
    amp = float(params.get("amp", 0.25))
    freq = float(params.get("freq", 220.0)) * TF()
    outL = [0.0]*n
    outR = [0.0]*n
    ph = 0.0
    inc = 2.0*math.pi*freq / sr
    for i in range(n):
        v = math.sin(ph) * amp
        outL[i] = v
        outR[i] = v
        ph += inc
    return outL, outR
