import sys, os, asyncio, time, concurrent.futures
sys.path.insert(0, "/app")
os.environ["PYTHONUNBUFFERED"] = "1"

from rapidocr import RapidOCR
import pypdfium2 as pdfium
import scripts.ingest_curriculum as ic

_PAGE_TIMEOUT = 120

def patched_ocr(filepath, page_numbers=None):
    ocr = RapidOCR()
    doc = pdfium.PdfDocument(filepath)
    pages = []
    total = len(doc)
    t0 = time.time()

    def ocr_page(page, page_num):
        image = page.render(scale=0.5)
        bitmap = image.to_numpy()
        result = ocr(bitmap)
        if result.txts:
            text = " ".join(result.txts).strip()
            if text:
                return {"text": text, "page_number": page_num}
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        for i in range(total):
            page_num = i + 1
            if page_numbers is not None and page_num not in page_numbers:
                continue
            try:
                fut = pool.submit(ocr_page, doc[i], page_num)
                result = fut.result(timeout=_PAGE_TIMEOUT)
                if result:
                    pages.append(result)
            except concurrent.futures.TimeoutError:
                print(f"  Page {page_num}: TIMEOUT after {_PAGE_TIMEOUT}s, skipping", flush=True)
            except Exception as e:
                print(f"  Page {page_num}: ERROR {e}, skipping", flush=True)
            if (i + 1) % 10 == 0 or i == total - 1:
                elapsed = time.time() - t0
                remaining = total - (i + 1)
                eta = (elapsed / (i + 1)) * remaining / 60 if (i + 1) > 0 else 0
                print(f"  Page {page_num}/{total}: {len(pages)} texts, {elapsed/60:.1f}m, ETA {eta:.0f}m", flush=True)
    doc.close()
    return pages

from src.llm.ollama_client import OllamaClient
_original_gen_emb = OllamaClient.generate_embedding

async def patched_gen_emb(self, text, model=None):
    try:
        return await asyncio.wait_for(_original_gen_emb(self, text, model), timeout=30.0)
    except asyncio.TimeoutError:
        print("  Embedding timeout (30s), returning zeros", flush=True)
        return [0.0] * 384
    except Exception as e:
        print(f"  Embedding error: {e}, returning zeros", flush=True)
        return [0.0] * 384

OllamaClient.generate_embedding = patched_gen_emb

ic._extract_with_ocr = patched_ocr
sys.argv = ["ingest_curriculum.py", "--use-docling", "--grade", "10"]
asyncio.run(ic.main())
