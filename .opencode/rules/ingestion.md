# PDF Ingestion — EthioSci AI Assistant

Read when: re-ingesting curriculum PDFs into the vector store, dealing with garbled PDFs.

## OCR Options

| Flag | Extractor | Quality | Speed | Language Support |
|------|-----------|---------|-------|-----------------|
| *(default)* | PyMuPDF text | ★★★★★ | Instant | PDF text layer only |
| `--use-docling` | RapidOCR | ★★★ | ~15 p/min | English only |
| `--use-tesseract` | Tesseract | ★★ | ~1 p/min | English+Ethiopic (very slow) |
| `--use-easyocr` | EasyOCR | ★★★★ | ~1.5 p/min | English only (no Amharic model) |

**EasyOCR** (`--use-easyocr`): Best option for image-heavy PDFs. PyTorch-based, renders at 100 DPI. ~50s/page on CPU. Grade 10 re-ingested with this method.

**PaddleOCR** (not integrated): Would support 109 languages including Amharic, but PaddlePaddle 3.3.1 has a PIR compiler bug blocking deployment.

## Commands

```bash
python scripts/ingest_curriculum.py --use-easyocr --grade 10            # Re-ingest single grade
python scripts/ingest_curriculum.py --use-easyocr --grade 10 --clear    # Clear + re-ingest
python scripts/ingest_curriculum.py --stats                              # Show vector store stats
```

Files are copied to the container via `docker cp` (not volume-mounted). After updating the script on the host, run `docker cp scripts/ingest_curriculum.py ethiosci-app:/app/scripts/ingest_curriculum.py`.
