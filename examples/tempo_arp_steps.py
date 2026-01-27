# PY Timeline tempo-linked example
# Uses CLIP_BPM injected by the app (track tempo), plus CLIP_DURATION, SR.
# render() can be called with various signatures; this implementation supports kwargs too.
import numpy as np

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

def render(duration=None, sr=None, t0=0.0, params=None):
    sr=_sr(sr); dur=_dur(duration); bpm=_bpm()
    n=int(round(dur*sr))
    t=np.arange(n, dtype=np.float32)/sr

    step = 60.0/bpm/4.0  # 16th
    k = np.floor((t+float(t0))/step).astype(np.int64)

    scale = np.array([0,2,3,5,7,10], dtype=np.int32)  # minor-ish
    seq = (k % 16).astype(np.int64)
    deg = scale[(seq % len(scale)).astype(np.int64)]
    base = 110.0
    f = base * (2.0 ** ((deg + 12*((seq//6)%2))/12.0)).astype(np.float32)

    # envelope per step
    frac = ((t+float(t0))/step) % 1.0
    env = (np.clip(frac/0.03,0,1) * np.exp(-frac*10.0)).astype(np.float32)

    ph = 2*np.pi*np.cumsum(f)/sr
    m = (np.sin(ph) + 0.35*np.sin(2*ph) + 0.18*np.sin(3*ph)).astype(np.float32) * env * 0.22
    return np.stack(_pan_stereo(m, pan=-0.35), axis=0)
