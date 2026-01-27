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
    bpm = _get_bpm(params, 128.0)
    density = float(params.get("density", 1.0))
    base = float(params.get("base", 220.0)) * TF()
    sharp = float(params.get("sharp", 14.0))

    n = int(max(1, duration*sr))
    t = (np.arange(n, dtype=np.float32) / float(sr)) + np.float32(t0)

    spb = 60.0 / bpm
    step = spb / 4.0
    gate = (np.mod(t, step) < (0.003 * density)).astype(np.float32)

    drift = 0.7 + 0.3*np.sin(2*np.pi*0.07*t).astype(np.float32)
    ph = np.sin(2*np.pi*(base*drift)*t).astype(np.float32)

    clicks = (ph > 0.995).astype(np.float32) * gate
    klen = max(16, int(sr*0.012))
    kernel = np.exp(-np.linspace(0, 1, klen, endpoint=False, dtype=np.float32)*sharp).astype(np.float32)
    clicks = np.convolve(clicks, kernel, mode="same").astype(np.float32) * np.float32(0.28)

    return _stereo(np.tanh(clicks*2.2).astype(np.float32))
