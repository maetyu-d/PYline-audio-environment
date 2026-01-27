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

    beat = 60.0/bpm
    # 1/4 note triggers
    phase = (t+float(t0))/beat
    trig = (np.floor(phase) != np.floor(np.concatenate(([phase[0]-1], phase[:-1])))).astype(np.float32)

    # kick: sine with exponential pitch drop
    env = np.exp(-t*12.0).astype(np.float32)
    drop = np.exp(-t*18.0).astype(np.float32)
    f = 90.0 + 120.0*drop
    ph = 2*np.pi*np.cumsum(f)/sr
    kick = np.sin(ph).astype(np.float32) * env

    # apply trig as impulse into envelope (simple: reset env per trigger)
    out = np.zeros(n, dtype=np.float32)
    cur = 0.0
    for i in range(n):
        if trig[i] > 0.5:
            cur = 1.0
        cur *= 0.9992
        out[i] = kick[i] * cur
    out *= 0.95
    return np.stack(_pan_stereo(out, pan=0.0), axis=0)
