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
    n = int(max(1, duration*sr))
    t = np.linspace(0.0, duration, n, endpoint=False, dtype=np.float32)
    rng = np.random.default_rng(int((t0+duration)*1e6) & 0xffffffff)

    sig = np.zeros(n, dtype=np.float32)
    grains = int(params.get("grains", 80))
    for _ in range(grains):
        c = float(rng.uniform(0.0, duration))
        w = float(rng.uniform(0.001, 0.006))
        env = np.exp(-0.5*((t - c)/w)**2).astype(np.float32)
        f = float(rng.uniform(800, 4000)) * TF()
        sig += (np.sin(2*np.pi*f*t).astype(np.float32) * env)

    sig *= np.float32(0.08)
    sig = np.tanh(sig * np.float32(1.6)).astype(np.float32)
    return _stereo(sig)
