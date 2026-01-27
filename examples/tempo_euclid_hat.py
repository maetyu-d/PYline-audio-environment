# PY Timeline tempo-linked example
# Uses CLIP_BPM injected by the app (track tempo), plus CLIP_DURATION, SR.
# render() can be called with various signatures; this implementation supports kwargs too.
import numpy as np



# --- transpose helper (semitones) ---
def TF(semi=None):
    """Transpose factor: 2**(semitones/12). Reads CLIP_TRANSPOSE or params['transpose']."""
    try:
        s = float(CLIP_TRANSPOSE if semi is None else semi)
    except Exception:
        try:
            if semi is None and isinstance(params := globals().get("_PARAMS", None), dict):
                s = float(params.get("transpose", 0.0))
            else:
                s = float(semi) if semi is not None else 0.0
        except Exception:
            s = 0.0
    return 2.0 ** (s / 12.0)
def _get(name, default):
    try:
        return globals().get(name, default)
    except Exception:
        return default

def _bpm():
    return float(_get("CLIP_BPM", 120.0))

def _sr(sr=None):
    return int(sr if sr is not None else _get("SR", 44100))

def _dur(d=None):
    return float(d if d is not None else _get("CLIP_DURATION", 1.0))

def _env_click(n, sr, tau_ms=3.0):
    # simple fast decay for clicks
    tau = max(1, int(sr * (tau_ms/1000.0)))
    e = np.exp(-np.arange(n, dtype=np.float32)/tau)
    return e.astype(np.float32)

def _hp1(x, a=0.995):
    # one-pole highpass via DC-blocker
    y = np.empty_like(x)
    xm1 = 0.0
    ym1 = 0.0
    for i in range(len(x)):
        y[i] = x[i] - xm1 + a*ym1
        xm1 = x[i]
        ym1 = y[i]
    return y

def _pan_stereo(m, pan=0.0):
    pan = float(np.clip(pan, -1.0, 1.0))
    ang = (pan + 1.0) * (np.pi * 0.25)   # equal-power
    gL = np.cos(ang); gR = np.sin(ang)
    return (m*gL).astype(np.float32), (m*gR).astype(np.float32)

def _euclid(pulses, steps):
    pulses = int(max(0, min(steps, pulses)))
    steps = int(max(1, steps))
    # simple Bjorklund-ish bucket method
    pat = np.zeros(steps, dtype=np.int32)
    bucket = 0
    for i in range(steps):
        bucket += pulses
        if bucket >= steps:
            bucket -= steps
            pat[i] = 1
    return pat

def render(duration=None, sr=None, t0=0.0, params=None):
    sr=_sr(sr); dur=_dur(duration); bpm=_bpm()
    n=int(round(dur*sr))
    t=np.arange(n, dtype=np.float32)/sr

    steps = 16
    pulses = 11
    pat = _euclid(pulses, steps)
    step = 60.0/bpm/4.0  # 16th
    ph = (t+float(t0))/step
    k = np.floor(ph).astype(np.int64) % steps
    frac = (ph % 1.0).astype(np.float32)

    trig = pat[k].astype(np.float32)
    env = (np.clip(frac/0.01, 0, 1) * np.exp(-frac*18.0)).astype(np.float32)

    rng = np.random.default_rng(1234)
    noise = rng.standard_normal(n).astype(np.float32)
    m = _hp1(noise, 0.97) * env * trig * 0.18
    m += np.sin(2*np.pi*(7600.0*TF())*t).astype(np.float32) * env * trig * 0.02
    return np.stack(_pan_stereo(m, pan=0.25), axis=0)
