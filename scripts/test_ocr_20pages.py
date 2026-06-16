import sys, os, time
sys.path.insert(0, "/app")
os.environ["PYTHONUNBUFFERED"] = "1"

from rapidocr import RapidOCR
import pypdfium2 as pdfium

ocr = RapidOCR()
doc = pdfium.PdfDocument("/app/data/textbooks/Grade10/grade 10-biology_kehulumcom_d02c.pdf")
total = len(doc)
t0 = time.time()

for i in range(min(20, total)):
    page_num = i + 1
    page = doc[i]
    image = page.render(scale=0.5)
    bitmap = image.to_numpy()
    result = ocr(bitmap)
    n_chars = 0
    if result.txts:
        n_chars = sum(len(t) for t in result.txts)
    elapsed = time.time() - t0
    print(f"Page {page_num}: {elapsed:.1f}s, {n_chars} chars", flush=True)

doc.close()
print(f"DONE: {total} total, {time.time()-t0:.1f}s", flush=True)
