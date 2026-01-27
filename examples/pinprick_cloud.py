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
    bpm = _get_bpm(params, 140.0)
    n = int(max(1, duration*sr))
    rng = np.random.default_rng(int((t0+duration)*1e6) & 0xffffffff)

    sig = np.zeros(n, dtype=np.float32)
    hits = int(max(32, 160 * duration))
    idx = rng.integers(0, n, size=hits)
    sig[idx] += (rng.uniform(-1.0, 1.0, size=hits)).astype(np.float32)

    klen = max(32, int(sr*0.010))
    kernel = np.exp(-np.linspace(0, 1, klen, endpoint=False, dtype=np.float32)*9.0).astype(np.float32)
    sig = np.convolve(sig, kernel, mode="same").astype(np.float32) * np.float32(0.22)

    spb = 60.0 / bpm
    step = spb / 8.0
    for k in range(int(duration/step)+2):
        te = k*step - (t0 % step) + float(rng.uniform(-0.002, 0.002))
        if te < 0.0 or te >= duration:
            continue
        i = int(te*sr)
        L = min(n-i, max(48, int(sr*float(rng.uniform(0.006, 0.018)))))
        if L <= 0:
            continue
        tt = (np.arange(L, dtype=np.float32)/float(sr))
        f = float(rng.uniform(900.0, 5200.0)) * TF()
        env = np.exp(-tt*float(rng.uniform(40.0, 120.0))).astype(np.float32)
        sig[i:i+L] += (0.08*np.sin(2*np.pi*f*tt)*env).astype(np.float32)

    sig = np.tanh(sig*2.0).astype(np.float32) * np.float32(0.85)
    return _stereo(sig)
