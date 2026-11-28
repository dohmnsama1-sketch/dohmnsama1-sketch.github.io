"""Local offline acoustic screening; not ASR or proof of human listening.
Uses exact final media and optional two independently sourced SRT files."""
import argparse, hashlib, json, pathlib, re, subprocess
import numpy as np
import parselmouth

def stamp(s):
    a,b,c=s.replace(',','.').split(':')
    return int(a)*3600+int(b)*60+float(c)

def cues(p):
    return [(stamp(a),stamp(b),t.strip()) for a,b,t in re.findall(r'\d+\s*\n([\d:,.]+) --> ([\d:,.]+)\s*\n(.*?)(?=\n\s*\n|\Z)',pathlib.Path(p).read_text().strip(),re.S)]

def assess(p, observed=None, expected=None):
    p=pathlib.Path(p)
    raw=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(p),'-map','0:a:0','-ac','1','-ar','16000','-f','f32le','-'],timeout=90)
    a=np.frombuffer(raw,dtype=np.float32).astype(float)
    if not len(a) or not np.all(np.isfinite(a)): raise ValueError('invalid audio')
    pitch=parselmouth.Sound(a,sampling_frequency=16000).to_pitch(time_step=.02,pitch_floor=70,pitch_ceiling=500).selected_array['frequency']
    voiced=pitch[pitch>0]
    rms=20*np.log10(max(np.sqrt(np.mean(a*a)),1e-12))
    peak=20*np.log10(max(np.max(np.abs(a)),1e-12))
    frames=a[:len(a)//320*320].reshape(-1,320)
    quiet=np.sqrt(np.mean(frames*frames,axis=1))<10**(-45/20)
    longest=max((len(x) for x in ''.join('1' if q else '0' for q in quiet).split('0')),default=0)*.02
    f0=[float(x) for x in np.percentile(voiced,[10,50,90])] if len(voiced) else []
    spread=12*np.log2(f0[2]/f0[0]) if f0 and f0[0] else 0
    flags=[]
    if peak>=0: flags.append('peak_at_or_over_full_scale')
    if rms < -35 or rms > -8: flags.append('unusual_RMS')
    if longest>1.5: flags.append('extended_quiet')
    if len(voiced)<20 or spread<1.5: flags.append('low_detected_pitch_variation')
    with p.open('rb') as f: sha=hashlib.file_digest(f,'sha256').hexdigest()
    r=dict(asset=p.name,sha256=sha,rms_dbfs=round(float(rms),2),peak_dbfs=round(float(peak),2),
        longest_quiet_s=round(longest,3),pitch_range_semitones=round(float(spread),2),pitch_10_50_90_hz=f0,
        acoustic_flags=flags,acoustic_screen='REVIEW' if flags else 'NO_HEURISTIC_FLAGS',
        human_listening=False,new_asr_inference=False,release_authorized=False,
        thresholds='Engineering heuristics, not validated pronunciation thresholds')
    if observed and expected:
        x,y=cues(observed),cues(expected)
        diffs=[[round(b[0]-a[0],3),round(b[1]-a[1],3)] for a,b in zip(x,y)]
        r['caption_timing_comparison']=dict(observed_cues=len(x),expected_cues=len(y),
            boundary_differences_seconds=diffs,status='REVIEW' if not x or len(x)!=len(y) or any(max(abs(a),abs(b))>.75 for a,b in diffs) else 'NO_LARGE_BOUNDARY_DIFFERENCE')
    return r

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('asset');ap.add_argument('--asr-srt');ap.add_argument('--expected-srt');ap.add_argument('--out',required=True)
    a=ap.parse_args();r=assess(a.asset,a.asr_srt,a.expected_srt);pathlib.Path(a.out).write_text(json.dumps(r,ensure_ascii=False,indent=2))
