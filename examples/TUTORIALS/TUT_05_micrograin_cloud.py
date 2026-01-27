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


# Tutorial 05: micrograin cloud (sparse, airy, microsound).
# Params:
# - density: grains per second
# - fmin, fmax: grain pitch range (transposes)
# - amp
def render(sr, duration, t0, params=None):
    params=params or {}
    n=max(1,int(sr*max(0.001,float(duration))))
    density=float(params.get("density",60.0))
    amp=float(params.get("amp",0.22))

    fmin=float(params.get("fmin",400.0))*TF()
    fmax=float(params.get("fmax",2400.0))*TF()
    lo=min(fmin,fmax); hi=max(fmin,fmax)

    outL=[0.0]*n
    outR=[0.0]*n

    expected=max(1,int(density*duration))
    for _ in range(expected):
        t = random.random()*duration
        i0 = int(t*sr)
        glen = int(sr * random.uniform(0.005, 0.03))
        if i0>=n: continue
        f = random.uniform(lo, hi)
        w = 2.0*math.pi*f
        pan = random.random()
        g = max(8, glen)
        for j in range(g):
            i=i0+j
            if i>=n: break
            x=j/(g-1)
            win=0.5-0.5*math.cos(2*math.pi*x)
            s=math.sin(w*(j/sr))*win*amp
            outL[i]+=s*(1-pan)
            outR[i]+=s*pan

    return outL,outR
