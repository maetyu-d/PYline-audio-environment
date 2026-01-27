import numpy as np

# --- transpose helper (semitones) ---
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

def _get_bpm(params):
    try:
        return float(CLIP_BPM)
    except Exception:
        pass
    try:
        return float(params.get("bpm", 98.0))
    except Exception:
        return 98.0

def _env(n, a=0.06, d=0.12, s=0.6, r=0.22):
    n = int(max(1, n))
    aN = max(1, int(n*a))
    dN = max(1, int(n*d))
    rN = max(1, int(n*r))
    sN = max(0, n - (aN + dN + rN))
    e = np.zeros(n, dtype=np.float32)
    e[:aN] = np.linspace(0, 1, aN, endpoint=False, dtype=np.float32)
    e[aN:aN+dN] = np.linspace(1, s, dN, endpoint=False, dtype=np.float32)
    if sN:
        e[aN+dN:aN+dN+sN] = np.float32(s)
    e[aN+dN+sN:] = np.linspace(s, 0, rN, endpoint=False, dtype=np.float32)
    return e

def _tile(sr, f, dur_s, phase=0.0):
    n = max(1, int(sr * dur_s))
    t = (np.arange(n, dtype=np.float32) / float(sr))
    # glassy, slightly inharmonic partials
    sig = (
        np.sin(2*np.pi*f*t + phase) +
        0.33*np.sin(2*np.pi*(2.005*f)*t + (0.2 + phase)) +
        0.22*np.sin(2*np.pi*(4.012*f)*t + (0.7 + phase))
    ).astype(np.float32)
    sig *= (0.85 + 0.15*np.sin(2*np.pi*0.35*t)).astype(np.float32)
    return (sig * _env(n) * 0.35).astype(np.float32)

def render(sr, duration, t0, params=None):
    """Oversteps-like harmonic tiles: chord fragments placed as discrete blocks."""
    params = params or {}
    sr = int(sr)
    duration = float(duration)
    t0 = float(t0)

    bpm = max(1.0, _get_bpm(params))
    root = float(params.get("root", 196.0)) * TF()   # transpose shifts harmonic center
    tile_beats = float(params.get("tile_beats", 0.5))
    pattern = params.get("pattern", [0,2,5,7,9,12,14,17])
    chord_sizes = params.get("sizes", [3,4,5])
    bright = float(params.get("bright", 1.0))

    n = max(1, int(duration * sr))
    L = np.zeros(n, dtype=np.float32)
    R = np.zeros(n, dtype=np.float32)

    # stable per-clip RNG (depends on absolute clip start)
    seed = int((t0 + duration) * 1e6) & 0xffffffff
    rng = np.random.default_rng(seed)

    spb = 60.0 / bpm
    step = spb * tile_beats

    i = 0
    while True:
        te = i*step - (t0 % step)
        if te >= duration:
            break
        if te >= 0.0:
            idx = int(te * sr)
            size = int(rng.choice(chord_sizes))
            size = max(1, min(size, len(pattern)))
            base = int(rng.integers(0, max(1, len(pattern) - size + 1)))
            degs = pattern[base:base+size]

            dur_s = float(step * rng.uniform(0.9, 1.6))

            for semi in degs:
                f = root * (2.0**(float(semi)/12.0)) * bright * (2.0**float(rng.uniform(-0.01, 0.01)))
                tone = _tile(sr, f, dur_s, phase=float(rng.uniform(0.0, 2*np.pi)))
                end = min(n, idx + tone.shape[0])
                if end <= idx:
                    continue
                pan = float(rng.uniform(-0.75, 0.75))
                g = float(0.06 + 0.10*rng.random())
                # simple pan
                gl = g * (0.5*(1.0 - pan))
                gr = g * (0.5*(1.0 + pan))
                L[idx:end] += tone[:end-idx] * np.float32(gl)
                R[idx:end] += tone[:end-idx] * np.float32(gr)

        i += 1

    out = np.tanh(np.stack([L, R], axis=0) * 1.1).astype(np.float32)
    return out
