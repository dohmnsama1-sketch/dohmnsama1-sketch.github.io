"""Validate native YouTube readback from the existing Make youtube_verify route.
Read-only. Never submits or retries an upload. A missing result is UNKNOWN, not PUBLIC.
"""
import re

def verify(response, video_id, channel_id):
    if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Invalid native video ID")
    if not isinstance(channel_id, str) or not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", channel_id):
        raise ValueError("Invalid channel ID")
    out = response.get("outputs") or {}
    result = {"state": "UNKNOWN", "video_id": video_id,
              "execution_id": response.get("executionId")}
    if response.get("status") != "success" or out.get("status") != 200:
        return result
    body = out.get("result") or {}
    items = body.get("items", []) if isinstance(body, dict) else []
    if len(items) != 1 or out.get("asset_id") != video_id:
        return result
    v = items[0]
    if v.get("id") != video_id or v.get("snippet", {}).get("channelId") != channel_id:
        return result
    status = v.get("status", {})
    processing = v.get("processingDetails", {}).get("processingStatus")
    result.update(state="PENDING", channel_id=channel_id,
                  privacy=status.get("privacyStatus"), upload=status.get("uploadStatus"),
                  processing=processing)
    if status.get("privacyStatus") == "public" and status.get("uploadStatus") == "processed" and processing == "succeeded":
        result.update(state="PUBLIC_VERIFIED", url="https://www.youtube.com/watch?v=" + video_id)
    elif status.get("uploadStatus") in ("failed", "rejected", "deleted") or processing in ("failed", "terminated"):
        result["state"] = "FAILED_RECONCILE_NO_REUPLOAD"
    return result
