"""Conservative automated Arabic speech QA. ASR is not human listening.
Bind all results to exact media; do not grant release from this report alone."""
import argparse, hashlib, json, pathlib, re, unicodedata, math

def norm(s):
    s=unicodedata.normalize("NFKC",s)
    s="".join(c for c in s if not unicodedata.combining(c))
    s=s.replace("ـ","").translate(str.maketrans("أإآٱى","ااااي"))
    return re.findall(r"[^\W_]+",s.lower(),flags=re.UNICODE)

def distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1): nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]

def evaluate(reference, observed, critical, confidence):
    a,b=norm(reference),norm(observed)
    wer=distance(a,b)/max(1,len(a))
    phrases=[p for p in critical if not (" "+" ".join(norm(p))+" ") in (" "+" ".join(b)+" ")]
    scores=list(confidence)
    ok=bool(a and b and critical and scores) and all(isinstance(x,(int,float)) and math.isfinite(x) and 0<=x<=1 for x in scores)
    mean=sum(scores)/len(scores) if ok else None
    low=sum(x<0.5 for x in scores)/len(scores) if ok else None
    # Conservative initial engineering thresholds, not a validated pronunciation metric.
    passed=bool(ok and wer<=0.08 and not phrases and mean>=0.80 and low<=0.05)
    return dict(status="PASS_AUTOMATED_INTELLIGIBILITY" if passed else "HOLD",
                wer=round(wer,5),missing_critical_phrases=phrases,mean_word_probability=mean,
                low_confidence_fraction=low,reference_words=len(a),observed_words=len(b),
                human_listening=False,prosody_validated=False,release_authorized=False)

def transcribe(model, file, language):
    segments,info=model.transcribe(str(file),language=language,beam_size=5,
        word_timestamps=True,condition_on_previous_text=False,vad_filter=True)
    segments=list(segments)
    return " ".join(s.text.strip() for s in segments),[w.probability for s in segments for w in (s.words or [])]

def main():
    p=argparse.ArgumentParser();p.add_argument("--audio-dir",required=True);p.add_argument("--references",required=True)
    p.add_argument("--out",required=True);p.add_argument("--model-dir",required=True)
    a=p.parse_args()
    from faster_whisper import WhisperModel
    model=WhisperModel(a.model_dir,device="cpu",compute_type="int8",cpu_threads=2)
    refs=json.loads(pathlib.Path(a.references).read_text())
    reports=[]
    for name,r in refs.items():
        if pathlib.Path(name).name!=name: raise ValueError("invalid asset name")
        file=pathlib.Path(a.audio_dir)/(name+".wav")
        try:
            with file.open("rb") as f: sha=hashlib.file_digest(f,"sha256").hexdigest()
            observed,scores=transcribe(model,file,r.get("language","ar"))
            report=evaluate(r["text"],observed,r["critical"],scores)
            report.update(asset=file.name,sha256=sha,transcript=observed,model="Systran/faster-whisper-small@536b066")
        except Exception as e:
            report=dict(asset=file.name,status="HOLD",error=type(e).__name__,release_authorized=False)
        reports.append(report)
    pathlib.Path(a.out).write_text(json.dumps(reports,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps([{k:v for k,v in r.items() if k!="transcript"} for r in reports],ensure_ascii=False))

if __name__=="__main__": main()
