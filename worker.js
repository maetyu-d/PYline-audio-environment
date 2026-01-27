// worker.js - Pyodide renderer + mixer with per-track vol/pan
let pyodide = null;
let numpyReady = false;

async function ensurePy(){
  if(pyodide) return pyodide;
  importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js");
  pyodide = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/" });
  return pyodide;
}
async function ensureNumpy(){
  if(numpyReady) return;
  await pyodide.loadPackage("numpy");
  numpyReady = true;
}

function toF32(x){
  if(x instanceof Float32Array) return x;
  if(Array.isArray(x)) return new Float32Array(x);
  return new Float32Array(x);
}

self.onmessage = async (ev)=>{
  const msg = ev.data;
  try{
    if(msg.type==="init"){
      await ensurePy(); await ensureNumpy();
      self.postMessage({type:"inited"});
      return;
    }
    if(msg.type==="renderAll"){
      await ensurePy(); await ensureNumpy();
      const {sr, bits, totalDur, clips, wavClips, tracks} = msg;

      // track gains map
      const trackMap = new Map();
      if(tracks){
        for(const t of tracks){
          trackMap.set(t.id, {
            vol: (t.vol==null?1:Number(t.vol)),
            pan: (t.pan==null?0:Number(t.pan))
          });
        }
      }
      function gainsFor(trackId){
        const tp = trackMap.get(trackId) || {vol:1, pan:0};
        const vol = Math.max(0, (tp.vol==null?1:tp.vol));
        const pan = Math.max(-1, Math.min(1, (tp.pan==null?0:tp.pan)));
        const ang = (pan + 1) * Math.PI * 0.25; // equal-power
        return { gL: Math.cos(ang)*vol, gR: Math.sin(ang)*vol };
      }

      const nSamp = Math.max(1, Math.floor(Number(totalDur) * sr));
      const mixL = new Float32Array(nSamp);
      const mixR = new Float32Array(nSamp);

      // wav map: wavClips entries use placed-clip id
      const wavMap = new Map();
      if(wavClips){
        for(const w of wavClips){
          wavMap.set(w.id, {L: toF32(w.L), R: toF32(w.R), sr: Number(w.sr)||sr});
        }
      }

      for(const c of clips){
        const startS = Math.max(0, Number(c.start)||0);
        const durS = Math.max(0.01, Number(c.dur)||0.01);
        const startI = Math.floor(startS*sr);
        const durI = Math.max(1, Math.floor(durS*sr));
        if(startI >= nSamp) continue;

        let clipL=null, clipR=null;

        if(c.type==="wav"){
          const w = wavMap.get(c.id);
          if(!w) continue;
          const srcN = w.L.length;
          const outN = durI;
          const l = new Float32Array(outN);
          const r = new Float32Array(outN);
          const ratio = (w.sr||sr) / sr;
          for(let i=0;i<outN;i++){
            const x=i*ratio;
            const i0=Math.floor(x);
            const i1=Math.min(srcN-1, i0+1);
            const t=x-i0;
            const a0=w.L[i0]||0, a1=w.L[i1]||0;
            const b0=w.R[i0]||0, b1=w.R[i1]||0;
            l[i]=a0+(a1-a0)*t;
            r[i]=b0+(b1-b0)*t;
          }
          clipL=l; clipR=r;
        } else if(c.type==="py"){
          const code = c.code || "";
          const params = c.params || {};
          const t0 = Number(c.t0)||0;

          pyodide.globals.set("_CODE", code);
          pyodide.globals.set("_DUR", durS);
          pyodide.globals.set("_SR", sr);
          pyodide.globals.set("_T0", t0);
          pyodide.globals.set("_BPM", Number(c.bpm||120));
          pyodide.globals.set("_TRANSPOSE", Number(c.transpose||0));
          // also expose transpose in params (common helper path)
          try{ if(params && typeof params==="object") params.transpose = Number(c.transpose||0); }catch(e){}
          pyodide.globals.set("_PARAMS", params);

          const pyRes = pyodide.runPython(`
import numpy as np, inspect
code = _CODE
g = {}
exec(code, g, g)

# PARAMS: always a real dict
try:
    p = _PARAMS.to_py() if hasattr(_PARAMS, "to_py") else _PARAMS
except Exception:
    p = _PARAMS
if isinstance(p, dict):
    P = p
elif hasattr(p, "keys"):
    try:
        P = {k: p[k] for k in list(p.keys())}
    except Exception:
        P = {}
else:
    P = {}

# inject globals (for scripts that ignore args)
g["CLIP_DURATION"] = float(_DUR)
g["CLIP_START"] = float(_T0)
g["CLIP_BPM"] = float(_BPM)
g["CLIP_TRANSPOSE"] = float(_TRANSPOSE)
g["SR"] = int(_SR)
g["PARAMS"] = P

fn = g.get("render", None)
if fn is None:
    raise Exception("No render() found")

def _call(fn, duration, sr, t0, params):
    # keyword first
    try:
        sig = inspect.signature(fn)
        names = list(sig.parameters.keys())
    except Exception:
        names = []
    if names:
        kw = {}
        for name in names:
            n = name.lower()
            if n in ("duration","dur","length","seconds"):
                kw[name] = duration
            elif n in ("sr","samplerate","sample_rate","rate"):
                kw[name] = sr
            elif n in ("t0","time0","offset","start","t"):
                kw[name] = t0
            elif n in ("params","p","kwargs","options"):
                kw[name] = params
        try:
            return fn(**kw)
        except TypeError:
            pass

    # positional fallbacks
    for args in [
        (duration, sr, t0, params),
        (duration, sr, t0),
        (duration, sr),
        (duration,),
        tuple(),
        (sr, duration, t0, params),
        (sr, duration, t0),
        (sr, duration),
        (sr,),
    ]:
        try:
            return fn(*args)
        except TypeError:
            continue
    raise TypeError("render() signature not supported")

out = _call(fn, float(_DUR), int(_SR), float(_T0), P)
a = np.asarray(out, dtype=np.float32)
if a.ndim == 1:
    a = np.stack([a,a], axis=0)
elif a.ndim == 2:
    if a.shape[0] == 2:
        pass
    elif a.shape[1] == 2:
        a = a.T
    else:
        a = a[:2,:] if a.shape[0] > 2 else np.vstack([a, a])
else:
    a = a.reshape(1,-1)
    a = np.stack([a[0],a[0]], axis=0)

n = int(round(float(_DUR) * int(_SR)))
if a.shape[1] < n:
    pad = np.zeros((2, n-a.shape[1]), dtype=np.float32)
    a = np.concatenate([a, pad], axis=1)
elif a.shape[1] > n:
    a = a[:, :n]

[a[0], a[1]]
          `);
          const chans = pyRes.toJs({create_proxies:false});
          clipL = (chans[0] instanceof Float32Array) ? chans[0] : new Float32Array(chans[0]);
          clipR = (chans[1] instanceof Float32Array) ? chans[1] : new Float32Array(chans[1]);
          pyRes.destroy && pyRes.destroy();
        }

        if(!clipL || !clipR) continue;

        // pitch (transpose) for PY clips too (simple resample)
        const pitch2 = Math.pow(2, (Number(c.transpose)||0)/12);
        if(pitch2 !== 1 && clipL && clipR){
          const srcL=clipL, srcR=clipR;
          const outN=srcL.length;
          const l=new Float32Array(outN);
          const r=new Float32Array(outN);
          const srcN=srcL.length;
          for(let i=0;i<outN;i++){
            const x=i*pitch2;
            const i0=Math.floor(x);
            const i1=Math.min(srcN-1, i0+1);
            const t=x-i0;
            const a0=srcL[i0]||0, a1=srcL[i1]||0;
            const b0=srcR[i0]||0, b1=srcR[i1]||0;
            l[i]=a0+(a1-a0)*t;
            r[i]=b0+(b1-b0)*t;
          }
          clipL=l; clipR=r;
        }

        const g = gainsFor(c.trackId);
        const endI = Math.min(nSamp, startI + clipL.length);
        for(let i=startI, j=0;i<endI;i++,j++){
          mixL[i] += clipL[j] * g.gL;
          mixR[i] += clipR[j] * g.gR;
        }
      }

      self.postMessage({type:"renderDone", L: mixL, R: mixR, sr, bits}, [mixL.buffer, mixR.buffer]);
      return;
    }
  }catch(e){
    self.postMessage({type:"err", err: (e && e.stack) ? e.stack : String(e)});
  }
};
