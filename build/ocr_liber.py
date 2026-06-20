#!/usr/bin/env python3
"""OCR a scanned Liber PDF into page-indexed text for the legion audit.

Renders each page at 200 dpi with PyMuPDF and runs RapidOCR (self-contained ONNX,
no tesseract/poppler needed). Writes one combined text file with `===== PDF PAGE N =====`
markers so units can be matched to pages by their title line.

Usage:  python3 build/ocr_liber.py <pdf> <out.txt> [start_page] [end_page]
Numbers (points) garble in OCR — confirm against the rendered page image.
"""
import sys, fitz
from rapidocr_onnxruntime import RapidOCR

pdf_path, out_path = sys.argv[1], sys.argv[2]
doc = fitz.open(pdf_path)
start = int(sys.argv[3]) if len(sys.argv) > 3 else 1
end = int(sys.argv[4]) if len(sys.argv) > 4 else doc.page_count
ocr = RapidOCR()

with open(out_path, "w", encoding="utf-8") as f:
    for i in range(start - 1, min(end, doc.page_count)):
        page = doc[i]
        pix = page.get_pixmap(dpi=200)
        png = pix.tobytes("png")
        res, _ = ocr(png)
        text = "\n".join(line[1] for line in res) if res else ""
        f.write(f"===== PDF PAGE {i+1} =====\n{text}\n")
        f.flush()
        if (i + 1) % 10 == 0:
            print(f"  {pdf_path.split('/')[-1]}: page {i+1}/{end}", flush=True)
print(f"DONE {out_path}  ({end-start+1} pages)", flush=True)
