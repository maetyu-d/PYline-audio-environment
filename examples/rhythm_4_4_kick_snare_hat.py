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

def _click(sr, ms=10.0, g=1.0, f=160.0):
    n = max(8, int(sr * (ms/1000.0)))
    t = (np.arange(n, dtype=np.float32) / float(sr))
    env = _env(n, 18.0)
    # transpose affects pitch only
    sig = np.sin(2*np.pi*(float(f)*TF())*t).astype(np.float32) * env * float(g)
    return sig.astype(np.float32)

def render(sr, duration, t0, params=None):
    params = params or {}
    sr = int(sr); duration = float(duration); t0 = float(t0)
    bpm = float(params.get("bpm", 120.0))
    try: bpm = float(CLIP_BPM)
    except Exception: pass
    bpm = max(1.0, bpm)

    n = max(1, int(duration * sr))
    out = np.zeros(n, dtype=np.float32)

    spb = 60.0 / bpm
    step = spb / 4.0  # 16ths

    # pattern: kick on 1, snare on 2&4, hat every 8th
    steps = int(duration/step) + 2
    for k in range(steps):
        te = k*step - (t0 % step)
        if te < 0.0 or te >= duration: 
            continue
        idx = int(te * sr)
        beat = (k//4) % 4
        sub  = k % 4
        amp = 0.0
        if beat == 0 and sub == 0: amp = 1.0          # kick
        if beat in (1,3) and sub == 0: amp = max(amp, 0.8)  # snare
        if sub in (0,2): amp = max(amp, 0.35)         # hat
        if amp > 0.0:
            hit = _click(sr, ms=10.0, g=amp, f=160.0)
            end = min(n, idx + hit.shape[0])
            if end > idx:
                out[idx:end] += hit[:end-idx]

    out = np.tanh(out * 1.4).astype(np.float32)
    return np.stack([out, out], axis=0)
