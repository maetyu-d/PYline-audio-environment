# PY Timeline tempo-linked rhythm example
# Reads CLIP_BPM (track tempo), plus SR and CLIP_DURATION injected by the app.
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

def _hp1(x, a=0.995):
    y = np.empty_like(x)
    xm1 = 0.0
    ym1 = 0.0
    for i in range(len(x)):
        y[i] = x[i] - xm1 + a*ym1
        xm1 = x[i]
        ym1 = y[i]
    return y

def _lp1(x, a=0.05):
    y = np.empty_like(x)
    ym1 = 0.0
    a = float(np.clip(a, 0.0001, 0.9999))
    for i in range(len(x)):
        ym1 = ym1 + a*(x[i]-ym1)
        y[i]=ym1
    return y

def _env_per_step(frac, atk=0.03, dec=8.0):
    a = np.clip(frac/max(1e-6, atk), 0, 1)
    return (a*np.exp(-frac*dec)).astype(np.float32)

def _pan(m, pan=0.0):
    pan = float(np.clip(pan, -1.0, 1.0))
    ang = (pan + 1.0) * (np.pi * 0.25)
    gL = np.cos(ang); gR = np.sin(ang)
    return (m*gL).astype(np.float32), (m*gR).astype(np.float32)

def _trigs(t, step, t0=0.0):
    ph = (t+float(t0))/step
    f = np.floor(ph)
    fm1 = np.floor(np.concatenate(([ph[0]-1], ph[:-1])))
    return (f != fm1).astype(np.float32), ph, (ph % 1.0).astype(np.float32)
def render(duration=None, sr=None, t0=0.0, params=None):
    sr=_sr(sr); dur=_dur(duration); bpm=_bpm()
    n=int(round(dur*sr))
    t=np.arange(n, dtype=np.float32)/sr
    beat=60.0/bpm

    trig, _, _ = _trigs(t, beat, t0)

    drop=np.exp(-t*26.0).astype(np.float32)
    f=55.0 + 280.0*drop
    ph=2*np.pi*np.cumsum(f)/sr
    osc=np.sin(ph).astype(np.float32)

    out=np.zeros(n, dtype=np.float32)
    cur=0.0
    for i in range(n):
        if trig[i] > 0.5:
            cur = 1.0
        cur *= 0.9986
        out[i] = osc[i] * cur

    click = _hp1(trig.astype(np.float32), 0.2) * 0.25
    out = np.tanh((out*5.5) + click).astype(np.float32) * 0.55

    return np.stack(_pan(out, pan=0.0), axis=0)
