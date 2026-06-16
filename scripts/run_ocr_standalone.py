import sys, os, time, concurrent.futures
os.environ["PYTHONUNBUFFERED"] = "1"

from rapidocr import RapidOCR
import pypdfium2 as pdfium

FILEPATH = "/app/data/textbooks/Grade10/grade 10-biology_kehulumcom_d02c.pdf"
_PAGE_TIMEOUT = 180

def extract_text():
    ocr = RapidOCR()
    doc = pdfium.PdfDocument(FILEPATH)
    total = len(doc)
    pages = []
    t0 = time.time()

    def ocr_page(page, page_num):
        try:
            image = page.render(scale=0.5)
            bitmap = image.to_numpy()
            result = ocr(bitmap)
            if result.txts:
                text = " ".join(result.txts).strip()
                return text if text else None
            return None
        except Exception as e:
            print(f"  Page {page_num}: OCR error: {e}", flush=True)
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        for i in range(total):
            page_num = i + 1
            try:
                fut = pool.submit(ocr_page, doc[i], page_num)
                text = fut.result(timeout=_PAGE_TIMEOUT)
                if text:
                    pages.append({"text": text, "page_number": page_num})
            except concurrent.futures.TimeoutError:
                print(f"  Page {page_num}: TIMEOUT {_PAGE_TIMEOUT}s", flush=True)
            except Exception as e:
                print(f"  Page {page_num}: ERROR {e}", flush=True)

            if (i + 1) % 10 == 0 or i == total - 1:
                elapsed = time.time() - t0
                rate = (i + 1) / (elapsed / 60) if elapsed > 0 else 0
                eta = (total - (i + 1)) / rate if rate > 0 else 0
                print(f"  Page {page_num}/{total}: {len(pages)} texts, {elapsed/60:.1f}m, {rate:.0f}/min, ETA {eta:.0f}m", flush=True)

    doc.close()
    return pages

pages = extract_text()
print(f"DONE: {len(pages)} pages extracted", flush=True)
