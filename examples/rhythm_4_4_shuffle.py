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

def _env(n, a=14.0):
    n = int(max(1, n))
    x = np.linspace(0.0, 1.0, n, endpoint=False, dtype=np.float32)
    return np.exp(-a * x).astype(np.float32)

def _fit(x, n):
    """Force x to length n (pad or trim)."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    n = int(max(1, n))
    if x.shape[0] == n:
        return x
    if x.shape[0] < n:
        return np.pad(x, (0, n - x.shape[0]))
    return x[:n]

def _hat(sr, ms=8.0, g=1.0):
    n = max(8, int(sr * (ms/1000.0)))
    noise = (np.random.rand(n).astype(np.float32) - 0.5)
    env = _env(n, 20.0)
    return (noise * env * float(g)).astype(np.float32)

def render(sr, duration, t0, params=None):
    params = params or {}
    sr = int(sr); duration = float(duration); t0 = float(t0)
    bpm = float(params.get("bpm", 110.0))
    try: bpm = float(CLIP_BPM)
    except Exception: pass
    bpm = max(1.0, bpm)

    swing = float(params.get("swing", 0.15))  # 0..0.3
    swing = max(0.0, min(0.35, swing))

    n = max(1, int(duration * sr))
    out = np.zeros(n, dtype=np.float32)

    spb = 60.0 / bpm
    step = spb / 2.0  # 8ths

    steps = int(duration/step) + 2
    for k in range(steps):
        te = k*step - (t0 % step)
        if k % 2 == 1:
            te += swing * step
        if te < 0.0 or te >= duration:
            continue
        idx = int(te * sr)
        amp = 0.35 if (k % 2 == 0) else 0.25
        hit = _hat(sr, ms=8.0, g=amp)
        end = min(n, idx + hit.shape[0])
        if end > idx:
            out[idx:end] += hit[:end-idx]

    out = np.tanh(out * 1.2).astype(np.float32)
    return np.stack([out, out], axis=0)
