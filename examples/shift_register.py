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
    bpm = _get_bpm(params, 120.0)

    n = int(max(1, duration*sr))
    out = np.zeros(n, dtype=np.float32)

    spb = 60.0 / bpm
    step = float(params.get("step", spb/8.0))

    reg = int(params.get("seed", 0b1010010010110101)) & 0xffff
    steps = int(duration/step) + 2
    for k in range(steps):
        te = k*step - (t0 % step)
        if te < 0.0 or te >= duration:
            continue
        idx = int(te*sr)
        if reg & 1:
            out[idx] += 1.0
        newbit = ((reg>>1) ^ (reg>>2)) & 1
        reg = (reg>>1) | (newbit<<15)

    out = np.convolve(out, np.ones(30, dtype=np.float32)/30.0, mode="same").astype(np.float32) * np.float32(0.35)
    return _stereo(np.tanh(out*2.0).astype(np.float32))
