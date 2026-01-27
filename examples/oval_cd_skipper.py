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
    """Oval-ish: fragile buffer that 'skips' and replays tiny chunks with glitch seams."""
    params = params or {}
    sr=int(sr); duration=float(duration); t0=float(t0)
    bpm = max(1.0, _bpm(params, 112.0))
    gmin = float(params.get("grain_ms_min", 12.0))
    gmax = float(params.get("grain_ms_max", 45.0))
    pskip = float(params.get("pskip", 0.35))
    blur = float(params.get("blur", 0.6))
    tone = float(params.get("tone", 0.6))

    n = max(1, int(round(duration*sr)))
    t = np.arange(n, dtype=np.float32)/float(sr)

    rng = np.random.default_rng(int((t0+duration)*1e6) & 0xffffffff)

    bed = (np.sin(2*np.pi*np.float32(110.0)*TF()*(t+t0)) +
           0.35*np.sin(2*np.pi*np.float32(220.0)*TF()*(t+t0)) +
           0.18*np.sin(2*np.pi*np.float32(330.0)*TF()*(t+t0))).astype(np.float32) * np.float32(tone*0.20)
    clicks = np.zeros(n, dtype=np.float32)
    for _ in range(max(6, int(duration*12))):
        i = int(rng.integers(0, n))
        clicks[i] += float(rng.uniform(-1,1))
    k = np.exp(-np.linspace(0,1,int(sr*0.002),endpoint=False,dtype=np.float32)*12.0).astype(np.float32)
    clicks = np.convolve(clicks, k, mode="same").astype(np.float32) * np.float32(0.15)

    src = bed + clicks
    out = np.zeros(n, dtype=np.float32)

    i = 0
    while i < n:
        gms = float(rng.uniform(gmin, gmax))
        glen = max(8, int(sr*(gms/1000.0)))
        end = min(n, i+glen)

        if rng.random() < pskip and i > glen*2:
            back = int(rng.integers(glen, min(i, glen*40)))
            src_start = max(0, i - back)
        else:
            src_start = i

        chunk = src[src_start:src_start+(end-i)]
        m = len(chunk)
        if m > 16 and blur > 0:
            f = int(min(m//2, max(2, int(m*0.25*blur))))
            win = np.ones(m, dtype=np.float32)
            ramp = np.linspace(0,1,f,endpoint=False,dtype=np.float32)
            win[:f] *= ramp
            win[-f:] *= ramp[::-1]
            chunk = chunk * win

        out[i:end] += chunk.astype(np.float32)
        i = end

    d = int(max(1, min(n-1, sr*0.0007)))
    L = out
    R = np.concatenate([np.zeros(d, dtype=np.float32), out[:-d]]) if d < n else out.copy()
    mix = np.stack([L,R], axis=0) * np.float32(1.2)
    mix = np.tanh(mix).astype(np.float32)
    return mix
