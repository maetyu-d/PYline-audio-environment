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

def _fade_edges(y, sr):
    n=len(y)
    f=min(int(0.01*sr), n//2)
    if f>1:
        ramp=np.linspace(0,1,f,endpoint=True,dtype=np.float32)
        y[:f]*=ramp
        y[-f:]*=ramp[::-1]
    return y

def render(sr, duration, t0, params=None):
    """Micro edit skip: clicks'n'cuts discontinuity (fixed)."""
    params=params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    n=max(1, int(round(sr*duration)))
    rng=np.random.default_rng(int((t0*1e6)) & 0xffffffff)

    y=np.zeros(n, dtype=np.float32)

    hits=max(12, int(duration * float(params.get("rate", 140.0))))
    for _ in range(hits):
        i=int(rng.integers(0,n))
        L=int(rng.uniform(0.001,0.01)*sr)
        L=max(16, min(L, n-i))
        if L<=0: 
            continue
        t=np.linspace(0, L/sr, L, endpoint=False, dtype=np.float32)
        env=np.exp(-t*float(rng.uniform(250,1200))).astype(np.float32)
        burst=(rng.standard_normal(L).astype(np.float32)*0.4)
        burst=burst - np.mean(burst)
        burst=np.cumsum(burst).astype(np.float32)
        burst=burst / max(1e-9, float(np.max(np.abs(burst))))
        y[i:i+L] += (burst*env*float(rng.uniform(0.2,1.0))).astype(np.float32)

    z=np.zeros(n, dtype=np.float32)
    read=0; write=0
    while write < n:
        r=rng.random()
        if r < 0.08:
            rep=int(rng.uniform(0.005,0.03)*sr); rep=max(8,rep)
            for _ in range(int(rng.integers(2,6))):
                end=min(n, write+rep)
                ln=end-write
                if read+ln >= n: read=0
                z[write:end] = y[read:read+ln]
                write=end
                if write>=n: break
        elif r < 0.12:
            bl=int(rng.uniform(0.004,0.02)*sr); bl=max(8,bl)
            end=min(n, write+bl); ln=end-write
            a=max(0, read-bl); seg=y[a:read].copy()[::-1]
            z[write:end] = seg[:ln]
            write=end
        elif r < 0.18:
            read += int(rng.uniform(0.01,0.08)*sr)

        chunk=int(rng.uniform(0.005,0.04)*sr); chunk=max(16,chunk)
        end=min(n, write+chunk); ln=end-write
        if read+ln >= n: read=0
        z[write:end] = y[read:read+ln]
        read += ln
        write = end

    for _ in range(max(1, int(duration*6))):
        a=int(rng.integers(0,n))
        L=int(rng.uniform(0.003,0.03)*sr)
        z[a:min(n,a+L)] *= 0.0

    z=np.tanh(z*1.6).astype(np.float32) * np.float32(params.get("amp", 0.85))
    z=_fade_edges(z, sr)

    # light stereo offset
    d=int(max(1, min(4096, int(sr*0.0009))))
    L=z.copy(); R=z.copy()
    if d < n:
        R[d:] = 0.85*R[d:] + 0.15*L[:-d]
    return np.stack([L,R], axis=0).astype(np.float32)
