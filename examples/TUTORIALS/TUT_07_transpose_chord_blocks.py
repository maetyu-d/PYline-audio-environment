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


# Tutorial 07: glass chord blocks (transpose is harmony control).
# Params: root_hz, block_rate (per second), amp
def render(sr, duration, t0, params=None):
    params=params or {}
    n=max(1,int(sr*max(0.001,float(duration))))
    amp=float(params.get("amp",0.25))
    root=float(params.get("root_hz",220.0))*TF()
    block_rate=max(0.1,float(params.get("block_rate",2.0)))

    ratios=[1.0, 5/4, 3/2, 2.0]
    freqs=[root*r for r in ratios]

    outL=[0.0]*n
    outR=[0.0]*n

    for i in range(n):
        t=i/sr
        phase=(t*block_rate)%1.0
        env=math.exp(-phase*7.0)
        v=0.0
        for f in freqs:
            v += math.sin(2*math.pi*f*t)
        v = (v/len(freqs))*env*amp
        outL[i]=v*0.95
        outR[i]=v*1.05
    return outL,outR
