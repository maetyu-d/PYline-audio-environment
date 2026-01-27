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


def render(sr, duration, t0, params=None):
    """Oval-ish microloops: 4 buffers in a matrix, repeated re-entry, dropout punctuation (fixed & vectorized)."""
    params = params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    seed = int(params.get("seed", int(t0*1e6) & 0xffffffff))
    bpm = max(1.0, _bpm(params, 124.0))

    n = max(1, int(round(duration*sr)))
    t = np.arange(n, dtype=np.float32)/float(sr)

    rng = np.random.default_rng(seed)

    base = (np.sin(2*np.pi*np.float32(55.0)*TF()*(t+t0)) + 0.25*np.sin(2*np.pi*np.float32(110.0)*TF()*(t+t0))).astype(np.float32)*0.22
    bufs = []
    for _ in range(4):
        ms = float(rng.uniform(20,90))
        bl = max(16, int(sr*(ms/1000.0)))
        start = int(rng.integers(0, max(1, n-bl)))
        b = base[start:start+bl].copy()
        for __ in range(int(bl*0.02)):
            b[int(rng.integers(0, bl))] *= 0.0
        bufs.append(b.astype(np.float32))

    sec_per_beat = 60.0/max(1e-6,bpm)
    step = sec_per_beat/8.0
    cell = np.floor((t+t0)/step).astype(np.int64)

    sel = ((cell*1664525 + 1013904223) & 3).astype(np.int64)
    phase = (((t+t0) / step) % 1.0).astype(np.float32)

    out = np.zeros(n, dtype=np.float32)
    for bi in range(4):
        mask = (sel == bi)
        if not np.any(mask):
            continue
        b = bufs[bi]
        idx = (phase[mask] * np.float32(len(b)-1)).astype(np.int64)
        out[mask] = b[idx]

    drop = (((cell*1103515245 + 12345) & 0xffffffff) / np.float32(2**32)).astype(np.float32)
    out *= (drop > np.float32(params.get("drop_th", 0.12))).astype(np.float32)

    k = np.ones(9, dtype=np.float32)/np.float32(9.0)
    out = np.convolve(out, k, mode="same").astype(np.float32) * np.float32(1.6)
    out = np.tanh(out).astype(np.float32)

    return np.stack([out, out], axis=0).astype(np.float32)
