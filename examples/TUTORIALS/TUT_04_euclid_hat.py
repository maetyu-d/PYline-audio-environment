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


# Tutorial 04: Euclidean hats (algorithmic rhythm) locked to tempo.
# Params: steps, pulses, amp, tone_hz (optional, transposes)
def _euclid(steps, pulses):
    steps=max(1,int(steps)); pulses=max(0,int(pulses))
    if pulses==0: return [0]*steps
    if pulses>=steps: return [1]*steps
    pat=[]
    bucket=0
    for _ in range(steps):
        bucket += pulses
        if bucket >= steps:
            bucket -= steps
            pat.append(1)
        else:
            pat.append(0)
    return pat

def render(sr, duration, t0, params=None):
    params=params or {}
    bpm=float(params.get("bpm",120.0))
    try:
        bpm=float(CLIP_BPM)
    except Exception:
        pass
    bpm=max(1.0,bpm)

    steps=int(params.get("steps",16))
    pulses=int(params.get("pulses",5))
    amp=float(params.get("amp",0.35))
    tone=float(params.get("tone_hz",0.0))
    if tone>0: tone*=TF()

    pat=_euclid(steps,pulses)
    spb=60.0/bpm
    bar=spb*4.0
    step_t=bar/steps

    n=max(1,int(sr*max(0.001,float(duration))))
    outL=[0.0]*n
    outR=[0.0]*n

    k=0
    t=0.0
    while t < duration + 1e-9:
        if pat[k%steps]:
            i=int(t*sr)
            if 0<=i<n:
                outL[i]+=amp
                outR[i]+=amp
        k+=1
        t+=step_t

    a=math.exp(-1.0/(sr*0.015))
    y=0.0
    ph=0.0
    inc=2.0*math.pi*tone/sr if tone>0 else 0.0
    for i in range(n):
        x=outL[i] + (random.random()*2-1)*0.06
        y = x + a*y
        v=y
        if tone>0:
            v += math.sin(ph)*0.05
            ph += inc
        outL[i]=v
        outR[i]=v
    return outL,outR
