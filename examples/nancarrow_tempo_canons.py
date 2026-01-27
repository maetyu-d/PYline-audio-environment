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


def _env(n, a=12.0):
    x = np.linspace(0, 1, int(n), endpoint=False, dtype=np.float32)
    return np.exp(-np.float32(a)*x).astype(np.float32)

def _chime(sr, f, dur_s, gain=1.0):
    n = max(1, int(sr*float(dur_s)))
    t = np.arange(n, dtype=np.float32)/float(sr)
    sig = (np.sin(2*np.pi*np.float32(f)*t) +
           0.35*np.sin(2*np.pi*np.float32(2.01*f)*t) +
           0.20*np.sin(2*np.pi*np.float32(3.02*f)*t)).astype(np.float32)
    sig *= _env(n, a=10.5) * np.float32(gain/1.55)
    return sig.astype(np.float32)

def render(sr, duration, t0, params=None):
    """Tempo-canons: several voices on different tempo ratios, quantised to a roll grid (fixed)."""
    params = params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    bpm = float(params.get("bpm", 132.0))
    ratios = params.get("ratios", [1.0, 4/3, 5/4, 7/6])
    grid = int(params.get("grid", 24))
    root = float(params.get("root", 220.0)) * TF()
    scale = params.get("scale", [0, 3, 7, 10, 12, 15, 19])
    prob = float(params.get("prob", 0.55))

    n = max(1, int(round(duration*sr)))
    L = np.zeros(n, dtype=np.float32)
    R = np.zeros(n, dtype=np.float32)

    sec_per_beat = 60.0/max(1e-6, bpm)
    micro = sec_per_beat * (4.0/float(max(1,grid)))

    rng = np.random.default_rng(int((t0*1e6)) & 0xffffffff)

    for vi, r in enumerate(ratios):
        step = micro / float(r)
        octave = 2**(vi*0.25)
        t_cur = (math.floor(t0/step) * step) - t0
        while t_cur < duration + step:
            if t_cur >= 0 and rng.random() < prob:
                idx = int(t_cur*sr)
                if 0 <= idx < n:
                    deg = int(rng.integers(0, len(scale)))
                    f = root * octave * (2**(float(scale[deg])/12.0))
                    note = _chime(sr, f, dur_s=rng.uniform(0.03, 0.10), gain=1.0)
                    end = min(n, idx+len(note))
                    g = float(0.08 + 0.12*rng.random())
                    pan = float(-0.8 + 1.6*(deg/(max(1,len(scale)-1))))
                    lmul = np.float32(g*(0.5*(1-pan)))
                    rmul = np.float32(g*(0.5*(1+pan)))
                    L[idx:end] += note[:end-idx]*lmul
                    R[idx:end] += note[:end-idx]*rmul
            t_cur += step

    outL = np.tanh(L*1.15).astype(np.float32)
    outR = np.tanh(R*1.15).astype(np.float32)
    return np.stack([outL,outR], axis=0)
