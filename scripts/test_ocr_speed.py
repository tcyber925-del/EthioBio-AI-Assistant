import sys, os, time
sys.path.insert(0, "/app")
os.environ["PYTHONUNBUFFERED"] = "1"

from rapidocr import RapidOCR
import pypdfium2 as pdfium

ocr = RapidOCR()
doc = pdfium.PdfDocument("/app/data/textbooks/Grade10/grade 10-biology_kehulumcom_d02c.pdf")
total = len(doc)

for page_num in [1, 2, 3, 4, 5]:
    t0 = time.time()
    page = doc[page_num - 1]
    image = page.render(scale=0.5)
    bitmap = image.to_numpy()
    result = ocr(bitmap)
    elapsed = time.time() - t0
    n_chars = 0
    if result.txts:
        n_chars = sum(len(t) for t in result.txts)
    print(f"Page {page_num}: {elapsed:.1f}s, {n_chars} chars", flush=True)

doc.close()
print("DONE", flush=True)
