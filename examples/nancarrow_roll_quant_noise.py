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


def _exp_env(n, a=10.0):
    x = np.linspace(0.0, 1.0, int(n), endpoint=False, dtype=np.float32)
    return np.exp(-np.float32(a) * x).astype(np.float32)

def _ping(sr, f, ms, gain=1.0):
    n = max(1, int(sr * (float(ms)/1000.0)))
    t = np.arange(n, dtype=np.float32) / float(sr)
    env = _exp_env(n, a=16.0)
    return (np.sin(2*np.pi*np.float32(f)*t) * env * np.float32(gain)).astype(np.float32)

def render(sr, duration, t0, params=None):
    """Conlon Nancarrow-ish quantised roll ticks + noisy felt. Fixed signature & indentation."""
    params = params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)

    bpm = float(params.get("bpm", 160.0))
    grid = float(params.get("grid", 16.0))  # 16 -> 16ths
    ratios = params.get("ratios", [1.0, 5/4, 7/6, 9/8, 11/10])
    density = float(params.get("density", 0.55))
    noise_amt = float(params.get("noise", 0.03))
    note_min = float(params.get("note_min", 180.0)) * TF()
    note_max = float(params.get("note_max", 1600.0)) * TF()

    n = max(1, int(round(duration*sr)))
    L = np.zeros(n, dtype=np.float32)
    R = np.zeros(n, dtype=np.float32)

    sec_per_beat = 60.0 / max(1e-6, bpm)
    base_step = sec_per_beat / (grid/4.0)

    rng = np.random.default_rng(int((t0+duration)*1e6) & 0xffffffff)

    ping_bank = []
    freqs = np.geomspace(max(30.0, note_min), max(note_min*1.01, note_max), num=24).astype(np.float32)
    for f in freqs:
        ping_bank.append(_ping(sr, float(f), ms=rng.uniform(6, 18), gain=1.0))

    for lane_i, r in enumerate(ratios):
        step = base_step / float(r)
        swing = (lane_i * 0.007) * sec_per_beat
        t_cur = (math.floor(t0/step) * step) - t0
        while t_cur < duration + step:
            if t_cur >= 0 and rng.random() < density:
                idx = int(t_cur * sr)
                if 0 <= idx < n:
                    pick = ping_bank[int(rng.integers(0, len(ping_bank)))]
                    m = len(pick)
                    end = min(n, idx + m)
                    g = float(0.10 + 0.18 * rng.random())
                    pan = float(rng.uniform(-0.85, 0.85))
                    lmul = np.float32(g * (0.5 * (1.0 - pan)))
                    rmul = np.float32(g * (0.5 * (1.0 + pan)))
                    L[idx:end] += pick[:end-idx] * lmul
                    R[idx:end] += pick[:end-idx] * rmul
            t_cur += step + (swing if (int((t0+t_cur)/step) & 1) else -swing)

    if noise_amt > 0:
        wn = rng.standard_normal(n).astype(np.float32) * np.float32(noise_amt)
        wn = np.tanh(wn * 2.5) * np.float32(noise_amt)
        L += wn * np.float32(0.7)
        R += wn * np.float32(0.7)

    outL = np.tanh(L * 1.2).astype(np.float32)
    outR = np.tanh(R * 1.2).astype(np.float32)
    return np.stack([outL, outR], axis=0)
