// app.js - clean rebuild: always-rerender Play, track vol/pan UI, robust editor buttons
const $ = (id)=>document.getElementById(id);

const state = {
  audio:null,
  playSrc:null,
  inited:false,
  tracks:[],
  bin:[],     // loaded assets: {type, name, code?} or {type,wavId,L,R,sr,duration}
  clips:[],   // placed clips: {id, trackId, type, name, start, dur, code? , wavAssetId?}
  selectedTrackId:null,
  selectedClipId:null,
  editorClipId:null,
  zoom:1,
  scrollX:0,
  timeMode:"sec",
  dragging:null,
};

let nextId=1;
const uid=()=>String(nextId++);

function setStatus(s){ $("status").textContent = s; }
function ensureAudio(){
  if(state.audio) return state.audio;
  state.audio = new (window.AudioContext||window.webkitAudioContext)();
  return state.audio;
}
function sr(){ return Number($("sr").value); }
function bits(){ return Number($("bits").value); }
function snapVal(){ return Number($("snap").value||0); }

function roman(n){
  const map=[[1000,"M"],[900,"CM"],[500,"D"],[400,"CD"],[100,"C"],[90,"XC"],[50,"L"],[40,"XL"],[10,"X"],[9,"IX"],[5,"V"],[4,"IV"],[1,"I"]];
  let s=""; for(const [v,g] of map){ while(n>=v){ s+=g; n-=v; } } return s||"I";
}
function getTrack(id){ return state.tracks.find(t=>t.id===id); }
function getClip(id){ return state.clips.find(c=>c.id===id); }

function addTrack(){
  const n=state.tracks.length+1;
  const t={id:uid(), name:`Track ${roman(n)}`, bpm:120, len:16, vol:1.0, pan:0.0};
  state.tracks.push(t);
  if(!state.selectedTrackId) state.selectedTrackId=t.id;
  renderTracks();
  draw();
}

function renderTracks(){
  const list=$("trackList");
  list.innerHTML="";
  state.tracks.forEach((t,i)=>{
    const row=document.createElement("div");
    row.className="trackRow"+(t.id===state.selectedTrackId?" sel":"");
    row.innerHTML=`
      <div class="roman">${roman(i+1)}</div>
      <div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${t.name}</div>
      <input class="input" title="BPM" data-k="bpm" value="${t.bpm}"/>
      <input class="input" title="Len (s)" data-k="len" value="${t.len}"/>
      <input class="input" title="Vol" data-k="vol" value="${t.vol}"/>
      <input class="input" title="Pan (-1..+1)" data-k="pan" value="${t.pan}"/>
    `;
    row.addEventListener("click", (ev)=>{
      if(ev.target && ev.target.tagName==="INPUT") return;
      
      state.selectedTrackId=t.id;
      renderTracks(); renderSelected(); draw();
    });
    row.querySelectorAll("input").forEach(inp=>{
      // prevent the row click handler from stealing focus / re-rendering while editing
      inp.addEventListener("mousedown", (e)=>{ e.stopPropagation(); });
      inp.addEventListener("click", (e)=>{ e.stopPropagation(); });
      inp.addEventListener("dblclick", (e)=>{ e.stopPropagation(); });

      const commit = ()=>{
        const k=inp.dataset.k;
        const v=Number(inp.value);
        if(Number.isFinite(v)){
          if(k==="vol") t[k]=Math.max(0, Math.min(4, v));
          else if(k==="pan") t[k]=Math.max(-1, Math.min(1, v));
          else if(k==="bpm") t[k]=Math.max(1, Math.min(999, v));
          else if(k==="len") t[k]=Math.max(0.25, Math.min(10_000, v));
          else t[k]=v;
        }
        inp.value=t[k];
        // reflect tempo-grid changes immediately in ruler/selected panel
        if(k==="bpm" || k==="len"){
          renderSelected();
          draw();
        }
      };

      inp.addEventListener("change", (e)=>{ e.stopPropagation(); commit(); });
      inp.addEventListener("blur", commit);
      inp.addEventListener("keydown", (e)=>{
        if(e.key==="Enter"){ e.preventDefault(); e.stopPropagation(); inp.blur(); }
        if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); inp.value=t[inp.dataset.k]; inp.blur(); }
      });
    });
    list.appendChild(row);
  });
}

function renderBin(){
  const bin=$("clipBin");
  bin.innerHTML="";
  state.bin.forEach((a,idx)=>{
    const div=document.createElement("div");
    div.className="clipItem";
    div.innerHTML=`
      <div style="min-width:0">
        <div style="font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${a.name}</div>
        <div style="color:#a1a1aa;font-size:12px">${a.type.toUpperCase()}</div>
      </div>
      <div class="clipBtns"><button class="chip">Place</button><button class="chip clipRemove">Remove</button></div>
    `;
    const btns=div.querySelectorAll("button");
    btns[0].onclick=()=>placeAsset(a);
    btns[1].onclick=()=>removeAsset(idx);
    bin.appendChild(div);
  });
}

function syncPyHeader(c){
  if(!c || c.type!=="py") return;
  const tr=getTrack(c.trackId);
  const hdrStart="# --- PY TIMELINE CLIP VARS (AUTO) ---";
  const hdrEnd  ="# --- END PY TIMELINE CLIP VARS ---";
  const start=(Number(c.start)||0).toFixed(6);
  const dur=(Number(c.dur)||0.01).toFixed(6);
  const bpm=(Number((tr && tr.bpm)||120)).toFixed(6);
  const header=[
    hdrStart,
    `CLIP_START = ${start}`,
    `CLIP_DURATION = ${dur}`,
    `CLIP_BPM = ${bpm}`,
    hdrEnd,
    ""
  ].join("\n");

  let code=String(c.code||"");
  if(code.includes(hdrStart) && code.includes(hdrEnd)){
    const a=code.indexOf(hdrStart);
    const b=code.indexOf(hdrEnd)+hdrEnd.length;
    code = header + code.slice(b).replace(/^\n+/, "\n");
  } else {
    code = header + code;
  }
  c.code=code;
}

function placeAsset(asset){
  const tid=state.selectedTrackId || (state.tracks[0] && state.tracks[0].id);
  if(!tid){ addTrack(); return placeAsset(asset); }

  // Identify "same clip" by an asset key
  const assetKey = asset.type==="wav" ? ("wav:"+String(asset.wavId)) : ("py:"+String(asset.name));

  // If already placed on this track, put it immediately after the last instance
  let start = 0;
  let lastEnd = -1;
  for(const c0 of state.clips){
    if(c0.trackId!==tid) continue;
    if(c0.assetKey!==assetKey) continue;
    const end = (Number(c0.start)||0) + (Number(c0.dur)||0);
    if(end > lastEnd) lastEnd = end;
  }
  if(lastEnd >= 0) start = lastEnd;

  const c={
    id:uid(), trackId:tid, type:asset.type, name:asset.name,
    assetKey,
    start,
    dur: asset.type==="py" ? 1.0 : Math.min(1.0, asset.duration||1.0),
    code: asset.type==="py" ? (asset.code||"") : null,
    params: asset.params||{},
    transpose: 0,
    bpm: Number((getTrack(tid) && getTrack(tid).bpm)||120),
    t0:0
  };
  if(asset.type==="wav") c.wavAssetId = asset.wavId;
  if(c.type==="py") syncPyHeader(c);

  // snap start to snap/tempo grid
  const tr=getTrack(tid);
  const snap=snapVal();
  const step = snap>0 ? snap : (60/Math.max(1e-6, Number((tr && tr.bpm)||120)))/4;
  c.start = Math.round(c.start/step)*step;

  state.clips.push(c);
  state.selectedClipId=c.id;
  renderSelected();
  draw();
}

function secToBBT(tr, sec){
  const bpm=Math.max(1e-6, Number((tr && tr.bpm)||120));
  const spb=60/bpm;
  const beats=sec/spb;
  const bar=Math.floor(beats/4)+1;
  const beat=Math.floor(beats%4)+1;
  const div=Math.floor(((beats%1)*4));
  return `${bar}:${beat}:${div}`;
}
function bbtToSec(tr, bbt){
  const bpm=Math.max(1e-6, Number((tr && tr.bpm)||120));
  const spb=60/bpm;
  const m=String(bbt||"").trim().match(/^(\d+)\s*:\s*(\d+)\s*:\s*(\d+)$/);
  if(!m) return NaN;
  const bar=Math.max(1, Number(m[1]));
  const beat=Math.max(1, Number(m[2]));
  const div=Math.max(0, Number(m[3]));
  const beats=(bar-1)*4 + (beat-1) + (div/4);
  return beats*spb;
}

function renderSelected(){
  const box=$("selected");
  const c=getClip(state.selectedClipId);
  if(!c){ box.innerHTML="No clip selected."; return; }
  const tr=getTrack(c.trackId);
  const showBBT=(state.timeMode==="bbt");
  const startStr= showBBT ? secToBBT(tr,c.start) : (Number(c.start)||0).toFixed(3);
  const durStr  = showBBT ? secToBBT(tr,c.dur) : (Number(c.dur)||0).toFixed(3);

  box.innerHTML = `
    <div class="title">${c.name}</div>
    <div class="grid2">
      <label>Type</label><div style="color:#f5f5f6">${c.type.toUpperCase()}</div>
      <label>Track</label><div style="color:#f5f5f6">${tr?tr.name:"?"}</div>

      <label>Start</label>
      <div>
        <input id="selStartS" class="input" type="number" step="0.001" value="${showBBT?"":startStr}" style="${showBBT?"display:none":""}"/>
        <input id="selStartB" class="input" type="text" value="${showBBT?startStr:""}" style="${showBBT?"":"display:none"}"/>
      </div>

      <label>Dur</label>
      <div>
        <input id="selDurS" class="input" type="number" step="0.001" value="${showBBT?"":durStr}" style="${showBBT?"display:none":""}"/>
        <input id="selDurB" class="input" type="text" value="${showBBT?durStr:""}" style="${showBBT?"":"display:none"}"/>
      </div>

      <label>Trans</label>
      <div>
        <input id="selTrans" class="input" type="number" step="0.1" value="${Number(c.transpose||0).toFixed(2)}"/>
      </div>

      <label></label>
      <div class="row" style="justify-content:flex-end">
        <button id="btnApply" class="btn">Apply</button>
        <button id="btnRemove" class="btn">Remove</button>
      </div>
    </div>
  `;

  const btnApply=$("btnApply"), btnRemove=$("btnRemove");
  const sS=$("selStartS"), dS=$("selDurS"), sB=$("selStartB"), dB=$("selDurB"), tX=$("selTrans");

  function markDirty(){ btnApply.textContent="Apply*"; }
  [sS,dS,sB,dB,tX].forEach(el=>{
    if(!el) return;
    el.addEventListener("input", markDirty);
    el.addEventListener("change", markDirty);
    el.addEventListener("keydown", (e)=>{ if(e.key==="Enter") btnApply.click(); });
  });

  btnApply.onclick=()=>{
    let ns=c.start, nd=c.dur;
    if(showBBT){
      const a=bbtToSec(tr, sB.value);
      const b=bbtToSec(tr, dB.value);
      if(Number.isFinite(a)) ns=a;
      if(Number.isFinite(b)) nd=b;
    } else {
      const a=Number(sS.value), b=Number(dS.value);
      if(Number.isFinite(a)) ns=a;
      if(Number.isFinite(b)) nd=b;
    }
    ns=Math.max(0, ns);
    nd=Math.max(0.05, nd);

    const snap=snapVal();
    const step = snap>0 ? snap : (60/Math.max(1e-6, Number((tr && tr.bpm)||120)))/4;
    ns = Math.round(ns/step)*step;
    nd = Math.round(nd/step)*step;

    const nt = tX ? Number(tX.value) : Number(c.transpose||0);
    c.start=ns; c.dur=nd; c.transpose = Number.isFinite(nt) ? nt : 0;
    if(c.type==="py") syncPyHeader(c);
    btnApply.textContent="Apply";
    draw();
    renderSelected();
  };

  btnRemove.onclick=()=>{
    state.clips = state.clips.filter(x=>x.id!==c.id);
    state.selectedClipId=null;
    renderSelected();
    draw();
  };
}

// --- Python editor modal ---
function isEditorOpen(){
  const m=$("pyEditorModal");
  return !!(m && !m.classList.contains("hidden"));
}
function openPyEditor(clipId){
  const c=getClip(clipId);
  if(!c || c.type!=="py") return;
  state.editorClipId=clipId;
  $("pyEditorTitle").textContent = `Edit: ${c.name}`;
  $("pyEditor").value = c.code || "";
  $("pyEditorModal").classList.remove("hidden");
  $("pyEditorModal").setAttribute("aria-hidden","false");
  setTimeout(()=>$("pyEditor").focus(), 0);
}
function closePyEditor(){
  $("pyEditorModal").classList.add("hidden");
  $("pyEditorModal").setAttribute("aria-hidden","true");
  state.editorClipId=null;
}
function savePyEditor(){
  const c=getClip(state.editorClipId);
  if(!c || c.type!=="py") return closePyEditor();
  c.code = $("pyEditor").value;
  syncPyHeader(c);
  closePyEditor();
  renderSelected();
  draw();
}

// delegated + capture (reliable)
document.addEventListener("click", (e)=>{
  const t=e.target;
  if(!t) return;
  if(t.id==="btnPySave"){ e.preventDefault(); e.stopPropagation(); savePyEditor(); }
  if(t.id==="btnPyCancel"){ e.preventDefault(); e.stopPropagation(); closePyEditor(); }
}, true);

window.addEventListener("keydown", (e)=>{
  if(!isEditorOpen()) return;
  if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); closePyEditor(); return; }
  if((e.ctrlKey||e.metaKey) && (e.key==="Enter"||e.key==="Return")){ e.preventDefault(); e.stopPropagation(); savePyEditor(); return; }
}, true);

$("pyEditorModal").addEventListener("mousedown", (e)=>{
  if(e.target === $("pyEditorModal")) closePyEditor();
}, true);

// --- timeline drawing + interaction ---
const canvas=$("tl");
const ctx=canvas.getContext("2d");

function resize(){
  const dpr=Math.max(1, window.devicePixelRatio||1);
  const r=canvas.getBoundingClientRect();
  canvas.width=Math.floor(r.width*dpr);
  canvas.height=Math.floor(r.height*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);
  draw();
}
function pxPerSec(){ return 120*state.zoom; }
function totalDurationSec(){
  let m=0;
  for(const t of state.tracks) m=Math.max(m, Number(t.len)||0);
  for(const c of state.clips) m=Math.max(m, (Number(c.start)||0)+(Number(c.dur)||0));
  return Math.max(1, m);
}
function fmtSec(x){ return `${Number(x).toFixed(2)}s`; }

function draw(){
  const r=canvas.getBoundingClientRect();
  const W=r.width, H=r.height;
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle="#09090b"; ctx.fillRect(0,0,W,H);

  const laneH=70, laneGap=6, topPad=26, leftPad=56;
  const lanes=Math.max(1, state.tracks.length);

  const pps=pxPerSec();
  const startSec=state.scrollX/pps;
  const visibleSec=Math.max(0.001, (W-leftPad)/pps);
  const endSec=startSec+visibleSec;

  const showBBT=(state.timeMode==="bbt");
  const tr=getTrack(state.selectedTrackId) || state.tracks[0];
  const bpm=Number((tr && tr.bpm)||120);
  const spb=60/Math.max(1e-6,bpm);
  let grid = showBBT ? spb : 1.0;
  while(grid*pps < 40) grid*=2;
  while(grid*pps > 220) grid/=2;

  const first=Math.floor(startSec/grid)*grid;
  for(let t=first; t<=endSec+grid; t+=grid){
    const x=leftPad + (t-startSec)*pps;
    if(x<leftPad-1||x>W+1) continue;
    ctx.strokeStyle="#1f1f25";
    ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke();
    ctx.fillStyle="#a1a1aa";
    ctx.font="11px ui-sans-serif,system-ui";
    const label = showBBT ? secToBBT(tr,t) : t.toFixed(1);
    ctx.fillText(label, x+2, 14);
  }

  for(let i=0;i<lanes;i++){
    const y=topPad + i*(laneH+laneGap);
    ctx.fillStyle="#0f0f12"; ctx.fillRect(leftPad,y,W-leftPad,laneH);
    ctx.strokeStyle="#2a2a31"; ctx.strokeRect(leftPad,y,W-leftPad,laneH);
    ctx.fillStyle="#e4e4e7"; ctx.font="12px ui-sans-serif,system-ui";
    ctx.fillText(roman(i+1), 12, y+20);
  }

  for(const c of state.clips){
    const ti=state.tracks.findIndex(t=>t.id===c.trackId);
    const y=topPad + (ti<0?0:ti)*(laneH+laneGap);
    const x=leftPad + (c.start-startSec)*pps;
    const w=Math.max(6, c.dur*pps);
    if(x+w<leftPad||x>W) continue;
    const sel=(c.id===state.selectedClipId);
    ctx.fillStyle=sel?"#e5e7eb":"#17171d";
    ctx.fillRect(x,y+8,w,laneH-16);
    ctx.strokeStyle=sel?"#ffffff":"#2a2a31";
    ctx.strokeRect(x,y+8,w,laneH-16);
    ctx.fillStyle=sel?"#0a0a0b":"#f5f5f6";
    ctx.font="12px ui-sans-serif,system-ui";
    ctx.fillText(c.name, x+6, y+28);
    ctx.fillStyle=sel?"#0a0a0b":"#a1a1aa";
    ctx.font="11px ui-sans-serif,system-ui";
    ctx.fillText(`${c.type.toUpperCase()}  ${fmtSec(c.start)}  ${fmtSec(c.dur)}`, x+6, y+46);
  }
}

function hitTest(mx,my){
  const r=canvas.getBoundingClientRect();
  const W=r.width;
  const laneH=70, laneGap=6, topPad=26, leftPad=56;
  const pps=pxPerSec();
  const startSec=state.scrollX/pps;

  for(let i=0;i<state.tracks.length;i++){
    const y=topPad + i*(laneH+laneGap);
    if(my<y || my>y+laneH) continue;
    for(let k=state.clips.length-1;k>=0;k--){
      const c=state.clips[k];
      if(state.tracks[i].id!==c.trackId) continue;
      const x=leftPad + (c.start-startSec)*pps;
      const w=Math.max(6, c.dur*pps);
      if(mx>=x && mx<=x+w && my>=y+8 && my<=y+laneH-8){
        if(mx >= x+w-8) return {clipId:c.id, kind:"resize"};
        return {clipId:c.id, kind:"move"};
      }
    }
    return {trackId: state.tracks[i].id};
  }
  return null;
}

canvas.addEventListener("dblclick",(e)=>{
  const r=canvas.getBoundingClientRect();
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  const hit=hitTest(mx,my);
  if((hit && hit.clipId)){
    const c=getClip(hit.clipId);
    if((c && c.type)==="py") openPyEditor(c.id);
  }
});

canvas.addEventListener("mousedown",(e)=>{
  const r=canvas.getBoundingClientRect();
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  const hit=hitTest(mx,my);
  if(!hit) return;
  if(hit.clipId){
    state.selectedClipId=hit.clipId;
    renderSelected(); draw();
    const c=getClip(hit.clipId);
    state.dragging={clipId:c.id, kind:hit.kind, startX:mx, startStart:c.start, startDur:c.dur};
  } else if(hit.trackId){
    state.selectedTrackId=hit.trackId;
    renderTracks(); renderSelected(); draw();
  }
});

canvas.addEventListener("mousemove",(e)=>{
  if(!state.dragging) return;
  const r=canvas.getBoundingClientRect();
  const mx=e.clientX-r.left;
  const dx=mx - state.dragging.startX;
  const c=getClip(state.dragging.clipId);
  if(!c) return;
  const pps=pxPerSec();
  const dS=dx/pps;
  const tr=getTrack(c.trackId);
  const snap=snapVal();
  const step = snap>0 ? snap : (60/Math.max(1e-6, Number((tr && tr.bpm)||120)))/4;

  if(state.dragging.kind==="move"){
    let ns=Math.max(0, state.dragging.startStart + dS);
    if(!e.shiftKey) ns=Math.round(ns/step)*step;
    c.start=ns;
  } else {
    let nd=Math.max(0.05, state.dragging.startDur + dS);
    if(!e.shiftKey) nd=Math.round(nd/step)*step;
    c.dur=nd;
    if(c.type==="py") syncPyHeader(c);
  }
  draw();
});

window.addEventListener("mouseup", ()=>{ state.dragging=null; });

canvas.addEventListener("wheel",(e)=>{
  e.preventDefault();
  state.scrollX=Math.max(0, state.scrollX + e.deltaY);
  draw();
},{passive:false});

$("zoom").addEventListener("input", ()=>{ state.zoom=Number($("zoom").value); draw(); });
$("timeMode").addEventListener("change", ()=>{ state.timeMode=$("timeMode").value; renderSelected(); draw(); });

// --- project save/load ---
function _ab2b64(ab){
  const bytes = new Uint8Array(ab);
  let bin = "";
  const chunk = 0x8000;
  for(let i=0;i<bytes.length;i+=chunk){
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i+chunk));
  }
  return btoa(bin);
}
function _b642ab(b64){
  const bin = atob(b64);
  const len = bin.length;
  const bytes = new Uint8Array(len);
  for(let i=0;i<len;i++) bytes[i]=bin.charCodeAt(i);
  return bytes.buffer;
}

async function saveProject(){
  // Embed WAV assets as WAV PCM (16-bit) to keep projects portable.
  const proj = {
    version: 1,
    ui: {
      sr: Number($("sr").value),
      bits: Number($("bits").value),
      snap: Number($("snap").value||0),
      timeMode: state.timeMode,
      zoom: state.zoom,
      scrollX: state.scrollX,
      selectedTrackId: state.selectedTrackId
    },
    tracks: state.tracks.map(t=>({id:t.id, name:t.name, bpm:Number(t.bpm), len:Number(t.len), vol:Number(t.vol), pan:Number(t.pan)})),
    bin: [],
    clips: state.clips.map(c=>({
      id:c.id, trackId:c.trackId, type:c.type, name:c.name,
      start:Number(c.start), dur:Number(c.dur), transpose:Number(c.transpose||0),
      wavId:c.wavId||null, // reference into bin
      code: (c.type==="py" ? (c.code||"") : null),
      params: c.params||{}
    }))
  };

  for(const a of state.bin){
    if(a.type==="py"){
      proj.bin.push({type:"py", name:a.name, code:a.code||"", params:a.params||{}});
    }else if(a.type==="wav"){
      // encode current L/R to wav
      try{
        const stereo=[a.L, a.R];
        const wavAB = writeWavPCM(stereo, a.sr||proj.ui.sr, 16);
        proj.bin.push({type:"wav", name:a.name, wavId:a.wavId, wavB64:_ab2b64(wavAB)});
      }catch(e){
        console.warn("WAV encode failed for", a.name, e);
        proj.bin.push({type:"wav", name:a.name, wavId:a.wavId, wavB64:null});
      }
    }
  }

  const blob = new Blob([JSON.stringify(proj, null, 2)], {type:"application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "py_timeline_project.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 500);
  setStatus("Project saved.");
}

async function loadProjectFromFile(file){
  const txt = await file.text();
  const proj = JSON.parse(txt);

  // reset
  state.tracks = [];
  state.bin = [];
  state.clips = [];
  state.selectedClipId = null;
  state.editorClipId = null;

  // UI
  if(proj.ui){
    if($("sr")) $("sr").value = String(proj.ui.sr||$("sr").value);
    if($("bits")) $("bits").value = String(proj.ui.bits||$("bits").value);
    if($("snap")) $("snap").value = String(proj.ui.snap||0);
    state.timeMode = (proj.ui.timeMode==="bbt" ? "bbt" : "sec");
    if($("timeMode")) $("timeMode").value = state.timeMode;
    state.zoom = Number(proj.ui.zoom||1);
    if($("zoom")) $("zoom").value = String(state.zoom);
    state.scrollX = Number(proj.ui.scrollX||0);
    state.selectedTrackId = proj.ui.selectedTrackId || null;
  }

  // tracks
  if(Array.isArray(proj.tracks)){
    proj.tracks.forEach(t=>{
      state.tracks.push({
        id:String(t.id),
        name:String(t.name||"Track"),
        bpm:Number(t.bpm||120),
        len:Number(t.len||16),
        vol:Number(t.vol==null?1.0:t.vol),
        pan:Number(t.pan==null?0.0:t.pan)
      });
    });
  }
  if(!state.tracks.length) addTrack();
  if(!state.selectedTrackId) state.selectedTrackId = state.tracks[0].id;

  // bin (py first, wav async decode)
  setStatus("Loading project assets…");
  if(Array.isArray(proj.bin)){
    // py first
    proj.bin.filter(a=>a.type==="py").forEach(a=>{
      state.bin.push({type:"py", name:a.name||"script.py", code:a.code||"", params:a.params||{}});
    });

    // wav
    const wavItems = proj.bin.filter(a=>a.type==="wav");
    if(wavItems.length){
      const ac = ensureAudio();
      for(const a of wavItems){
        if(!a.wavB64){
          continue;
        }
        try{
          const ab = _b642ab(a.wavB64);
          const audio = await ac.decodeAudioData(ab.slice(0));
          const L = audio.getChannelData(0).slice();
          const R = (audio.numberOfChannels>1 ? audio.getChannelData(1).slice() : audio.getChannelData(0).slice());
          const wavId = a.wavId ? String(a.wavId) : uid();
          state.bin.push({type:"wav", name:a.name||"audio.wav", wavId, duration:audio.duration, sr:audio.sampleRate, L, R});
        }catch(e){
          console.warn("decode wav failed", a.name, e);
        }
      }
    }
  }

  // clips
  if(Array.isArray(proj.clips)){
    proj.clips.forEach(c=>{
      state.clips.push({
        id:String(c.id||uid()),
        trackId:String(c.trackId||state.tracks[0].id),
        type:String(c.type||"py"),
        name:String(c.name||""),
        start:Number(c.start||0),
        dur:Number(c.dur||1),
        transpose:Number(c.transpose||0),
        wavId: c.wavId ? String(c.wavId) : null,
        code: (c.type==="py" ? (c.code||"") : null),
        params: c.params||{}
      });
    });
  }

  renderTracks();
  renderBin();
  renderSelected();
  draw();
  setStatus("Project loaded.");
}


// project save/load
if($("btnSaveProj")) $("btnSaveProj").onclick = ()=>saveProject();
if($("btnLoadProj")) $("btnLoadProj").onclick = ()=>$("fileProj").click();
if($("fileProj")) $("fileProj").addEventListener("change", async (e)=>{
  const f = e.target.files[0]; if(!f) return;
  try{ await loadProjectFromFile(f); }
  catch(err){ console.error(err); setStatus("Load failed (see console)."); }
  e.target.value = "";
});

// --- loading assets ---
$("btnLoadPy").onclick=()=>$("filePy").click();
$("btnLoadWav").onclick=()=>$("fileWav").click();

$("filePy").addEventListener("change", async (e)=>{
  const f=e.target.files[0]; if(!f) return;
  const code=await f.text();
  state.bin.push({type:"py", name:f.name, code, params:{}});
  renderBin();
  e.target.value="";
});

$("fileWav").addEventListener("change", async (e)=>{
  const f=e.target.files[0]; if(!f) return;
  const ac=ensureAudio();
  const buf=await f.arrayBuffer();
  const audio=await ac.decodeAudioData(buf.slice(0));
  const L = audio.getChannelData(0).slice();
  const R = (audio.numberOfChannels>1 ? audio.getChannelData(1).slice() : audio.getChannelData(0).slice());
  const wavId=uid();
  state.bin.push({type:"wav", name:f.name, wavId, duration:audio.duration, sr:audio.sampleRate, L, R});
  renderBin();
  e.target.value="";
});

$("btnAddTrack").onclick=addTrack;

// --- worker + rendering ---
let worker=null;
let pendingPlay=false;
let pendingDownload=false;
let lastRender=null; // {L,R,sr,bits}

function ensureWorker(){
  if(worker) return worker;
  worker = new Worker("worker.js");
  worker.onmessage = (ev)=>{
    const m=ev.data;
    if(m.type==="inited"){ state.inited=true; setStatus("Pyodide ready."); }
    if(m.type==="err"){ console.error(m.err); setStatus("Error: "+String(m.err).slice(0,160)); pendingPlay=false; pendingDownload=false; }
    if(m.type==="renderDone"){
      const L=new Float32Array(m.L), R=new Float32Array(m.R);
      lastRender={L,R,sr:m.sr,bits:m.bits};
      if(pendingPlay){
        pendingPlay=false;
        playBuffer(L,R,m.sr);
        setStatus("Playing…");
      } else if(pendingDownload){
        pendingDownload=false;
        const blob=writeWavPCM([L,R], m.sr, m.bits);
        const a=document.createElement("a");
        a.href=URL.createObjectURL(blob);
        a.download="render.wav";
        a.click();
        setTimeout(()=>URL.revokeObjectURL(a.href), 5000);
        setStatus("Render complete.");
      } else {
        setStatus("Render complete.");
      }
    }
  };
  return worker;
}

async function init(){
  if(!$("useWorker").checked){ $("useWorker").checked=true; }
  setStatus("Initializing Pyodide…");
  ensureWorker().postMessage({type:"init"});
}

$("btnInit").onclick=init;

function playBuffer(L,R, SR){
  const ac=ensureAudio();
  const b=ac.createBuffer(2, L.length, SR);
  b.copyToChannel(L,0); b.copyToChannel(R,1);
  const src=ac.createBufferSource();
  src.buffer=b;
  src.connect(ac.destination);
  src.onended=()=>{ if(state.playSrc===src) state.playSrc=null; setStatus("Stopped."); };
  state.playSrc=src;
  src.start();
}

$("btnStop").onclick=()=>{
  pendingPlay=false;
  if(state.playSrc){ try{ state.playSrc.stop(); }catch{} state.playSrc=null; }
  setStatus("Stopped.");
};

function projectTotal(){
  let total=0;
  for(const t of state.tracks) total=Math.max(total, Number(t.len)||0);
  for(const c of state.clips) total=Math.max(total, (Number(c.start)||0)+(Number(c.dur)||0));
  return Math.max(0.5, total);
}

async function requestRender({play=false, download=false}={}){
  if(!state.inited) await init();
  const SR=sr(), B=bits();
  const total=projectTotal();

  const tracks = state.tracks.map(t=>({id:t.id, vol:Number(t.vol||1), pan:Number(t.pan||0)}));
  const clips = state.clips.map(c=>({
    id:c.id, trackId:c.trackId, type:c.type, start:Number(c.start)||0, dur:Number(c.dur)||0.01,
    transpose: Number(c.transpose)||0,
    bpm: Number((getTrack(c.trackId) && getTrack(c.trackId).bpm)||120),
    code: c.type==="py" ? (c.code||"") : null,
    params: c.params||{},
    t0:Number(c.t0)||0
  }));

  // Provide wav PCM per placed wav clip id
  const wavClips=[];
  for(const c of state.clips){
    if(c.type!=="wav") continue;
    const a = state.bin.find(x=>x.type==="wav" && x.wavId===c.wavAssetId);
    if(a){
      wavClips.push({id:c.id, L:a.L, R:a.R, sr:a.sr});
    }
  }

  pendingPlay=!!play;
  pendingDownload=!!download;
  setStatus(play ? "Rendering for playback…" : "Rendering…");

  // transfer buffers for wav clips
  const transfers=[];
  for(const w of wavClips){
    if(w.L && w.L.buffer) transfers.push(w.L.buffer);
    if(w.R && w.R.buffer) transfers.push(w.R.buffer);
  }
  ensureWorker().postMessage({type:"renderAll", sr:SR, bits:B, totalDur:total, tracks, clips, wavClips}, transfers);
}

$("btnPlay").onclick=async ()=>{
  const ac=ensureAudio();
  if(ac.state==="suspended"){ try{ await ac.resume(); }catch{} }
  await requestRender({play:true}); // always re-render
};

$("btnRender").onclick=()=>requestRender({download:true});

// boot
addTrack();
renderBin();
renderSelected();
window.addEventListener("resize", resize);
resize();function removeAsset(idx){
  state.bin.splice(idx,1);
  renderBin();
}


