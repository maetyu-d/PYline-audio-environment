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
    # Tempo-quantised 'glass' chord blocks (Oversteps-ish vibe)
    sr=_sr(sr); dur=_dur(duration); bpm=_bpm()
    n=int(round(dur*sr))
    t=np.arange(n, dtype=np.float32)/sr

    step = 60.0/bpm/2.0   # 8th-note blocks
    idx = np.floor((t+float(t0))/step).astype(np.int64)

    # choose chord per block
    # a few pitch sets in Hz (just intonation-ish-ish)
    chords = [
      [220, 277.18, 330, 440],
      [246.94, 311.13, 370, 493.88],
      [196, 247, 294, 392],
      [261.63, 329.63, 392, 523.25],
    ]
    chord_id = (idx % len(chords)).astype(np.int64)
    f0 = np.zeros(n, dtype=np.float32)
    f1 = np.zeros(n, dtype=np.float32)
    f2 = np.zeros(n, dtype=np.float32)
    f3 = np.zeros(n, dtype=np.float32)
    for k,ch in enumerate(chords):
        m = chord_id==k
        f0[m]=ch[0]; f1[m]=ch[1]; f2[m]=ch[2]; f3[m]=ch[3]

    # soft attack/decay per block
    frac = ((t+float(t0))/step) % 1.0
    a = np.clip(frac/0.08, 0, 1)
    d = np.clip((1-frac)/0.12, 0, 1)
    env = (a*d).astype(np.float32)

    ph0 = 2*np.pi*np.cumsum(f0)/sr
    ph1 = 2*np.pi*np.cumsum(f1)/sr
    ph2 = 2*np.pi*np.cumsum(f2)/sr
    ph3 = 2*np.pi*np.cumsum(f3)/sr
    sig = (np.sin(ph0)+0.8*np.sin(ph1)+0.6*np.sin(ph2)+0.5*np.sin(ph3)).astype(np.float32)
    sig *= env*0.22
    sig = _hp1(sig, 0.999)
    return np.stack(_pan_stereo(sig, pan=-0.2), axis=0)
