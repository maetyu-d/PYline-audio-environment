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


# Tutorial 06: Oval-ish skipping loop illusion (buffer jumps).
# Params:
# - base_hz: underlying pitched bed (transposes)
# - skip_rate: skips per second
# - amp
def render(sr, duration, t0, params=None):
    params=params or {}
    n=max(1,int(sr*max(0.001,float(duration))))
    amp=float(params.get("amp",0.25))
    base=float(params.get("base_hz",140.0))*TF()
    skip_rate=float(params.get("skip_rate",8.0))
    skip_rate=max(0.0,skip_rate)

    loop_len=max(32,int(sr*0.12))
    buf=[0.0]*loop_len
    ph=0.0
    inc=2.0*math.pi*base/sr
    for i in range(loop_len):
        v=math.sin(ph)*1.2
        v=max(-0.8,min(0.8,v))
        buf[i]=v
        ph+=inc

    outL=[0.0]*n
    outR=[0.0]*n

    pos=0
    next_skip=0.0
    for i in range(n):
        t=i/sr
        if skip_rate>0 and t >= next_skip:
            pos=int(random.random()*loop_len)
            next_skip = t + 1.0/skip_rate
        v=buf[pos]
        pos=(pos+1)%loop_len
        outL[i]=v*amp
        outR[i]=v*amp
    return outL,outR
