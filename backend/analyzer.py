import json
import time
import base64
import io
from typing import List, Dict, Optional
from PIL import Image
from google import genai
from google.genai import types
from models import (
    AnalysisResult, SceneAssessment, DetectedObject,
    UncertainMatch, ChangeStatus, Confidence, BoundingBox
)

# Use Gemini Flash — free tier via Google AI Studio
MODEL = "gemini-3.6-flash"


def _build_image_parts(images: List[bytes], label: str) -> list:
    """Build content parts: a text label followed by inline image data."""
    parts = [types.Part.from_text(text=label)]
    for img_bytes in images:
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
    return parts


PASS1_PROMPT = """Analyze the provided BEFORE and AFTER images of the same room or desk area.

Return a JSON object with exactly two keys:

1. "scene" — an object:
   - "lighting_change": describe any lighting, exposure, or white-balance difference.
   - "viewpoint_change": describe any camera angle or framing difference.
   - "coverage_comparison": which parts of the scene are visible in both sets and which are not.

2. "inventory" — a list of every distinct physical object visible in ANY image (before or after). For each:
   {
     "name": "human-readable name",
     "visible_in_before": true/false,
     "visible_in_after": true/false,
     "bbox_before": {"x_pct": ..., "y_pct": ..., "w_pct": ..., "h_pct": ...} or null,
     "bbox_after":  {"x_pct": ..., "y_pct": ..., "w_pct": ..., "h_pct": ...} or null
   }
   Bounding boxes are percentages of image width/height (0-100). Set to null if not visible.
"""

PASS2_PROMPT_TEMPLATE = """Using the inventory from the first pass:
{inventory_json}

And the scene assessment:
{scene_json}

Determine the status of every inventoried object.

CRITICAL RULES:
1. NOT VERIFIABLE, not removed: If an object from BEFORE is NOT visible in AFTER, but its original location is also NOT visible in AFTER (different framing, cropped, occluded), classify as "not_verifiable". Do NOT say "removed".
2. REMOVED requires proof: Only classify as "removed" if the exact area where it was IS clearly visible in AFTER and the object is absent.
3. Lighting is NOT physical change: Brightness, color temperature, white balance, exposure differences must NOT be reported as physical changes.
4. MOVED: Object appears in both BEFORE and AFTER at a significantly different position.
5. ADDED: Object in AFTER but not in BEFORE, and its location in AFTER was visible and empty in BEFORE.
6. UNCHANGED: Same object, same approximate position.

Return JSON with exactly three keys:

"confirmed_changes": [
  {{
    "name": "object name",
    "bbox_before": {{"x_pct": 0, "y_pct": 0, "w_pct": 0, "h_pct": 0}} or null,
    "bbox_after":  {{"x_pct": 0, "y_pct": 0, "w_pct": 0, "h_pct": 0}} or null,
    "status": "moved" | "added" | "removed",
    "confidence": "high" | "medium" | "low",
    "evidence_note": "Why this status was chosen."
  }}
],
"unchanged_objects": [
  {{
    "name": "object name",
    "bbox_before": ...,
    "bbox_after": ...,
    "status": "unchanged",
    "confidence": "high" | "medium" | "low",
    "evidence_note": "..."
  }}
],
"uncertain_matches": [
  {{
    "object_name": "object name",
    "reason": "why uncertain",
    "suggested_action": "what extra photo or angle would help",
    "bbox_before": ... or null
  }}
]

Objects classified as "not_verifiable" go into "uncertain_matches".
"""


def analyze_images(
    before_images: List[bytes],
    after_images: List[bytes],
    api_key: str,
) -> AnalysisResult:
    """Run two-pass Gemini Flash analysis on before/after image sets."""
    start_time = time.time()
    client = genai.Client(api_key=api_key)
    warnings: list[str] = []
    token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # Build image parts
    before_parts = _build_image_parts(before_images, "BEFORE images:")
    after_parts = _build_image_parts(after_images, "AFTER images:")

    json_config = types.GenerateContentConfig(
        response_mime_type="application/json",
    )

    # ── PASS 1: Scene Assessment & Inventory ─────────────────────────────
    pass1_contents = [
        types.Part.from_text(text=PASS1_PROMPT),
        *before_parts,
        *after_parts,
    ]

    try:
        pass1_resp = client.models.generate_content(
            model=MODEL,
            contents=pass1_contents,
            config=json_config,
        )
        _accumulate_usage(token_usage, pass1_resp)
        raw_pass1 = json.loads(pass1_resp.text)
        if isinstance(raw_pass1, list):
            pass1_data = raw_pass1[0] if raw_pass1 else {}
        elif isinstance(raw_pass1, dict):
            pass1_data = raw_pass1
        else:
            pass1_data = {}
    except Exception as e:
        warnings.append(f"Pass 1 error: {e}")
        pass1_data = {"scene": {}, "inventory": []}

    # ── PASS 2: Change Detection ─────────────────────────────────────────
    scene_json = json.dumps(pass1_data.get("scene", {}), indent=2)
    inventory_json = json.dumps(pass1_data.get("inventory", []), indent=2)

    pass2_prompt = PASS2_PROMPT_TEMPLATE.format(
        inventory_json=inventory_json,
        scene_json=scene_json,
    )

    pass2_contents = [
        types.Part.from_text(text=pass2_prompt),
        *before_parts,
        *after_parts,
    ]

    try:
        pass2_resp = client.models.generate_content(
            model=MODEL,
            contents=pass2_contents,
            config=json_config,
        )
        _accumulate_usage(token_usage, pass2_resp)
        raw_pass2 = json.loads(pass2_resp.text)
        if isinstance(raw_pass2, list):
            pass2_data = raw_pass2[0] if raw_pass2 else {}
        elif isinstance(raw_pass2, dict):
            pass2_data = raw_pass2
        else:
            pass2_data = {}
    except Exception as e:
        warnings.append(f"Pass 2 error: {e}")
        pass2_data = {
            "confirmed_changes": [],
            "unchanged_objects": [],
            "uncertain_matches": [],
        }

    processing_time = time.time() - start_time

    # Cost: Gemini Flash free tier = $0, paid = $0.075/1M input, $0.30/1M output
    cost_usd = (
        token_usage["prompt_tokens"] / 1_000_000 * 0.075
        + token_usage["completion_tokens"] / 1_000_000 * 0.30
    )

    # Parse scene
    scene_raw = pass1_data.get("scene", {})
    scene = SceneAssessment(
        lighting_change=scene_raw.get("lighting_change", "Unknown"),
        viewpoint_change=scene_raw.get("viewpoint_change", "Unknown"),
        coverage_comparison=scene_raw.get("coverage_comparison", "Unknown"),
    )

    return AnalysisResult(
        scene=scene,
        confirmed_changes=_parse_detected_objects(
            pass2_data.get("confirmed_changes", [])
        ),
        unchanged_objects=_parse_detected_objects(
            pass2_data.get("unchanged_objects", [])
        ),
        uncertain_matches=_parse_uncertain(
            pass2_data.get("uncertain_matches", [])
        ),
        processing_time_seconds=round(processing_time, 2),
        token_usage=token_usage,
        estimated_cost_usd=round(cost_usd, 6),
        warnings=warnings,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _accumulate_usage(totals: dict, response) -> None:
    """Extract token counts from Gemini response metadata."""
    try:
        meta = response.usage_metadata
        if meta:
            totals["prompt_tokens"] += getattr(meta, "prompt_token_count", 0) or 0
            totals["completion_tokens"] += getattr(meta, "candidates_token_count", 0) or 0
            totals["total_tokens"] += getattr(meta, "total_token_count", 0) or 0
    except Exception:
        pass


def _parse_bbox(raw) -> Optional[BoundingBox]:
    if not raw or not isinstance(raw, dict):
        return None
    try:
        return BoundingBox(
            x_pct=float(raw.get("x_pct", 0)),
            y_pct=float(raw.get("y_pct", 0)),
            w_pct=float(raw.get("w_pct", 0)),
            h_pct=float(raw.get("h_pct", 0)),
        )
    except (TypeError, ValueError):
        return None


def _parse_detected_objects(items: list) -> list[DetectedObject]:
    results = []
    if not isinstance(items, list):
        return results
    for obj in items:
        if not isinstance(obj, dict):
            continue
        try:
            results.append(DetectedObject(
                name=obj.get("name", "Unknown"),
                bbox_before=_parse_bbox(obj.get("bbox_before")),
                bbox_after=_parse_bbox(obj.get("bbox_after")),
                status=ChangeStatus(obj.get("status", "unchanged")),
                confidence=Confidence(obj.get("confidence", "medium")),
                evidence_note=obj.get("evidence_note", ""),
            ))
        except (ValueError, KeyError):
            continue
    return results


def _parse_uncertain(items: list) -> list[UncertainMatch]:
    results = []
    if not isinstance(items, list):
        return results
    for obj in items:
        if not isinstance(obj, dict):
            continue
        try:
            results.append(UncertainMatch(
                object_name=obj.get("object_name", obj.get("name", "Unknown")),
                reason=obj.get("reason", ""),
                suggested_action=obj.get("suggested_action", ""),
                bbox_before=_parse_bbox(obj.get("bbox_before")),
            ))
        except (ValueError, KeyError):
            continue
    return results


def crop_evidence_region(image_bytes: bytes, bbox: BoundingBox) -> bytes:
    """Crop a region from an image using percentage-based bounding box."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size

        left = max(0, int((bbox.x_pct / 100) * width))
        top = max(0, int((bbox.y_pct / 100) * height))
        right = min(width, left + int((bbox.w_pct / 100) * width))
        bottom = min(height, top + int((bbox.h_pct / 100) * height))

        if right - left < 10 or bottom - top < 10:
            return b""

        cropped = img.crop((left, top, right, bottom))

        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return b""


def create_evidence_pairs(
    before_images: List[bytes],
    after_images: List[bytes],
    result: AnalysisResult,
) -> Dict[str, Dict[str, str]]:
    """Create cropped evidence pairs for every detected change."""
    evidence: Dict[str, Dict[str, str]] = {}

    b_img = before_images[0] if before_images else None
    a_img = after_images[0] if after_images else None

    for obj in result.confirmed_changes:
        crops: Dict[str, str] = {}
        if obj.bbox_before and b_img:
            crop_b = crop_evidence_region(b_img, obj.bbox_before)
            if crop_b:
                crops["before"] = base64.b64encode(crop_b).decode("utf-8")
        if obj.bbox_after and a_img:
            crop_a = crop_evidence_region(a_img, obj.bbox_after)
            if crop_a:
                crops["after"] = base64.b64encode(crop_a).decode("utf-8")
        if crops:
            evidence[obj.name] = crops

    for match in result.uncertain_matches:
        if match.bbox_before and b_img:
            crop_b = crop_evidence_region(b_img, match.bbox_before)
            if crop_b:
                evidence[match.object_name] = {
                    "before": base64.b64encode(crop_b).decode("utf-8"),
                }

    return evidence
