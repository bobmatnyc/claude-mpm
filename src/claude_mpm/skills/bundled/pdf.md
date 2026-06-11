---
skill_id: pdf
skill_version: 0.3.0
when_to_use: when generating, reading, converting, merging, or extracting content from PDF files programmatically
description: Common PDF operations and libraries across languages.
updated_at: 2025-10-30T17:00:00Z
tags: [pdf, document-processing, manipulation, media]
effort: low
---

# PDF Manipulation

Common PDF operations and libraries across languages.

## Python (PyPDF2 / pikepdf)

### Reading PDF
```python
from PyPDF2 import PdfReader

reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

# Extract text
text = reader.pages[0].extract_text()
```

### Writing PDF
```python
from PyPDF2 import PdfWriter, PdfReader

reader = PdfReader("input.pdf")
writer = PdfWriter()

# Copy pages
for page in reader.pages:
    writer.add_page(page)

# Save
with open("output.pdf", "wb") as f:
    writer.write(f)
```

### Merging PDFs
```python
from PyPDF2 import PdfMerger

merger = PdfMerger()
merger.append("file1.pdf")
merger.append("file2.pdf")
merger.write("merged.pdf")
merger.close()
```

### Splitting PDF
```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i}.pdf", "wb") as f:
        writer.write(f)
```

## JavaScript (pdf-lib)

```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

// Load existing PDF
const existingPdfBytes = fs.readFileSync('input.pdf');
const pdfDoc = await PDFDocument.load(existingPdfBytes);

// Get pages
const pages = pdfDoc.getPages();
const firstPage = pages[0];

// Add text
firstPage.drawText('Hello World!', {
  x: 50,
  y: 50,
  size: 30
});

// Save
const pdfBytes = await pdfDoc.save();
fs.writeFileSync('output.pdf', pdfBytes);
```

## Common Operations

### Extracting Images
```python
import fitz  # PyMuPDF

doc = fitz.open("document.pdf")
for page_num in range(len(doc)):
    page = doc[page_num]
    images = page.get_images()

    for img_index, img in enumerate(images):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]

        with open(f"image_{page_num}_{img_index}.png", "wb") as f:
            f.write(image_bytes)
```

### Adding Watermark
```python
from PyPDF2 import PdfReader, PdfWriter

# Create watermark PDF first
watermark_reader = PdfReader("watermark.pdf")
watermark_page = watermark_reader.pages[0]

# Apply to document
reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark_page)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as f:
    writer.write(f)
```

### Compressing PDF
```python
from pikepdf import Pdf

with Pdf.open("input.pdf") as pdf:
    pdf.save("compressed.pdf", compress_streams=True)
```

## Non-Obvious Patterns (the gotchas)

These are the things the library quick-starts above will NOT warn you about:

- **`extract_text()` returns garbage or empty for scanned/image PDFs** — there is no text layer. Detect this (empty/whitespace result) and fall back to OCR (`pytesseract` on rasterized pages via PyMuPDF), don't silently emit empty strings.
- **`PdfWriter` does NOT inherit form fields, annotations, or bookmarks** by default when you copy pages — interactive PDFs lose their AcroForm. Use `writer.append()` / `clone_document_from_reader()` (pypdf ≥3) to preserve structure, or pikepdf which keeps the object graph intact.
- **`merge_page()` watermarks render UNDER existing content for opaque pages** — a filled background hides the page. Watermark PDFs must have a transparent background, and overlay direction matters (`merge_page` vs `merge_transformed_page`).
- **`pikepdf` ≫ `PyPDF2`/`pypdf` for linearization, encryption, and repair** — pikepdf wraps QPDF (C++), so it round-trips malformed/encrypted PDFs that pure-Python writers corrupt. Prefer it whenever you "save" a PDF you didn't generate.
- **`pdf-lib` (JS) cannot extract text** — it is a creation/modification library only. For text extraction in Node use `pdfjs-dist` or `pdf-parse`.
- **`compress_streams=True` is lossless** (stream re-compression only). To actually shrink image-heavy PDFs you must downsample the embedded images — that is a separate, lossy step pikepdf does not do for you.

## Remember
- Check PDF file size before processing
- Handle corrupted PDFs gracefully
- Use appropriate library for task (pikepdf > PyPDF2 for complex ops)
- Consider memory usage for large PDFs
