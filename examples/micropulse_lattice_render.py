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
    """Micropulse lattice: jittered micro-impulses excite short modal rings (fixed)."""
    params=params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    n=max(1, int(round(sr*duration)))
    y=np.zeros(n, dtype=np.float32)
    rng=np.random.default_rng(int((t0*1e6)) & 0xffffffff)

    # lattice spacing (1..12ms), optionally tempo-derived
    bpm=max(1.0, _bpm(params, 120.0))
    if bool(params.get("tempo_lock", False)):
        spb=60.0/bpm
        step=max(8, int(sr*(spb/16.0)))  # 64ths
    else:
        step=max(8, int(rng.uniform(0.001,0.012)*sr))

    # modal set (transpose affects overall center)
    base = float(params.get("base", 520.0)) * TF()
    modes = np.array([0.60, 1.00, 1.56, 2.38, 3.79], dtype=np.float32) * np.float32(base)
    modes *= np.float32(rng.uniform(0.7, 1.4))

    # ring length (2..18ms)
    L=int(rng.uniform(0.002,0.018)*sr)
    L=max(32, L)
    t=np.linspace(0.0, L/sr, L, endpoint=False, dtype=np.float32)
    win=np.hanning(L).astype(np.float32)
    dec=np.exp(-t*float(rng.uniform(120,650))).astype(np.float32)

    pos=0
    while pos < n:
        if rng.random() < float(params.get("drop", 0.08)):
            pos += step
            continue
        j=int(rng.integers(-step//4, step//4))
        i0=pos+j
        if i0 < 0 or i0 >= n:
            pos += step
            continue

        ring=np.zeros(L, dtype=np.float32)
        pick=int(rng.integers(2, min(5, len(modes)+1)))
        for f in rng.choice(modes, size=pick, replace=False):
            ring += np.sin(2*np.pi*np.float32(f)*t).astype(np.float32)
        mmax=float(np.max(np.abs(ring))) if ring.size else 0.0
        if mmax > 1e-9:
            ring = ring / np.float32(mmax)
        ring = ring * win * dec

        amp=float(rng.uniform(0.15,0.85)) * float(params.get("amp", 0.9))
        end=min(n, i0+L); segN=end-i0
        y[i0:end] += (np.float32(amp) * ring[:segN]).astype(np.float32)

        pos += step

    y=np.tanh(y*1.25).astype(np.float32) * np.float32(0.9)

    # stereo: tiny delay decorrelation
    d=int(max(1, min(4096, int(sr*0.0012))))
    Lc=y.copy(); Rc=y.copy()
    if d < n:
        Rc[d:] = 0.8*Rc[d:] + 0.2*Lc[:-d]
    return np.stack([Lc,Rc], axis=0).astype(np.float32)
