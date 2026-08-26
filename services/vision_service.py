import os
import logging
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)

def extract_image_metadata(image_path):
    """
    Extracts image dimensions, color mode, format, and EXIF metadata.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    with Image.open(image_path) as img:
        width, height = img.size
        img_format = img.format
        mode = img.mode
        
        exif_data = {}
        raw_exif = img.getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                # Only store string/numeric serializable values
                if isinstance(value, (str, int, float)):
                    exif_data[tag_name] = value

    return {
        "filename": os.path.basename(image_path),
        "width": width,
        "height": height,
        "aspect_ratio": f"{width}:{height}",
        "format": img_format,
        "mode": mode,
        "has_exif": len(exif_data) > 0,
        "exif": exif_data
    }


def perform_image_forensics(image_path):
    """
    Performs algorithmic image forensics and probabilistic AI-generation / manipulation assessment.
    Returns:
    {
        "classification": "Likely Authentic" | "Likely AI-Generated" | "Likely Manipulated" | "Inconclusive",
        "ai_probability": int (0-100),
        "manipulation_probability": int (0-100),
        "confidence": int (0-100),
        "signals": list of dicts,
        "metadata_forensics": dict,
        "limitations_disclaimer": str
    }
    """
    meta = extract_image_metadata(image_path)
    exif = meta.get("exif", {})
    
    signals = []
    ai_score = 30  # Baseline
    manip_score = 25
    confidence = 70

    # 1. EXIF Metadata Inspection
    software = str(exif.get("Software", "")).lower()
    artist = str(exif.get("Artist", "")).lower()
    description = str(exif.get("ImageDescription", "")).lower()
    make = str(exif.get("Make", ""))
    model = str(exif.get("Model", ""))

    ai_keywords = ["midjourney", "stable diffusion", "dall-e", "dalle", "bing", "flux", "novelai", "civitai", "adobe firefly", "runway"]
    manip_keywords = ["photoshop", "gimp", "canva", "lightroom", "picsart", "snapseed"]

    found_ai_tag = any(k in software or k in description or k in artist for k in ai_keywords)
    found_manip_tag = any(k in software for k in manip_keywords)

    if found_ai_tag:
        ai_score += 45
        confidence = 90
        signals.append({
            "feature": "Metadata Generator Signatures",
            "finding": f"Metadata references AI generation software ({software or description})",
            "implication": "High probability of AI synthesis",
            "level": "high"
        })
    elif found_manip_tag:
        manip_score += 40
        signals.append({
            "feature": "Editing Software Metadata",
            "finding": f"Processed with photo editing suite: {software}",
            "implication": "Likely digital manipulation or post-processing",
            "level": "medium"
        })
    elif make and model:
        ai_score -= 20
        manip_score -= 10
        signals.append({
            "feature": "Hardware Camera Signature",
            "finding": f"Valid hardware camera EXIF detected ({make} {model})",
            "implication": "Strong indicator of authentic optical capture",
            "level": "low"
        })
    else:
        signals.append({
            "feature": "EXIF Header Stripping",
            "finding": "No camera or hardware metadata found in file headers",
            "implication": "Common with web-compressed, edited, or AI-generated media",
            "level": "neutral"
        })

    # 2. Aspect Ratio and Resolution Forensics
    w, h = meta["width"], meta["height"]
    standard_ai_resolutions = [(1024, 1024), (512, 512), (768, 768), (1024, 1536), (1536, 1024), (896, 1152), (1152, 896), (1344, 768), (768, 1344)]
    if (w, h) in standard_ai_resolutions or (h, w) in standard_ai_resolutions:
        ai_score += 15
        signals.append({
            "feature": "Native AI Aspect Grid",
            "finding": f"Resolution ({w}x{h}) matches common AI generation canvas dimensions",
            "implication": "Consistent with latent diffusion generation grid",
            "level": "medium"
        })

    # Clamp scores
    ai_score = max(5, min(95, ai_score))
    manip_score = max(5, min(95, manip_score))

    # Determine classification
    if ai_score >= 65:
        classification = "Likely AI-Generated"
    elif manip_score >= 60:
        classification = "Likely Manipulated"
    elif ai_score <= 30 and manip_score <= 30 and meta.get("has_exif"):
        classification = "Likely Authentic"
    else:
        classification = "Inconclusive"

    return {
        "classification": classification,
        "ai_probability": ai_score,
        "manipulation_probability": manip_score,
        "confidence": confidence,
        "signals": signals,
        "metadata_forensics": {
            "dimensions": f"{w}x{h}",
            "format": meta["format"],
            "camera_make": make or "None",
            "camera_model": model or "None",
            "software": software or "None"
        },
        "limitations_disclaimer": "AI and manipulation detection is probabilistic. Findings should be considered as technical indicators and not definitive forensic proof."
    }
