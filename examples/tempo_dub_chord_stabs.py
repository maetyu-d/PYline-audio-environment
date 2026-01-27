import numpy as np

# Tempo-linked dub chord stabs (fixed, app-compatible)
# - render(sr, duration, t0, params=None) -> stereo (2,n) float32
# - Uses CLIP_BPM when available (track tempo)
# - Uses CLIP_TRANSPOSE via TF() for pitch only
# - Memory-safe: allocates only (n,) buffers for the clip duration

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
    try:
        return float(CLIP_BPM)
    except Exception:
        pass
    try:
        return float(params.get("bpm", 140.0))
    except Exception:
        return 140.0

def _env_adsr(n, a=0.01, d=0.08, s=0.35, r=0.18):
    n = int(max(1, n))
    aN = max(1, int(n*a))
    dN = max(1, int(n*d))
    rN = max(1, int(n*r))
    sN = max(0, n - (aN+dN+rN))
    e = np.zeros(n, dtype=np.float32)
    e[:aN] = np.linspace(0,1,aN,endpoint=False,dtype=np.float32)
    e[aN:aN+dN] = np.linspace(1,s,dN,endpoint=False,dtype=np.float32)
    if sN:
        e[aN+dN:aN+dN+sN] = np.float32(s)
    e[aN+dN+sN:] = np.linspace(s,0,rN,endpoint=False,dtype=np.float32)
    return e

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

def _softclip(x):
    return np.tanh(x).astype(np.float32)

def render(sr, duration, t0, params=None):
    params = params or {}
    sr = int(sr)
    duration = float(duration)
    t0 = float(t0)

    bpm = max(1.0, _bpm(params))
    root = float(params.get("root", 196.0)) * TF()
    amp = float(params.get("amp", 0.35))
    swing = float(params.get("swing", 0.0))  # 0..0.25 typical
    swing = float(np.clip(swing, 0.0, 0.35))

    n = max(1, int(round(duration * sr)))
    L = np.zeros(n, dtype=np.float32)
    R = np.zeros(n, dtype=np.float32)

    spb = 60.0 / bpm
    # stab every 2 beats by default
    step = float(params.get("step_beats", 2.0)) * spb
    stab_len = float(params.get("stab_sec", 0.18))
    stabN = max(32, int(sr * stab_len))

    # chord shape (minor 7-ish, dubby)
    chord = params.get("chord", [0, 7, 10, 14])  # semitones
    detune = float(params.get("detune", 0.003))  # small inharm
    bright = float(params.get("bright", 1.0))

    # fixed RNG per clip start so it’s stable on rerender
    seed = int((t0*1e6) % 2**32)
    rng = np.random.default_rng(seed)

    i = 0
    while True:
        te = i*step - (t0 % step)
        # add swing on odd stabs if desired
        if (i % 2) == 1:
            te += swing * step
        if te >= duration:
            break
        if te >= 0.0:
            idx = int(te * sr)
            end = min(n, idx + stabN)
            segN = end - idx
            if segN > 0:
                t = (np.arange(segN, dtype=np.float32) / sr)
                env = _env_adsr(segN, a=0.02, d=0.10, s=0.18, r=0.25)

                # choose inversion / octave shift lightly
                octave = int(rng.integers(-1, 2))
                base = root * (2.0**octave)

                sig = np.zeros(segN, dtype=np.float32)
                for semi in chord:
                    f = base * (2.0**(float(semi)/12.0)) * bright
                    # 2 detuned sines per partial for thickness
                    sig += np.sin(2*np.pi*f*(1.0-detune)*t).astype(np.float32)
                    sig += np.sin(2*np.pi*f*(1.0+detune)*t + 0.3).astype(np.float32)

                sig *= (env / max(1.0, float(len(chord))*2.0))  # normalize
                # simple dubby filtering: one-pole lowpass-ish via cumulative smoothing
                # (cheap + stable)
                a = float(params.get("lp", 0.08))  # smaller = darker
                a = float(np.clip(a, 0.01, 0.25))
                y = np.empty_like(sig)
                acc = np.float32(0.0)
                aa = np.float32(a)
                for k in range(segN):
                    acc = acc + aa*(sig[k] - acc)
                    y[k] = acc
                sig = y

                sig = _dc_block(sig)
                sig = _softclip(sig * amp * 2.2)

                # stereo spread: random-ish per stab but stable per clip
                pan = float(rng.uniform(-0.6, 0.6))
                gl = np.float32(0.5*(1.0 - pan))
                gr = np.float32(0.5*(1.0 + pan))
                L[idx:end] += sig[:segN] * gl
                R[idx:end] += sig[:segN] * gr

        i += 1

    out = _softclip(np.stack([L, R], axis=0) * 1.2)
    return out
