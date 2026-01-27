import numpy as np
import math

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
    """Mouse-on-Mars-ish bubble percussion: resonant pings + short noise bubbles (fixed)."""
    params = params or {}
    sr = int(sr); duration = float(duration); t0 = float(t0)
    n = max(1, int(round(duration*sr)))
    rng = np.random.default_rng(int((t0*1e6)) & 0xffffffff)

    bpm = max(1.0, _bpm(params, 128.0))
    spb = 60.0/bpm
    step = max(8, int(sr*(spb/8.0)))  # 32nds
    density = float(params.get("density", 0.65))
    amp = float(params.get("amp", 0.20))

    y = np.zeros(n, dtype=np.float32)

    for i in range(0, n, step):
        if rng.random() > density:
            continue
        idx = i + int(rng.integers(-step//4, step//4))
        if idx < 0 or idx >= n: 
            continue
        f = float(rng.uniform(280.0, 1500.0)) * TF()
        m = max(16, int(sr*0.010))
        end = min(n, idx+m)
        L = end-idx
        t = np.arange(L, dtype=np.float32)/float(sr)
        env = np.exp(-t*float(rng.uniform(180.0, 900.0))).astype(np.float32)
        burst = (np.sin(2*np.pi*np.float32(f)*t) + 0.25*rng.standard_normal(L).astype(np.float32)) * env
        y[idx:end] += burst[:L] * np.float32(rng.uniform(0.3, 1.0))

        # occasional second tiny bubble
        if rng.random() < 0.25 and idx+int(sr*0.006) < n:
            j = idx + int(sr*float(rng.uniform(0.003,0.010)))
            end2=min(n, j+m); L2=end2-j
            t2=np.arange(L2, dtype=np.float32)/float(sr)
            env2=np.exp(-t2*float(rng.uniform(220.0, 1200.0))).astype(np.float32)
            burst2=(0.6*np.sin(2*np.pi*np.float32(f*1.5)*t2) + 0.35*rng.standard_normal(L2).astype(np.float32))*env2
            y[j:end2] += burst2[:L2] * np.float32(rng.uniform(0.2, 0.8))

    y = np.tanh(y*3.0).astype(np.float32) * np.float32(amp*2.5)
    # stereo decorrelation
    d = int(max(1, min(4096, int(sr*0.0009))))
    L = y.copy(); R = y.copy()
    if d < n:
        R[d:] = 0.82*R[d:] + 0.18*L[:-d]
    return np.stack([L,R], axis=0).astype(np.float32)
