---
skill_id: imagemagick
skill_version: 0.1.0
description: Image manipulation and optimization techniques using ImageMagick.
updated_at: 2025-10-30T17:00:00Z
tags: [imagemagick, image-processing, optimization, media]
---

# ImageMagick/Image Optimization

Image manipulation and optimization techniques.

## ImageMagick CLI

### Basic Operations

```bash
# Resize image
convert input.jpg -resize 800x600 output.jpg

# Convert format
convert input.png output.jpg

# Compress JPEG
convert input.jpg -quality 85 output.jpg

# Create thumbnail
convert input.jpg -thumbnail 200x200 thumb.jpg
```

### Batch Operations

```bash
# Resize all images in directory
for img in *.jpg; do
  convert "$img" -resize 800x600 "resized_$img"
done

# Convert all PNGs to JPGs
mogrify -format jpg *.png
```

### Advanced

```bash
# Add watermark
convert input.jpg watermark.png -gravity southeast -composite output.jpg

# Crop image
convert input.jpg -crop 800x600+100+100 output.jpg

# Rotate
convert input.jpg -rotate 90 output.jpg

# Grayscale
convert input.jpg -colorspace Gray output.jpg
```

## Python (Pillow)

### Basic Operations

```python
from PIL import Image

# Open image
img = Image.open('input.jpg')

# Resize
img_resized = img.resize((800, 600))
img_resized.save('output.jpg')

# Convert format
img.save('output.png')

# Compress
img.save('compressed.jpg', quality=85, optimize=True)

# Thumbnail
img.thumbnail((200, 200))
img.save('thumb.jpg')
```

### Advanced Operations

```python
# Crop
box = (100, 100, 900, 700)  # left, top, right, bottom
cropped = img.crop(box)

# Rotate
rotated = img.rotate(90, expand=True)

# Grayscale
gray = img.convert('L')

# Add watermark
watermark = Image.open('watermark.png')
img.paste(watermark, (img.width - watermark.width, img.height - watermark.height), watermark)
```

### Optimization

```python
# Optimize PNG
from PIL import Image

img = Image.open('input.png')
img.save('optimized.png', optimize=True)

# Optimize JPEG
img.save('optimized.jpg', quality=85, optimize=True, progressive=True)

# WebP format (better compression)
img.save('output.webp', quality=80)
```

## JavaScript (sharp)

```javascript
const sharp = require('sharp');

// Resize
await sharp('input.jpg')
  .resize(800, 600)
  .toFile('output.jpg');

// Compress
await sharp('input.jpg')
  .jpeg({ quality: 85 })
  .toFile('compressed.jpg');

// Convert format
await sharp('input.png')
  .jpeg()
  .toFile('output.jpg');

// Thumbnail
await sharp('input.jpg')
  .resize(200, 200, { fit: 'cover' })
  .toFile('thumb.jpg');
```

## Image Optimization Guidelines

### Web Images

```
Format recommendations:
- Photos: JPEG (quality 85) or WebP (quality 80)
- Graphics/logos: PNG or SVG
- Animations: WebP or video

Size recommendations:
- Hero images: 1920px width max
- Content images: 1200px width max
- Thumbnails: 200-400px
- Icons: 64px or SVG
```

### Responsive Images

```html
<picture>
  <source srcset="image-320w.jpg" media="(max-width: 320px)">
  <source srcset="image-640w.jpg" media="(max-width: 640px)">
  <source srcset="image-1024w.jpg" media="(max-width: 1024px)">
  <img src="image-1920w.jpg" alt="Description">
</picture>
```

## Common Tasks

### Bulk Resize and Compress

```python
from PIL import Image
import os

def optimize_images(input_dir, output_dir, max_size=(1200, 1200)):
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            img = Image.open(input_path)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            if filename.lower().endswith('.png'):
                img.save(output_path, 'PNG', optimize=True)
            else:
                img.save(output_path, 'JPEG', quality=85, optimize=True)

optimize_images('originals/', 'optimized/')
```

## Remember
- Always keep original files
- Test optimized images for quality
- Use WebP for modern browsers
- Progressive JPEGs for better perceived load time
- Lazy load images not in viewport
