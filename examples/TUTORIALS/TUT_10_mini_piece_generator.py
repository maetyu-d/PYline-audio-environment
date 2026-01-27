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


# Tutorial 10: a complete tiny generative piece in one clip.
# - tempo-locked kick + hat
# - glass chord shimmer (transpose affects harmony)
# Params: amp, density, root_hz
def render(sr, duration, t0, params=None):
    params=params or {}
    bpm=float(params.get("bpm", 124.0))
    try:
        bpm=float(CLIP_BPM)
    except Exception:
        pass
    bpm=max(1.0,bpm)

    n=max(1,int(sr*max(0.001,float(duration))))
    amp=float(params.get("amp",0.25))
    density=float(params.get("density",1.0))

    spb=60.0/bpm
    sixteenth=spb/4.0

    root=float(params.get("root_hz", 110.0))*TF()
    chord=[root, root*5/4, root*3/2, root*2.0]

    outL=[0.0]*n
    outR=[0.0]*n

    kick_idx=set()
    hat_idx=set()
    t=0.0
    step=0
    while t < duration + 1e-9:
        if step % 16 in (0,4,8,12):
            kick_idx.add(int(t*sr))
        if step % 2 == 1 and random.random() < 0.75*density:
            hat_idx.add(int(t*sr))
        step += 1
        t += sixteenth

    # lay down impulses + harmony bed
    for i in range(n):
        tt=i/sr
        if i in kick_idx:
            outL[i]+=1.0
            outR[i]+=1.0
        if i in hat_idx:
            outL[i]+=0.35
            outR[i]+=0.35

        env = 0.55 + 0.45*math.sin(2*math.pi*(0.25/spb)*tt)
        c=0.0
        for f in chord:
            c += math.sin(2*math.pi*f*tt + 0.3*math.sin(2*math.pi*f*0.01*tt))
        c = (c/len(chord))*0.12*env
        outL[i]+=c
        outR[i]+=c

    # shape kick + hat with simple one-poles
    aK = math.exp(-1.0/(sr*0.10))
    aH = math.exp(-1.0/(sr*0.02))
    yK=0.0
    yH=0.0
    for i in range(n):
        x=outL[i]
        imp = 1.0 if x>0.9 else 0.0
        hat = 1.0 if (0.3<x<0.6) else 0.0
        yK = imp + aK*yK
        yH = (hat*(random.random()*2-1)*0.6) + aH*yH
        v = (yK*0.9 + yH*0.35 + (x - imp - hat)) * amp
        outL[i]=v*0.98
        outR[i]=v*1.02
    return outL,outR
