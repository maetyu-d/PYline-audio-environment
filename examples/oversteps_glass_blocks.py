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


def _adsr(n, a, d, s, r):
    aN = max(1, int(n*a))
    dN = max(1, int(n*d))
    rN = max(1, int(n*r))
    sN = max(0, n - (aN+dN+rN))
    env = np.zeros(n, dtype=np.float32)
    env[:aN] = np.linspace(0, 1, aN, endpoint=False, dtype=np.float32)
    env[aN:aN+dN] = np.linspace(1, s, dN, endpoint=False, dtype=np.float32)
    env[aN+dN:aN+dN+sN] = np.float32(s)
    env[aN+dN+sN:] = np.linspace(s, 0, rN, endpoint=False, dtype=np.float32)
    return env

def _glass_tone(sr, f, dur_s, gain=1.0, shimmer=0.20):
    n = max(1, int(sr*dur_s))
    t = (np.arange(n, dtype=np.float32) / float(sr))
    sig = (np.sin(2*np.pi*f*t) +
           0.55*np.sin(2*np.pi*(2.003*f)*t) +
           0.25*np.sin(2*np.pi*(3.997*f)*t) +
           0.18*np.sin(2*np.pi*(5.021*f)*t)).astype(np.float32)
    if shimmer > 0.0:
        mod = (0.85 + 0.25*np.sin(2*np.pi*0.25*t + 0.8*np.sin(2*np.pi*0.07*t))).astype(np.float32)
        sig *= (1.0 - shimmer) + shimmer*mod
    env = _adsr(n, 0.04, 0.10, 0.55, 0.31).astype(np.float32)
    return (sig * env * np.float32(gain/2.0)).astype(np.float32)

def render(duration=1.0, sr=48000, t0=0.0, params=None):
    params = _get_params(params)
    bpm = _get_bpm(params, 92.0)
    root = float(params.get("root", 220.0)) * TF()

    chords = params.get("chords", [
        [0, 4, 9, 14],
        [0, 3, 7, 12, 16],
        [0, 5, 10, 15],
        [0, 2, 7, 11, 14],
    ])
    step_beats = float(params.get("step_beats", 1.0))
    pan_spread = float(params.get("pan", 0.8))
    bright = float(params.get("bright", 1.0))
    shimmer = float(params.get("shimmer", 0.20))

    n = int(max(1, duration*sr))
    L = np.zeros(n, dtype=np.float32)
    R = np.zeros(n, dtype=np.float32)

    sec_per_beat = 60.0 / bpm
    step = sec_per_beat * max(1e-6, step_beats)
    rng = np.random.default_rng(int((t0+duration)*1e6) & 0xffffffff)

    k = 0
    while True:
        t_ev = k*step - (t0 % step)
        if t_ev >= duration:
            break
        if t_ev >= 0.0:
            idx = int(t_ev*sr)
            ch = chords[int(rng.integers(0, len(chords)))]
            d = float(step * rng.uniform(0.65, 0.95))
            for j, semi in enumerate(ch):
                f = root * (2**(semi/12.0)) * (2**(rng.uniform(-0.02, 0.02)))
                tone = _glass_tone(sr, f*bright, d, gain=1.0, shimmer=shimmer)
                end = min(n, idx + tone.shape[0])
                if end > idx:
                    pan = (((j/(max(1, len(ch)-1))) * 2.0 - 1.0) * pan_spread)
                    g = float(0.10 + 0.10*rng.random())
                    lmul = np.float32(g*(0.5*(1.0 - pan)))
                    rmul = np.float32(g*(0.5*(1.0 + pan)))
                    L[idx:end] += tone[:end-idx]*lmul
                    R[idx:end] += tone[:end-idx]*rmul
        k += 1

    air = rng.standard_normal(n).astype(np.float32) * np.float32(0.0012)
    L += air; R += air
    out = np.tanh(np.stack([L, R], axis=0) * np.float32(1.15)).astype(np.float32)
    return out
