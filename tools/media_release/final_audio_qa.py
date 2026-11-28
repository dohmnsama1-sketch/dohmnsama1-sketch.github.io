"""Prepare exact final MP4 speech evidence on a worker with installed CPU ASR.
No credentials, network, upload or implicit approval."""
import argparse, hashlib, json, pathlib, subprocess, tempfile
from speech_qa import evaluate, transcribe

def main():
    p=argparse.ArgumentParser()
    p.add_argument("asset");p.add_argument("reference");p.add_argument("--model-dir",required=True)
    p.add_argument("--out",required=True);a=p.parse_args()
    asset=pathlib.Path(a.asset);ref=json.loads(pathlib.Path(a.reference).read_text())
    with asset.open("rb") as f: sha=hashlib.file_digest(f,"sha256").hexdigest()
    out=dict(sha256=sha,asset=asset.name,bytes=asset.stat().st_size,status="HOLD",release_authorized=False)
    try:
        from faster_whisper import WhisperModel
        with tempfile.TemporaryDirectory() as tmp:
            wav=str(pathlib.Path(tmp)/"final_audio.wav")
            subprocess.run(["ffmpeg","-nostdin","-v","error","-xerror","-i",str(asset),"-map","0:a:0","-ac","1","-ar","16000","-c:a","pcm_s16le",wav],check=True,timeout=180)
            model=WhisperModel(a.model_dir,device="cpu",compute_type="int8",cpu_threads=2)
            observed,scores=transcribe(model,wav,ref.get("language","ar"))
            out.update(evaluate(ref["text"],observed,ref["critical"],scores))
            out["transcript"]=observed
            out["model"]="Systran/faster-whisper-small@536b066 (configured local model directory; provenance must be verified by worker)"
            out["classification"]="EXACT_FINAL_MEDIA_ASR_NOT_HUMAN_LISTENING"
    except Exception as e:
        out.update(status="HOLD",error=type(e).__name__)
    pathlib.Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(out["status"])
    return 0 if out["status"]=="PASS_AUTOMATED_INTELLIGIBILITY" else 1
if __name__=="__main__": raise SystemExit(main())
