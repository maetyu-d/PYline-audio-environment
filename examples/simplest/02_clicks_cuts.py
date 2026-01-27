import math, random

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


def render(sr, duration, t0, params=None):
    params = params or {}
    n = int(sr * duration)
    seed = int(params.get("seed", 1))
    density = float(params.get("density", 14.0))  # clicks per second
    random.seed(seed + int(t0 * 1000))

    out = [0.0] * n
    num = max(1, int(duration * density))
    for _ in range(num):
        at = random.randint(0, n-1)
        w = random.randint(8, 90)  # click width samples
        amp = random.uniform(0.2, 1.0) * (1.0 if random.random() < 0.8 else -1.0)
        for i in range(w):
            j = at + i
            if j >= n: break
            env = math.exp(-i / (w/6))
            out[j] += amp * env

    # tiny DC kill + clamp
    m = sum(out)/n
    for i in range(n):
        out[i] = max(-1.0, min(1.0, (out[i]-m)*0.9))
    return out