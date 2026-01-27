import math

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


import random

def render(sr, duration, t0, params=None):
    """Clicks & cuts: randomized micro-clicks. Returns stereo (duplicated). Transpose-safe."""
    params = params or {}
    sr = int(sr)
    duration = float(duration)
    t0 = float(t0)
    n = max(1, int(round(sr * duration)))

    seed = int(params.get("seed", 1))
    density = float(params.get("density", 14.0))  # clicks per second
    random.seed(seed + int(t0 * 1000))

    out = [0.0] * n
    num = max(1, int(duration * density))
    for _ in range(num):
        at = random.randint(0, n - 1)
        w = random.randint(8, 90)  # click width samples
        amp = random.uniform(0.2, 1.0) * (1.0 if random.random() < 0.8 else -1.0)
        # simple exponential declick
        decay = max(1.0, (w / 6.0))
        for i in range(w):
            j = at + i
            if j >= n:
                break
            env = math.exp(-i / decay)
            out[j] += amp * env

    # DC kill + clamp
    m = sum(out) / float(n)
    for i in range(n):
        v = (out[i] - m) * 0.9
        if v > 1.0: v = 1.0
        if v < -1.0: v = -1.0
        out[i] = v

    return out, out[:]  # stereo duplicate
