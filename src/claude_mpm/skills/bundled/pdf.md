---
skill_id: pdf
skill_version: 0.1.0
description: Common PDF operations and libraries across languages.
updated_at: 2025-10-30T17:00:00Z
tags: [pdf, document-processing, manipulation, media]
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

## Remember
- Check PDF file size before processing
- Handle corrupted PDFs gracefully
- Use appropriate library for task (pikepdf > PyPDF2 for complex ops)
- Consider memory usage for large PDFs
