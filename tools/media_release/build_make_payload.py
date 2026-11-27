#!/usr/bin/env python3
"""Build Make 7095932 youtube_release input from approved exact-asset evidence.
No credentials, no network, no upload. Technical QA alone never grants release.
"""
import argparse, hashlib, json, pathlib, sys
CHANNELS = {"health":"UCmIXHZDJ5iI7Vz_pfHnsCZQ","interest":"UCvd3hzu8DxvL8n1YDqpCuRg"}
REQUIRED = ("content_sources", "rights", "intelligibility", "visual_captions",
            "native_identity", "native_inventory", "dedup", "day_slot", "single_sender", "authorization")
def build(asset, qa, evidence, transport):
    p = pathlib.Path(asset)
    with p.open("rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    c = CHANNELS.get(evidence.get("channel"))
    if not c or qa.get("channel") != c or evidence.get("channel_id") != c:
        raise ValueError("channel mismatch")
    if qa.get("kind") != "candidate" or not qa.get("technical_pass") or qa.get("sha256") != sha or qa.get("bytes") != p.stat().st_size:
        raise ValueError("technical QA absent, smoke, or changed bytes")
    if evidence.get("sha256") != sha:
        raise ValueError("evidence not bound to asset")
    for key in REQUIRED:
        record = evidence.get("checks", {}).get(key, {})
        if record.get("status") != "PASS" or not record.get("reference"):
            raise ValueError("missing verified evidence: "+key)
    for key in ("title","description","content_id","upload_action_key"):
        if not isinstance(evidence.get(key),str) or not evidence[key].strip():
            raise ValueError("missing "+key)
    result = dict(operation="youtube_release", channel_id=c, expected_channel_id=c,
        title=evidence["title"], description=evidence["description"], content_id=evidence["content_id"],
        upload_action_key=evidence["upload_action_key"], qa_state="cleared", rights_state="cleared",
        dedup_state="cleared", sender_state="single_sender_confirmed", release_status="QA_READY",
        upload_authorized=True, execute_publish=True, stage_private=False, dedup_cleared=True,
        day_slot_cleared=True, native_inventory_cleared=True, asset_sha256=sha,
        expected_sha256=sha, expected_size=p.stat().st_size, file_name=p.name,
        contains_synthetic_media=bool(evidence.get("contains_synthetic_media",False)))
    if evidence["channel"]=="interest":
        if not transport.get("drive_file_id"): raise ValueError("missing Drive file ID")
        result["drive_file_id"]=transport["drive_file_id"]
    else:
        if not str(transport.get("source_url","")).startswith("https://"): raise ValueError("missing authorized HTTPS source")
        result["source_url"]=transport["source_url"]
    return result
def main():
    parser=argparse.ArgumentParser()
    for name in ("asset","qa","evidence","transport"): parser.add_argument(name)
    args=parser.parse_args()
    try:
        payload=build(args.asset,*[json.loads(pathlib.Path(getattr(args,n)).read_text()) for n in ("qa","evidence","transport")])
    except (ValueError, KeyError, OSError, TypeError) as e:
        print(json.dumps({"release_status":"HOLD","reason":str(e)}),file=sys.stderr)
        return 1
    print(json.dumps(payload,ensure_ascii=False))
    return 0
if __name__=="__main__": sys.exit(main())
