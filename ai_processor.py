import os
import re
import anthropic
from dotenv import load_dotenv
from pathlib import Path

# Always load .env from project root (same folder as this file),
# so it works even when the IDE run cwd is different.
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def _build_image_manifest(image_records):
    if not image_records:
        return "Not Available"
    lines = []
    for record in image_records:
        lines.append(
            f"- {record['file_name']} (source={record['source']}, page={record['page']})"
        )
    return "\n".join(lines)


def _local_ddr_fallback(inspection_text, thermal_text, image_records):
    """
    Build a basic DDR without calling external LLM APIs.
    This keeps the pipeline runnable when API credits are unavailable.
    """
    combined = f"{inspection_text}\n\n{thermal_text}"
    lower = combined.lower()

    issue_signals = [
        "leak", "damp", "moisture", "crack", "seepage", "stain",
        "thermal anomaly", "hotspot", "cold spot", "water ingress",
    ]
    found_signals = [s for s in issue_signals if s in lower]
    summary_line = (
        "Observed issues include: " + ", ".join(found_signals) + "."
        if found_signals
        else "Potential issues are present in the provided inspection and thermal documents."
    )

    area_candidates = re.findall(
        r"\b(kitchen|bathroom|bedroom|living room|ceiling|wall|roof|terrace|balcony|toilet|corridor)\b",
        lower,
    )
    unique_areas = []
    for area in area_candidates:
        area_title = area.title()
        if area_title not in unique_areas:
            unique_areas.append(area_title)
    if not unique_areas:
        unique_areas = ["General Areas"]

    image_names = [r["file_name"] for r in image_records]
    img_idx = 0
    area_lines = []
    for area in unique_areas[:8]:
        area_lines.append(f"### {area}")
        area_lines.append("- Visual findings are available in source inspection document.")
        area_lines.append("- Thermal findings are referenced from thermal document where relevant.")
        if img_idx < len(image_names):
            area_lines.append(f"- [Image: {image_names[img_idx]}]")
            img_idx += 1
        else:
            area_lines.append("- Image Not Available")

    missing_line = "Not Available"
    if "not available" in lower:
        missing_line = "Some details are explicitly marked as Not Available in source documents."

    ddr = f"""## 1. Property Issue Summary
{summary_line}

## 2. Area-wise Observations
{chr(10).join(area_lines)}

## 3. Probable Root Cause
- Likely causes include moisture ingress, material deterioration, or thermal insulation gaps based on reported observations.
- Exact engineering validation is Not Available in the provided reports.

## 4. Severity Assessment (with reasoning)
- High: Areas with active moisture/leak indicators, because continued exposure can cause structural and health risks.
- Medium: Areas with repeated thermal anomalies, because they may indicate hidden defects needing near-term checks.
- Low: Cosmetic observations without supporting thermal or progression evidence.

## 5. Recommended Actions
- Conduct targeted on-site validation for high severity areas first.
- Repair moisture ingress pathways and damaged finishes.
- Re-scan affected zones after corrective action.
- Keep dated photo/thermal evidence for closure reporting.

## 6. Additional Notes
- This version is generated via fallback mode due to API availability limits.
- Statements are restricted to provided document context and generic reporting language.

## 7. Missing or Unclear Information
- Exact moisture source confirmation: Not Available
- Engineering test measurements beyond report scope: Not Available
- Conflicting statements across reports: Not Available
- Source completeness note: {missing_line}
"""
    return ddr


def generate_ddr(inspection_text, thermal_text, image_records):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _local_ddr_fallback(inspection_text, thermal_text, image_records)

    client = anthropic.Anthropic(api_key=api_key)
    image_manifest = _build_image_manifest(image_records)

    prompt = f"""
You are an expert diagnostics report writer.

You are given:
1) Inspection report text
2) Thermal report text
3) Extracted image manifest with file names and source page

Goal:
Create a client-friendly DDR (Detailed Diagnostic Report) using ONLY provided facts.

Critical rules:
- Do not invent facts
- If information is missing, write "Not Available"
- If facts conflict, explicitly mention the conflict
- Merge both reports logically without duplicate points
- Keep language simple and client-friendly

Image usage rules:
- Use only file names from the image manifest
- Place image markers where relevant in area observations using this exact syntax:
  [Image: file_name.ext]
- If a relevant image is not available for an area, write: Image Not Available
- Do not reference images not in the manifest

Required output sections (exact headers):
## 1. Property Issue Summary
## 2. Area-wise Observations
## 3. Probable Root Cause
## 4. Severity Assessment (with reasoning)
## 5. Recommended Actions
## 6. Additional Notes
## 7. Missing or Unclear Information

For section 2, use subheadings per area with format:
### <Area Name>

Then add concise bullet points for findings and image markers.

IMAGE MANIFEST:
{image_manifest}

INSPECTION REPORT CONTENT:
{inspection_text}

THERMAL REPORT CONTENT:
{thermal_text}
"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception:
        # Fallback on billing/quota/network/model issues so report generation continues.
        return _local_ddr_fallback(inspection_text, thermal_text, image_records)