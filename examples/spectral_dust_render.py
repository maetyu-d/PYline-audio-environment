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

    block = int(params.get("block", 2048))
    hop = int(params.get("hop", 512))
    block = max(256, block); hop = max(64, min(hop, block))
    win = np.hanning(block).astype(np.float32)

    y = np.zeros(n + block, dtype=np.float32)
    bins = block//2 + 1
    active = np.zeros(bins, dtype=np.float32)

    stars = rng.integers(low=20, high=max(21, bins-20), size=32)
    for b in stars:
        if 0 <= b < bins:
            active[b] = float(rng.uniform(0.2, 1.0))

    drift_rate = float(rng.uniform(0.002, 0.02))
    decay = float(rng.uniform(0.90, 0.985))
    tilt = np.linspace(0.6, 1.2, bins).astype(np.float32)

    frames = int(np.ceil((n + block)/hop)) + 2
    for fi in range(frames):
        start = fi*hop
        if start >= n + block:
            break

        active *= np.float32(decay)
        if rng.random() < drift_rate:
            b = int(rng.integers(10, max(11, bins-10)))
            active[b] = float(rng.uniform(0.4, 1.0))
        if rng.random() < drift_rate:
            baseb = int(rng.integers(40, min(max(41, bins-40), 800)))
            for k in range(1, 5):
                bb = min(bins-1, baseb*k)
                active[bb] = max(active[bb], float(rng.uniform(0.15, 0.7)))

        x = (rng.standard_normal(block).astype(np.float32) * np.float32(0.15)) * win
        X = np.fft.rfft(x)
        mask = (active * (active > 0.01)).astype(np.float32)
        X = X * (mask * tilt)
        x2 = np.fft.irfft(X).astype(np.float32) * win

        end = min(len(y), start + block)
        L = end - start
        if L > 0:
            y[start:end] += x2[:L]

    y = y[:n]

    flutter_hz = float(rng.uniform(7.0, 22.0))
    t = np.linspace(0.0, duration, n, endpoint=False, dtype=np.float32)
    flutter = (0.75 + 0.25*np.sin(2*np.pi*flutter_hz*t + float(rng.uniform(0, 2*np.pi)))).astype(np.float32)
    y *= flutter

    m = float(np.max(np.abs(y))) if n else 0.0
    if m > 1e-9:
        y = (y / m * np.float32(0.35)).astype(np.float32)

    f = min(int(0.01*sr), n//2)
    if f > 1:
        ramp = np.linspace(0, 1, f, endpoint=True, dtype=np.float32)
        y[:f] *= ramp; y[-f:] *= ramp[::-1]
    return _stereo(y)
