import numpy as np

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

def _bpm(params, default=120.0):
    try:
        return float(CLIP_BPM)
    except Exception:
        pass
    try:
        return float((params or {}).get("bpm", default))
    except Exception:
        return float(default)

def render(sr, duration, t0, params=None):
    params = params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    bpm=max(1.0, _bpm(params, 140.0))
    n=max(1, int(round(duration*sr)))
    t=(np.arange(n, dtype=np.float32)/float(sr)) + np.float32(t0)

    spb=60.0/bpm
    g1=spb/4.0   # 16th
    g2=spb/5.0   # quint
    g3=spb/7.0   # sept

    p1=((t/g1)%1.0) < 0.04
    p2=((t/g2)%1.0) < 0.03
    p3=((t/g3)%1.0) < 0.02

    x=(p1.astype(np.int8) ^ p2.astype(np.int8) ^ p3.astype(np.int8)).astype(np.float32)
    sig=(x*2.0 - 1.0) * (x>0).astype(np.float32)

    tail_len=int(sr*0.0015)
    if tail_len>2:
        k=np.exp(-np.linspace(0,1,tail_len,dtype=np.float32)*10.0).astype(np.float32)
        sig=np.convolve(sig, k, mode="same").astype(np.float32) * np.float32(0.9)

    bar=spb*4.0
    gate=((t % bar) < (bar*0.92)).astype(np.float32)
    sig=(sig*gate).astype(np.float32)

    return np.stack([sig, sig], axis=0)
