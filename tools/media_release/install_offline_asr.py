#!/usr/bin/env python3
"""Offline Linux x86_64 CPython 3.13 install. Run in an approved persistent workspace.
Never downloads dependencies, uses an explicit wheelhouse and model directory."""
import argparse, hashlib, json, os, pathlib, platform, subprocess, sys, venv
def digest(p):
    with p.open("rb") as f: return hashlib.file_digest(f,"sha256").hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("bundle",type=pathlib.Path);ap.add_argument("destination",type=pathlib.Path)
    a=ap.parse_args(); root=a.bundle.resolve(); dst=a.destination.resolve()
    if not sys.version_info[:2]==(3,13) or platform.system()!="Linux" or platform.machine()!="x86_64":
        raise SystemExit("HOLD: bundle targets Linux x86_64 CPython 3.13")
    manifest=json.loads((root/"SHA256SUMS.json").read_text())
    if not isinstance(manifest,dict) or not manifest: raise SystemExit("HOLD: missing manifest")
    for name,sha in manifest.items():
        p=(root/name).resolve()
        if not p.is_relative_to(root) or not p.is_file() or digest(p)!=sha: raise SystemExit("HOLD: invalid file "+name)
    required={"model/model.bin","model/config.json","model/tokenizer.json","model/vocabulary.txt","requirements.lock"}
    if not required.issubset(manifest): raise SystemExit("HOLD: incomplete model")
    if any(str(p.relative_to(root)) not in manifest for p in root.rglob("*") if p.is_file() and p.name!="SHA256SUMS.json"):
        raise SystemExit("HOLD: unmanifested files")
    if dst.exists(): raise SystemExit("HOLD: use a new versioned destination, never overwrite known-good")
    env=dict(os.environ,HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",PIP_NO_INDEX="1")
    venv.EnvBuilder(with_pip=True).create(dst)
    python=dst/"bin/python"
    subprocess.run([str(python),"-m","pip","install","--no-index","--only-binary=:all:","--find-links",str(root/"wheels"),"-r",str(root/"requirements.lock")],env=env,check=True)
    subprocess.run([str(python),"-m","pip","check"],env=env,check=True)
    subprocess.run([str(python),"-c","import sys; from faster_whisper import WhisperModel; WhisperModel(sys.argv[1],device='cpu',compute_type='int8',local_files_only=True); print('LOCAL_MODEL_LOAD_OK')",str(root/"model")],env=env,check=True)
    print("Runtime installed; actual final-media speech QA is still required.")
if __name__=="__main__": main()
