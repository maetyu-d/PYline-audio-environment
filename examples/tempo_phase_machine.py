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
    # Mark Fell / Ikeda-ish: extreme pulses whose density follows tempo grid
    sr=_sr(sr); dur=_dur(duration); bpm=_bpm()
    n=int(round(dur*sr))
    t=np.arange(n, dtype=np.float32)/sr

    base = 60.0/bpm/4.0  # 16th grid
    k = np.floor((t+float(t0))/base).astype(np.int64)

    # density changes every bar
    bar = (k//16).astype(np.int64)
    dens = (1 + (bar % 6)).astype(np.int64)  # 1..6 pulses per 16th slot internally

    # Create a pulse train inside each 16th
    frac = ((t+float(t0))/base) % 1.0
    # pulses at dens evenly spaced
    pulse = (np.mod(np.floor(frac*dens), 1) == 0).astype(np.float32)
    # sharpen to thin clicks
    click = (pulse * (frac < (1.0/(dens+1e-6))*0.05)).astype(np.float32)

    env = _env_click(n, sr, tau_ms=2.0)
    m = _hp1(click*env*1.2, 0.99) * 0.7
    return np.stack(_pan_stereo(m, pan=0.0), axis=0)
