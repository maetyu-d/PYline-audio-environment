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
    bpm = _get_bpm(params, 90.0)
    n = int(max(1, sr*duration))
    rng = np.random.default_rng(0)

    scale = np.array([0, 2, 3, 7, 10], dtype=np.int32)
    base_midi = int(params.get("base_midi", 48))
    step_beats = float(params.get("step_beats", 2.0))
    step = int(max(1, (60.0/bpm) * step_beats * sr))

    y = np.zeros(n, dtype=np.float32)
    idx = 0
    for i in range(0, n, step):
        note = base_midi + int(scale[idx % len(scale)]) + int(rng.integers(-12, 13)//12)*12
        freq = 440.0 * TF() * (2.0 ** ((note - 69) / 12.0))
        L = min(step, n - i)
        tt = (np.arange(L, dtype=np.float32) / float(sr))
        env = np.exp(-tt * np.float32(2.0)).astype(np.float32)
        y[i:i+L] += (0.28 * np.sin(2*np.pi*freq*tt).astype(np.float32) * env)
        idx += 1

    y = np.tanh(y * np.float32(1.2)).astype(np.float32)
    return _stereo(y)
