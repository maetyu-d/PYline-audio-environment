// WAV writer for PCM 8/16/24/32-bit from float32 stereo [-1,1]
function writeWavPCM(stereo, sampleRate, bits){
  const L=stereo[0], R=stereo[1];
  const n=L.length;
  const ch=2;
  const bps = bits===24 ? 3 : (bits/8);
  const blockAlign = ch*bps;
  const byteRate = sampleRate*blockAlign;
  const dataSize = n*blockAlign;
  const buf = new ArrayBuffer(44+dataSize);
  const dv = new DataView(buf);
  let o=0;
  const u32=v=>{dv.setUint32(o,v,true); o+=4;};
  const u16=v=>{dv.setUint16(o,v,true); o+=2;};
  const str=s=>{for(let i=0;i<s.length;i++) dv.setUint8(o++, s.charCodeAt(i));};
  const clamp=x=>Math.max(-1, Math.min(1, x));

  str("RIFF"); u32(36+dataSize); str("WAVE");
  str("fmt "); u32(16); u16(1); u16(ch); u32(sampleRate);
  u32(byteRate); u16(blockAlign); u16(bits);
  str("data"); u32(dataSize);

  if(bits===8){
    for(let i=0;i<n;i++){
      dv.setUint8(o++, Math.round((clamp(L[i])*0.5+0.5)*255));
      dv.setUint8(o++, Math.round((clamp(R[i])*0.5+0.5)*255));
    }
  } else if(bits===16){
    for(let i=0;i<n;i++){
      dv.setInt16(o, Math.round(clamp(L[i])*32767), true); o+=2;
      dv.setInt16(o, Math.round(clamp(R[i])*32767), true); o+=2;
    }
  } else if(bits===24){
    const max=8388607;
    for(let i=0;i<n;i++){
      let a=Math.round(clamp(L[i])*max);
      dv.setUint8(o++, a & 255); dv.setUint8(o++, (a>>8)&255); dv.setUint8(o++, (a>>16)&255);
      a=Math.round(clamp(R[i])*max);
      dv.setUint8(o++, a & 255); dv.setUint8(o++, (a>>8)&255); dv.setUint8(o++, (a>>16)&255);
    }
  } else {
    const max=2147483647;
    for(let i=0;i<n;i++){
      dv.setInt32(o, Math.round(clamp(L[i])*max), true); o+=4;
      dv.setInt32(o, Math.round(clamp(R[i])*max), true); o+=4;
    }
  }
  return new Blob([buf], {type:"audio/wav"});
}
