import asyncio
import os
import sys
import time

sys.path.insert(0, "/app")
os.environ["PYTHONUNBUFFERED"] = "1"

import pypdfium2 as pdfium
from rapidocr import RapidOCR

import scripts.ingest_curriculum as ic


def patched_ocr(filepath, page_numbers=None):
    ocr = RapidOCR()
    doc = pdfium.PdfDocument(filepath)
    pages = []
    total = len(doc)
    t0 = time.time()
    for i in range(total):
        page_num = i + 1
        if page_numbers is not None and page_num not in page_numbers:
            continue
        try:
            page = doc[i]
            image = page.render(scale=0.5)
            bitmap = image.to_numpy()
            result = ocr(bitmap)
            if result.txts:
                text = " ".join(result.txts).strip()
                if text:
                    pages.append({"text": text, "page_number": page_num})
        except Exception as e:
            print(f"  Page {page_num}: error: {e}", flush=True)
        if (i + 1) % 10 == 0 or i == total - 1:
            elapsed = time.time() - t0
            remaining = total - (i + 1)
            eta = (elapsed / (i + 1)) * remaining / 60 if (i + 1) > 0 else 0
            print(f"  Page {page_num}/{total}: {len(pages)} texts, {elapsed/60:.1f}m, ETA {eta:.0f}m", flush=True)
    doc.close()
    return pages

ic._extract_with_ocr = patched_ocr

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

sys.argv = ["ingest_curriculum.py", "--use-docling", "--grade", "10"]
asyncio.run(ic.main())
