# Tempo-linked Nancarrow-ish roll (fixed)
# - App signature: render(sr, duration, t0, params=None)
# - Uses CLIP_BPM (track tempo) when available
# - Uses CLIP_TRANSPOSE via TF() to transpose pitch only

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

def _bpm(params):
    # track bpm injected by app
    try:
        return float(CLIP_BPM)
    except Exception:
        pass
    try:
        return float(params.get("bpm", 120.0))
    except Exception:
        return 120.0

def _env_click(n, sr, tau_ms=18.0):
    tau = max(1.0, float(sr) * (float(tau_ms)/1000.0))
    return np.exp(-np.arange(n, dtype=np.float32)/tau).astype(np.float32)

def _hp1(x, a=0.997):
    # DC blocker high-pass: y[n] = x[n] - x[n-1] + a*y[n-1]
    y = np.empty_like(x)
    xm1 = np.float32(0.0)
    ym1 = np.float32(0.0)
    a = np.float32(a)
    for i in range(len(x)):
        xn = x[i]
        yn = xn - xm1 + a*ym1
        y[i] = yn
        xm1 = xn
        ym1 = yn
    return y

def _pan(m, pan=0.15):
    pan = float(np.clip(pan, -1.0, 1.0))
    ang = (pan + 1.0) * (np.pi * 0.25)  # equal-power
    gL = np.cos(ang); gR = np.sin(ang)
    return (m*gL).astype(np.float32), (m*gR).astype(np.float32)

def render(sr, duration, t0, params=None):
    params = params or {}
    sr = int(sr)
    dur = float(duration)
    t0 = float(t0)
    bpm = max(1.0, _bpm(params))

    n = max(1, int(round(dur * sr)))
    t = (np.arange(n, dtype=np.float32) / sr) + np.float32(t0)

    # 16th grid
    step16 = (60.0 / bpm) / 4.0
    k16 = np.floor(t / step16).astype(np.int64)

    # Bursts every 2 beats (8x16ths)
    burst_on = ((k16 % 8) == 0).astype(np.float32)

    # Within bursts: 32nd strikes
    step32 = step16 / 2.0
    k32 = np.floor(t / step32).astype(np.int64)
    strikes = ((k32 % 2) == 0).astype(np.float32)

    # Hold burst gate for whole 2-beat window: use k16 block index
    burst_gate = (((k16 // 8) % 2) == 0).astype(np.float32)  # alternating 2-beat windows
    gate = strikes * burst_gate

    env = _env_click(n, sr, tau_ms=float(params.get("tau_ms", 18.0)))

    # Cycling pitch set; transpose affects pitch only
    notes = np.array([220, 247, 262, 294, 330, 370, 392, 440], dtype=np.float32) * np.float32(TF())
    idx = (k32 // 2) % len(notes)  # change pitch every 16th
    f = notes[idx.astype(np.int64)]

    phase = 2.0*np.pi*np.cumsum(f).astype(np.float32) / np.float32(sr)
    m = np.sin(phase).astype(np.float32) * env * gate * np.float32(params.get("amp", 0.28))

    m = _hp1(m, a=float(params.get("hp", 0.997)))
    L, R = _pan(m, pan=float(params.get("pan", 0.15)))
    return np.stack([L, R], axis=0)
