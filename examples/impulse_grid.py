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

def _env(n, sr, tau_ms=14.0):
    tau = max(1.0, float(sr)*(float(tau_ms)/1000.0))
    return np.exp(-np.arange(n, dtype=np.float32)/tau).astype(np.float32)

def render(sr, duration, t0, params=None):
    params=params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    bpm=max(1.0, _bpm(params, 145.0))
    n=max(1, int(round(duration*sr)))
    y=np.zeros(n, dtype=np.float32)

    spb=60.0/bpm
    step=int(max(1, round(sr*(spb/16.0))))  # 64ths
    dens=float(params.get("density", 0.7))
    tau=float(params.get("tau_ms", 14.0))
    amp=float(params.get("amp", 0.30))

    rng=np.random.default_rng(int((t0*1e6)) & 0xffffffff)
    for i in range(0, n, step):
        if (i//step)%3 != 1 and rng.random() < dens:
            y[i] += 1.0

    klen=max(8, int(sr*0.006))
    k=_env(klen, sr, tau_ms=tau)
    y=np.convolve(y, k, mode="same").astype(np.float32) * np.float32(amp)
    y=np.tanh(y*2.2).astype(np.float32)
    return np.stack([y,y], axis=0)
