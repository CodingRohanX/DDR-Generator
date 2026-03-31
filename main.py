from extractor import extract_from_pdf
from ai_processor import generate_ddr
from report_builder import build_word_report
import os

# --- Paths ---
INSPECTION_PDF = "inputs/Sample Report.pdf"
THERMAL_PDF = "inputs/Thermal Images.pdf"
IMAGE_DIR      = "extracted_images"
OUTPUT_REPORT  = "outputs/DDR_Report.docx"
OUTPUT_TEXT = "outputs/DDR_Report.md"

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs("outputs", exist_ok=True)

print("Extracting Inspection Report...")
inspection_text, inspection_images, _ = extract_from_pdf(
    INSPECTION_PDF, IMAGE_DIR, prefix="inspection"
)

print("Extracting Thermal Report...")
thermal_text, thermal_images, _ = extract_from_pdf(
    THERMAL_PDF, IMAGE_DIR, prefix="thermal"
)

print("Sending to Claude AI for DDR generation...")
all_images = inspection_images + thermal_images
ddr_text = generate_ddr(inspection_text, thermal_text, all_images)

with open(OUTPUT_TEXT, "w", encoding="utf-8") as f:
    f.write(ddr_text)

print("Building Word Report...")
build_word_report(ddr_text, all_images, OUTPUT_REPORT)

print("\nDONE! Check your outputs/ folder for the DDR markdown and Word report.")