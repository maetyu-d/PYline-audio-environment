import numpy as np
import math

def TF(semi=None):
    """Transpose factor: 2**(semitones/12). Reads CLIP_TRANSPOSE or params['transpose']."""
    try:
        s = float(CLIP_TRANSPOSE if semi is None else semi)
    except Exception:
        try:
            s = float(_PARAMS.get("transpose", 0.0)) if semi is None else float(semi)
        except Exception:
            try:
                s = float((params or {}).get("transpose", 0.0)) if semi is None else float(semi)
            except Exception:
                s = 0.0
    return 2.0 ** (s / 12.0)

def _get_params(params):
    return {} if params is None else params

def _get_bpm(params, default=120.0):
    p = _get_params(params)
    bpm = float(p.get("bpm", default))
    try:
        bpm = float(CLIP_BPM)
    except Exception:
        pass
    return max(1.0, bpm)

def _stereo(sig):
    sig = np.asarray(sig, dtype=np.float32)
    if sig.ndim == 1:
        return np.stack([sig, sig], axis=0)
    if sig.ndim == 2 and sig.shape[0] == 2:
        return sig.astype(np.float32)
    if sig.ndim == 2 and sig.shape[1] == 2:
        return sig.T.astype(np.float32)
    sig = sig.reshape(-1).astype(np.float32)
    return np.stack([sig, sig], axis=0)


def render(duration=1.0, sr=48000, t0=0.0, params=None):
    params = _get_params(params)
    n = int(max(1, sr*duration))
    rng = np.random.default_rng(int((t0+duration)*1e6) & 0xffffffff)
    t = np.linspace(0.0, duration, n, endpoint=False, dtype=np.float32)

    bed = (0.22*np.sin(2*np.pi*float(rng.uniform(120, 260))*TF()*t) +
           0.12*np.sin(2*np.pi*float(rng.uniform(400, 900))*TF()*t)).astype(np.float32)

    y = bed.copy()
    skips = max(4, int(duration * 6))
    for _ in range(skips):
        p = int(rng.integers(0, n))
        L = int(rng.uniform(0.01, 0.08) * sr)
        L = max(32, min(L, n - p))
        if L <= 0:
            continue
        mode = int(rng.integers(0, 3))
        if mode == 0:
            frag = y[p:p+L].copy()
            reps = int(rng.integers(2, 6))
            for r in range(reps):
                a = p + r*L
                b = min(n, a+L)
                if b > a:
                    y[a:b] = frag[:b-a]
        elif mode == 1:
            y[p:p+L] *= 0.0
        else:
            step = int(rng.uniform(8, 64))
            frag = y[p:p+L].copy()
            frag = np.repeat(frag[::step], step)[:L]
            y[p:p+L] = frag.astype(np.float32)

    y = np.tanh(y * np.float32(1.2)).astype(np.float32) * np.float32(0.75)

    f = min(int(0.01*sr), n//2)
    if f > 1:
        ramp = np.linspace(0, 1, f, endpoint=True, dtype=np.float32)
        y[:f] *= ramp
        y[-f:] *= ramp[::-1]

    return _stereo(y)
