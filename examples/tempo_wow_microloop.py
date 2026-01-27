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
    # tempo-synced microloop with wow (Oval-ish but clean)
    sr=_sr(sr); dur=_dur(duration); bpm=_bpm()
    n=int(round(dur*sr))
    t=np.arange(n, dtype=np.float32)/sr

    # loop length = 1 beat
    loop = 60.0/bpm
    # build a tiny source: filtered noise + tone
    rng=np.random.default_rng(42)
    srcN=int(sr*loop)
    src = (rng.standard_normal(srcN).astype(np.float32)*0.12 + np.sin(2*np.pi*220*np.arange(srcN)/sr).astype(np.float32)*0.06)
    src = _hp1(src, 0.995)

    # wow: slow lfo modulates playback speed
    wow = 0.004*np.sin(2*np.pi*0.7*t).astype(np.float32)
    pos = (np.cumsum(1.0+wow) % srcN).astype(np.float32)
    i0 = np.floor(pos).astype(np.int64)
    i1 = (i0+1) % srcN
    frac = pos - i0
    m = (src[i0]*(1-frac) + src[i1]*frac).astype(np.float32)

    # gate on 8ths
    step = 60.0/bpm/2.0
    frac2 = ((t+float(t0))/step) % 1.0
    env = (np.clip(frac2/0.02,0,1)*np.exp(-frac2*6.0)).astype(np.float32)
    m *= env*0.9
    return np.stack(_pan_stereo(m, pan=0.1), axis=0)
