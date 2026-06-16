"""
Standalone Grade 10 OCR script.
No app module imports — pure OCR + JSON output.
"""
import json, os, sys, time

os.environ["PYTHONUNBUFFERED"] = "1"

from rapidocr import RapidOCR
import pypdfium2 as pdfium

PDF_PATH = "/app/data/textbooks/Grade10/grade 10-biology_kehulumcom_d02c.pdf"
OUT_PATH = "/tmp/grade10_ocr.json"

def ocr_all():
    ocr = RapidOCR()
    doc = pdfium.PdfDocument(PDF_PATH)
    total = len(doc)
    pages = []
    t0 = time.time()

    for i in range(total):
        page_num = i + 1
        try:
            page = doc[i]
            image = page.render(scale=0.5)
            bitmap = image.to_numpy()
            result = ocr(bitmap)
            if result.txts:
                text = " ".join(result.txts).strip()
                if text:
                    pages.append({
                        "page_number": page_num,
                        "text": text,
                        "char_count": len(text)
                    })
        except Exception as e:
            print(f"  Error page {page_num}: {e}", flush=True)

        elapsed = time.time() - t0
        remaining = total - (i + 1)
        eta = (elapsed / (i + 1)) * remaining if (i + 1) > 0 else 0
        chars_so_far = sum(p["char_count"] for p in pages)
        print(f"  [{page_num}/{total}] {len(pages)} pages OCR'd, {chars_so_far} chars, "
              f"{elapsed/60:.1f}m elapsed, ETA {eta/60:.0f}m", flush=True)

    doc.close()

    with open(OUT_PATH, "w") as f:
        json.dump({"total_pages": total, "ocr_pages": pages}, f)
    print(f"\nDone: {len(pages)}/{total} pages with text -> {OUT_PATH}", flush=True)
    return pages

if __name__ == "__main__":
    ocr_all()
