import os
import fitz  # pymupdf


def extract_from_pdf(pdf_path, image_output_dir, prefix="doc"):
    """
    Extract text and images from a PDF.
    Returns:
      - full_text: concatenated page text
      - image_records: list of dicts with image metadata
      - page_text_map: dict[page_number] -> text content
    """
    doc = fitz.open(pdf_path)
    full_text_parts = []
    image_records = []
    page_text_map = {}

    for page_idx in range(len(doc)):
        page_num = page_idx + 1
        page = doc[page_idx]
        page_text = page.get_text().strip()

        page_text_map[page_num] = page_text
        full_text_parts.append(f"--- Page {page_num} ---\n{page_text}")

        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image.get("ext", "png")

            image_filename = f"{prefix}_page{page_num}_img{img_index + 1}.{ext}"
            image_filepath = os.path.join(image_output_dir, image_filename)

            with open(image_filepath, "wb") as f:
                f.write(image_bytes)

            image_records.append(
                {
                    "file_name": image_filename,
                    "file_path": image_filepath,
                    "source": prefix,
                    "page": page_num,
                    "index_on_page": img_index + 1,
                }
            )

    return "\n\n".join(full_text_parts), image_records, page_text_map