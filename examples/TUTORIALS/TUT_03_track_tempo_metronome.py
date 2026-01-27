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


# Tutorial 03: metronome locked to the track tempo.
# Uses CLIP_BPM if available, otherwise params["bpm"].
# Params: subdiv (1=quarters, 2=eighths, 4=sixteenths), amp
def render(sr, duration, t0, params=None):
    params = params or {}
    bpm = float(params.get("bpm", 120.0))
    try:
        bpm = float(CLIP_BPM)
    except Exception:
        pass
    bpm = max(1.0, bpm)

    subdiv = max(1, int(params.get("subdiv", 2)))
    amp = float(params.get("amp", 0.6))
    n = max(1, int(sr * max(0.001, float(duration))))

    spb = 60.0 / bpm
    step = spb / subdiv

    outL=[0.0]*n
    outR=[0.0]*n

    t=0.0
    while t < duration + 1e-9:
        i = int(t * sr)
        if 0 <= i < n:
            outL[i] += amp
            outR[i] += amp
        t += step

    # soften clicks
    a = math.exp(-1.0/(sr*0.02))
    y=0.0
    for i in range(n):
        y = outL[i] + a*y
        outL[i]=y
        outR[i]=y
    return outL,outR
