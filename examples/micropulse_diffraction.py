import numpy as np

# Micropulse Diffraction (fixed, app-compatible)
# - render(sr, duration, t0, params=None) -> stereo (2,n) float32
# - Uses CLIP_BPM when available
# - Uses CLIP_TRANSPOSE via TF() to shift resonant center
# A dense, crystalline microclick texture with "diffracted" delays (comb taps).

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
    try:
        return float(CLIP_BPM)
    except Exception:
        pass
    try:
        return float(params.get("bpm", 128.0))
    except Exception:
        return 128.0

def _env_exp(n, tau_ms, sr):
    n = int(max(1, n))
    tau = max(1.0, float(sr) * (float(tau_ms)/1000.0))
    return np.exp(-np.arange(n, dtype=np.float32)/tau).astype(np.float32)

def _dc_block(x, a=0.995):
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

def render(sr, duration, t0, params=None):
    params = params or {}
    sr = int(sr)
    duration = float(duration)
    t0 = float(t0)

    bpm = max(1.0, _bpm(params))
    n = max(1, int(round(duration * sr)))

    # density + click shape
    density = float(params.get("density", 1.0))   # ~0.5..2.0
    tau_ms  = float(params.get("tau_ms", 9.0))    # click decay
    amp     = float(params.get("amp", 0.25))

    # resonant center (transpose affects this)
    base_hz = float(params.get("base_hz", 800.0)) * TF()
    base_hz = float(np.clip(base_hz, 80.0, 12000.0))

    # tempo grid (32nds)
    spb = 60.0 / bpm
    step = spb / 8.0
    # how many pulses per grid tick
    pulses_per = int(np.clip(int(params.get("pulses_per", 1)), 1, 8))

    # stable RNG based on clip position
    seed = int((t0 * 1e6) % 2**32)
    rng = np.random.default_rng(seed)

    mono = np.zeros(n, dtype=np.float32)

    # a few short comb/diffraction taps (in samples)
    tap_ms = params.get("tap_ms", [1.7, 3.4, 6.8, 10.2])
    taps = []
    for ms in tap_ms:
        try:
            taps.append(max(1, int(float(ms) * 0.001 * sr)))
        except Exception:
            pass
    if not taps:
        taps = [max(1, int(0.003*sr))]

    # Build events
    num_steps = int(duration / step) + 2
    for k in range(num_steps):
        te0 = k*step - (t0 % step)
        if te0 >= duration:
            break
        if te0 < 0.0:
            continue

        # probabilistic dropout
        if rng.random() > min(1.0, 0.85 * density):
            continue

        for p in range(pulses_per):
            jitter = (rng.random() - 0.5) * (0.18 * step)  # small microtiming
            te = te0 + jitter
            if te < 0.0 or te >= duration:
                continue
            idx = int(te * sr)
            # click length (2-12 ms)
            click_ms = float(rng.uniform(2.0, 12.0))
            m = max(8, int(sr * click_ms/1000.0))
            end = min(n, idx + m)
            segN = end - idx
            if segN <= 0:
                continue

            t = (np.arange(segN, dtype=np.float32) / sr)
            env = _env_exp(segN, tau_ms=tau_ms, sr=sr)

            # "glass" carrier: noisy phase FM-ish, but cheap
            f = base_hz * (2.0 ** (rng.uniform(-0.5, 0.75)))
            f = float(np.clip(f, 60.0, 14000.0))
            ph = 2*np.pi*f*t
            mod = 0.8*np.sin(2*np.pi*(f*0.125)*t + rng.uniform(0,2*np.pi)).astype(np.float32)
            sig = np.sin(ph + mod).astype(np.float32)

            # add grit
            sig += 0.25*(rng.random(segN).astype(np.float32)-0.5)

            sig *= env * float(rng.uniform(0.25, 1.0))

            # diffraction taps: add a few delayed copies within the click window
            for d in taps:
                if d < segN:
                    sig[d:] += 0.35 * sig[:-d]

            mono[idx:end] += sig[:segN]

    mono = _dc_block(mono)
    mono = np.tanh(mono * (amp * 3.0)).astype(np.float32)

    # simple stereo decorrelation: tiny allpass-ish delay between channels
    dL = int(np.clip(int(params.get("stereo_delay_ms", 0.9) * 0.001 * sr), 1, 4096))
    L = mono.copy()
    R = mono.copy()
    if dL < n:
        R[dL:] = 0.82*R[dL:] + 0.18*L[:-dL]

    return np.stack([L, R], axis=0).astype(np.float32)
