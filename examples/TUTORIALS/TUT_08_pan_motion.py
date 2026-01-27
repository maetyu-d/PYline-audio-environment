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


# Tutorial 08: stereo pan motion inside a clip.
# Params: freq, amp, pan_rate (Hz). Transpose affects pitch.
def render(sr, duration, t0, params=None):
    params=params or {}
    n=max(1,int(sr*max(0.001,float(duration))))
    amp=float(params.get("amp",0.22))
    freq=float(params.get("freq",180.0))*TF()
    pan_rate=float(params.get("pan_rate",0.35))

    outL=[0.0]*n
    outR=[0.0]*n

    for i in range(n):
        t=i/sr
        v=math.sin(2*math.pi*freq*t)*amp
        pan=0.5+0.5*math.sin(2*math.pi*pan_rate*t)
        l=math.cos(pan*math.pi/2)
        r=math.sin(pan*math.pi/2)
        outL[i]=v*l
        outR[i]=v*r
    return outL,outR
