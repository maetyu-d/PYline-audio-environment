import numpy as np

# --- transpose helper (semitones) ---
def TF(semi=None):
    """Transpose factor: 2**(semitones/12).
    Reads CLIP_TRANSPOSE (preferred) or params['transpose'] / _PARAMS['transpose'].
    """
    def _g(d, k, default=0.0):
        try:
            return d.get(k, default)
        except Exception:
            return default

    s = None
    if semi is not None:
        try:
            s = float(semi)
        except Exception:
            s = 0.0

    if s is None:
        try:
            s = float(globals().get("CLIP_TRANSPOSE", 0.0))
        except Exception:
            s = None

    if s is None:
        try:
            s = float(_g(globals().get("_PARAMS", {}), "transpose", 0.0))
        except Exception:
            s = None

    if s is None:
        s = 0.0
    return 2.0 ** (float(s) / 12.0)


def _sr(sr=None):
    try:
        return int(sr if sr is not None else globals().get("SR", 44100))
    except Exception:
        return 44100

def _dur(d=None):
    try:
        return float(d if d is not None else globals().get("CLIP_DURATION", 1.0))
    except Exception:
        return 1.0

def render(duration=None, sr=None, t0=0.0, params=None):
    '''
    Tape oval loop (stereo):
    - smooth carrier + wow/flutter FM wobble
    - slow stereo orbit
    - duration-safe / memory-safe
    '''
    sr = _sr(sr)
    dur = _dur(duration)
    params = params or {}
    n = int(round(dur * sr))
    if n <= 0:
        return []
    t = (np.arange(n, dtype=np.float32) / sr) + np.float32(t0)

    wow = 0.003*np.sin(2*np.pi*0.4*t + 0.7)
    flutter = 0.0008*np.sin(2*np.pi*6.0*t + 1.3)

    base = 180.0 * TF()
    fm = base + 30.0*wow + 10.0*flutter
    ph = 2*np.pi*np.cumsum(fm).astype(np.float64)/sr
    mod = np.sin(ph).astype(np.float32)

    env = (np.sin(2*np.pi*0.33*t)**2 + np.cos(2*np.pi*0.21*t)**2).astype(np.float32)
    env = np.power(env, 0.9).astype(np.float32)

    sig = (mod * env * 0.25).astype(np.float32)

    L = (sig*(0.5 + 0.5*np.sin(2*np.pi*0.12*t + 0.2))).astype(np.float32)
    R = (sig*(0.5 + 0.5*np.cos(2*np.pi*0.12*t + 0.2))).astype(np.float32)

    f = min(int(0.01*sr), n//2)
    if f > 1:
        ramp = np.linspace(0, 1, f, endpoint=True).astype(np.float32)
        L[:f] *= ramp; R[:f] *= ramp
        L[-f:] *= ramp[::-1]; R[-f:] *= ramp[::-1]

    return np.stack([L, R], axis=0).tolist()
