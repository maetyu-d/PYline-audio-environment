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


def _env(n, a=14.0):
    n = int(max(1, n))
    x = np.linspace(0.0, 1.0, n, endpoint=False, dtype=np.float32)
    return np.exp(-a * x).astype(np.float32)

def _click(sr, f=200.0, ms=10.0, g=1.0):
    n = max(8, int(sr * (ms/1000.0)))
    t = (np.arange(n, dtype=np.float32) / float(sr))
    env = _env(n, 18.0)
    sig = np.sin(2*np.pi*(float(f)*TF())*t).astype(np.float32) * env * float(g)
    return sig.astype(np.float32)

def render(duration=1.0, sr=48000, t0=0.0, params=None):
    params = _get_params(params)
    bpm = _get_bpm(params, 120.0)

    n = max(1, int(duration * sr))
    out = np.zeros(n, dtype=np.float32)

    spb = 60.0 / bpm
    step = spb / 4.0
    bar_steps = 20

    steps = int(duration/step) + 2
    for k in range(steps):
        te = k*step - (t0 % step)
        if te < 0.0 or te >= duration:
            continue
        idx = int(te * sr)
        pos = k % bar_steps

        amp = 0.0
        if pos == 0:  amp = 1.0
        if pos == 12: amp = max(amp, 0.85)
        if pos % 4 == 0: amp = max(amp, 0.35)

        if amp > 0.0:
            f = 180.0 + (60.0 if pos == 0 else 0.0)
            hit = _click(sr, f=f, ms=10.0, g=amp)
            end = min(n, idx + hit.shape[0])
            if end > idx:
                out[idx:end] += hit[:end-idx]

    out = np.tanh(out * np.float32(1.3)).astype(np.float32)
    return _stereo(out)
