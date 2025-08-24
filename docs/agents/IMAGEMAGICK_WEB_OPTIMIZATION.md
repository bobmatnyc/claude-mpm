# ImageMagick Web Optimization Agent Guidelines

## Executive Summary

This document provides comprehensive guidelines for an ImageMagick agent specialized in optimizing images for modern web use in 2025. The agent should focus on delivering optimal file sizes, supporting modern formats, ensuring responsive design compatibility, and maintaining visual quality while meeting Core Web Vitals requirements.

## Core Principles

### 1. Format-First Strategy
- **AVIF** (primary): 50% smaller than JPEG, supports HDR, transparency, wide color gamut
- **WebP** (fallback): 30% smaller than JPEG, broader browser support
- **JPEG** (legacy): For maximum compatibility
- **SVG**: For logos, icons, and simple graphics
- **PNG**: Only when transparency is required and modern formats unavailable

### 2. Performance Targets
- **Hero/Header Images**: < 250KB (1920px wide)
- **Product/Content Images**: < 200KB (standard), < 300KB (high-quality)
- **Thumbnail Images**: < 50KB
- **Background Images**: < 200KB (1920x1080)
- **Total Page Weight**: 1-1.5MB ideal, never exceed 3MB
- **Maximum Single File**: Never exceed 20MB

### 3. Core Web Vitals Impact
- Optimize for Largest Contentful Paint (LCP) < 2.5s
- Prevent Cumulative Layout Shift (CLS) by specifying dimensions
- Minimize Total Blocking Time through lazy loading
- Target 20-30% LCP improvement on image-heavy pages

## Essential ImageMagick Commands

### Format Conversion

```bash
# Convert to WebP (lossy)
magick input.jpg -quality 85 -define webp:method=6 output.webp

# Convert to WebP (lossless)
magick input.jpg -quality 100 -define webp:lossless=true output.webp

# Convert to AVIF
magick input.jpg -quality 85 -define avif:speed=3 output.avif

# Batch conversion to AVIF
for image in *.jpg; do 
  magick "$image" -quality 85 -define avif:speed=3 "${image%.jpg}.avif"
done

# Batch conversion to WebP
magick mogrify -format webp -quality 85 -define webp:method=6 *.jpg
```

### Responsive Image Generation

```bash
# Generate multiple sizes for srcset
magick input.jpg \
  \( -clone 0 -resize 640x -write small.jpg \) \
  \( -clone 0 -resize 1024x -write medium.jpg \) \
  \( -clone 0 -resize 1920x -write large.jpg \) \
  \( -clone 0 -resize 2560x -write xlarge.jpg \) \
  null:

# Generate responsive variants with modern formats
for size in 640 1024 1920 2560; do
  magick input.jpg -resize ${size}x -quality 85 output-${size}w.jpg
  magick input.jpg -resize ${size}x -quality 85 -define webp:method=6 output-${size}w.webp
  magick input.jpg -resize ${size}x -quality 85 -define avif:speed=3 output-${size}w.avif
done
```

### Quality Optimization

```bash
# Standard web optimization (sRGB conversion, metadata stripping)
magick input.jpg -profile sRGB.icc -resize 1920x1080> -quality 85 -strip output.jpg

# High-quality resize with Lanczos filter
magick input.jpg -filter Lanczos -resize 1920x1080 -quality 90 output.jpg

# Sharp resize for product images
magick input.jpg -filter Catrom -resize 800x800 -unsharp 0x1 output.jpg

# Adaptive quality based on content
magick input.jpg -resize 1920x -quality 85 -sampling-factor 4:2:0 -strip output.jpg
```

### Color Profile and Metadata Management

```bash
# Convert to sRGB and strip metadata
magick input.jpg -profile sRGB.icc -strip output.jpg

# Strip all metadata except color profile
magick input.jpg -thumbnail 1200x800> output.jpg

# Complete optimization pipeline
magick input.jpg \
  -profile sRGB.icc \
  -resize 1920x1080> \
  -quality 85 \
  -sampling-factor 4:2:0 \
  -strip \
  -define jpeg:optimize-coding=true \
  output.jpg
```

### Smart Cropping and Art Direction

```bash
# Center crop to specific aspect ratio
magick input.jpg -gravity center -crop 16:9 output.jpg

# Entropy-based smart crop (finds busy areas)
magick input.jpg -gravity center -extent 800x600 output.jpg

# Face-aware cropping (requires external detection)
# First detect face coordinates, then:
magick input.jpg -gravity northwest -crop 800x600+${x}+${y} output.jpg

# Generate square thumbnails with smart cropping
magick input.jpg -resize 500x500^ -gravity center -extent 500x500 output.jpg
```

## Optimization Workflows

### 1. Hero Image Optimization

```bash
#!/bin/bash
# Optimize hero image for web with multiple formats

INPUT="$1"
BASE="${INPUT%.*}"

# Generate responsive sizes in multiple formats
for width in 640 1024 1920 2560; do
  # AVIF (best compression)
  magick "$INPUT" \
    -profile sRGB.icc \
    -resize ${width}x \
    -quality 85 \
    -define avif:speed=3 \
    -strip \
    "${BASE}-${width}w.avif"
  
  # WebP (good compatibility)
  magick "$INPUT" \
    -profile sRGB.icc \
    -resize ${width}x \
    -quality 85 \
    -define webp:method=6 \
    -strip \
    "${BASE}-${width}w.webp"
  
  # JPEG (fallback)
  magick "$INPUT" \
    -profile sRGB.icc \
    -resize ${width}x \
    -quality 85 \
    -sampling-factor 4:2:0 \
    -strip \
    "${BASE}-${width}w.jpg"
done
```

### 2. Product Image Optimization

```bash
#!/bin/bash
# Optimize product images with consistent dimensions

INPUT="$1"
OUTPUT_BASE="${INPUT%.*}"

# Main product image
magick "$INPUT" \
  -profile sRGB.icc \
  -resize 1200x1200 \
  -background white \
  -gravity center \
  -extent 1200x1200 \
  -quality 90 \
  -strip \
  "${OUTPUT_BASE}-main.jpg"

# Thumbnail
magick "$INPUT" \
  -profile sRGB.icc \
  -resize 300x300^ \
  -gravity center \
  -extent 300x300 \
  -quality 85 \
  -strip \
  "${OUTPUT_BASE}-thumb.jpg"

# Convert to modern formats
magick "${OUTPUT_BASE}-main.jpg" -define webp:method=6 "${OUTPUT_BASE}-main.webp"
magick "${OUTPUT_BASE}-main.jpg" -define avif:speed=3 "${OUTPUT_BASE}-main.avif"
```

### 3. Batch Processing Pipeline

```bash
#!/bin/bash
# Comprehensive batch optimization

QUALITY_HIGH=90
QUALITY_STANDARD=85
QUALITY_LOW=75

process_image() {
  local input="$1"
  local base="${input%.*}"
  local ext="${input##*.}"
  
  # Determine quality based on file size
  local size=$(stat -f%z "$input" 2>/dev/null || stat -c%s "$input")
  local quality=$QUALITY_STANDARD
  
  if [ "$size" -gt 5000000 ]; then
    quality=$QUALITY_LOW
  elif [ "$size" -lt 500000 ]; then
    quality=$QUALITY_HIGH
  fi
  
  # Process image
  magick "$input" \
    -profile sRGB.icc \
    -resize 1920x1080> \
    -quality $quality \
    -strip \
    -define jpeg:optimize-coding=true \
    "${base}-optimized.${ext}"
  
  # Generate modern formats
  magick "${base}-optimized.${ext}" \
    -define webp:method=6 \
    "${base}-optimized.webp"
  
  magick "${base}-optimized.${ext}" \
    -define avif:speed=3 \
    "${base}-optimized.avif"
}

# Process all images in directory
for img in *.{jpg,jpeg,png,JPG,JPEG,PNG}; do
  [ -f "$img" ] && process_image "$img"
done
```

## Responsive Image Implementation

### HTML Output Templates

```html
<!-- Picture element with art direction -->
<picture>
  <source media="(max-width: 640px)" 
          srcset="image-640w.avif" type="image/avif">
  <source media="(max-width: 640px)" 
          srcset="image-640w.webp" type="image/webp">
  <source media="(max-width: 1024px)" 
          srcset="image-1024w.avif" type="image/avif">
  <source media="(max-width: 1024px)" 
          srcset="image-1024w.webp" type="image/webp">
  <source srcset="image-1920w.avif" type="image/avif">
  <source srcset="image-1920w.webp" type="image/webp">
  <img src="image-1920w.jpg" 
       alt="Description" 
       width="1920" 
       height="1080"
       loading="lazy">
</picture>

<!-- Responsive img with srcset -->
<img src="image-1920w.jpg"
     srcset="image-640w.jpg 640w,
             image-1024w.jpg 1024w,
             image-1920w.jpg 1920w,
             image-2560w.jpg 2560w"
     sizes="(max-width: 640px) 100vw,
            (max-width: 1024px) 100vw,
            1920px"
     alt="Description"
     width="1920"
     height="1080"
     loading="lazy">
```

## Quality Guidelines by Content Type

### Photography
- **Format**: AVIF > WebP > JPEG
- **Quality**: 85-90%
- **Resize Filter**: Lanczos
- **Color Space**: sRGB
- **Chroma Subsampling**: 4:2:0

### Product Images
- **Format**: AVIF/WebP with JPEG fallback
- **Quality**: 90-95%
- **Resize Filter**: Catrom (sharp)
- **Background**: White/transparent
- **Post-processing**: Slight unsharp mask

### Graphics/Logos
- **Format**: SVG (preferred) > PNG
- **Quality**: Lossless
- **Resize Filter**: Point (for pixel art)
- **Optimization**: Minimize paths, remove metadata

### Hero/Banner Images
- **Format**: AVIF > WebP > JPEG
- **Quality**: 80-85%
- **Dimensions**: 1920x1080 minimum
- **File Size**: < 250KB target
- **Loading**: Priority high, no lazy loading

## Performance Optimization Strategies

### 1. Progressive Enhancement
```bash
# Generate progressive JPEG
magick input.jpg -interlace Plane -quality 85 output-progressive.jpg

# Generate progressive WebP
magick input.jpg -define webp:method=6 -define webp:pass=10 output-progressive.webp
```

### 2. Adaptive Quality
```bash
# Lower quality for high-DPI displays
magick input.jpg -resize 3840x -quality 70 output-2x.jpg

# Higher quality for standard displays
magick input.jpg -resize 1920x -quality 90 output-1x.jpg
```

### 3. Conditional Processing
```bash
# Only process if larger than target
if [ $(identify -format "%w" "$INPUT") -gt 1920 ]; then
  magick "$INPUT" -resize 1920x output.jpg
else
  cp "$INPUT" output.jpg
fi
```

## Automation Best Practices

### 1. Directory Watching
```bash
# Monitor directory for new images and auto-optimize
fswatch -o ./uploads | while read f; do
  for img in ./uploads/*.{jpg,png}; do
    [ -f "$img" ] && ./optimize.sh "$img"
  done
done
```

### 2. Pre-commit Hooks
```bash
# Git pre-commit hook for image optimization
#!/bin/sh
for file in $(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(jpg|jpeg|png)$'); do
  magick "$file" -quality 85 -strip "$file"
  git add "$file"
done
```

### 3. CI/CD Integration
```yaml
# GitHub Actions example
- name: Optimize Images
  run: |
    for img in $(find . -name "*.jpg" -o -name "*.png"); do
      magick "$img" -resize 1920x1920> -quality 85 -strip "$img"
    done
```

## Error Handling and Validation

### 1. File Size Validation
```bash
check_file_size() {
  local file="$1"
  local max_size="$2"
  local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file")
  
  if [ "$size" -gt "$max_size" ]; then
    echo "Warning: $file exceeds size limit ($size > $max_size)"
    return 1
  fi
  return 0
}
```

### 2. Format Support Detection
```bash
# Check if browser supports modern formats
check_format_support() {
  local format="$1"
  case "$format" in
    avif) echo "Checking AVIF support..." ;;
    webp) echo "Checking WebP support..." ;;
    *) echo "Format $format not recognized" ;;
  esac
}
```

### 3. Quality Assurance
```bash
# Compare original vs optimized
compare_quality() {
  local original="$1"
  local optimized="$2"
  
  magick compare -metric SSIM "$original" "$optimized" null: 2>&1
}
```

## Monitoring and Metrics

### Key Performance Indicators
- **File Size Reduction**: Target 50-70% reduction
- **Load Time Improvement**: Target 20-30% faster
- **Quality Score (SSIM)**: Maintain > 0.95
- **Core Web Vitals**: LCP < 2.5s, CLS < 0.1
- **Bandwidth Savings**: Track monthly reduction

### Logging Template
```bash
log_optimization() {
  local input="$1"
  local output="$2"
  local input_size=$(stat -f%z "$input")
  local output_size=$(stat -f%z "$output")
  local reduction=$((100 - (output_size * 100 / input_size)))
  
  echo "$(date): $input -> $output | Reduction: ${reduction}% | ${input_size} -> ${output_size}"
}
```

## Common Issues and Solutions

### 1. Color Shifts
**Problem**: Colors look different after optimization
**Solution**: Always convert to sRGB before stripping profiles
```bash
magick input.jpg -profile sRGB.icc -strip output.jpg
```

### 2. Blurry Images
**Problem**: Images appear soft after resizing
**Solution**: Use appropriate filter and add sharpening
```bash
magick input.jpg -filter Lanczos -resize 1920x -unsharp 0x1 output.jpg
```

### 3. Large File Sizes
**Problem**: Optimized images still too large
**Solution**: Use modern formats and aggressive compression
```bash
magick input.jpg -quality 75 -define avif:speed=0 output.avif
```

### 4. Layout Shifts
**Problem**: Images cause layout shift on load
**Solution**: Always specify dimensions
```bash
# Extract and embed dimensions
WIDTH=$(identify -format "%w" input.jpg)
HEIGHT=$(identify -format "%h" input.jpg)
echo "<img src=\"output.jpg\" width=\"$WIDTH\" height=\"$HEIGHT\" alt=\"\">"
```

## Future Considerations

### Emerging Technologies (2025+)
- **JPEG XL**: Monitor adoption, superior to JPEG in all aspects
- **HEIC/HEIF**: Consider for Apple ecosystem
- **AI-Enhanced Compression**: Integration with ML-based optimization
- **Edge Computing**: CDN-level image optimization
- **HTTP/3 and QUIC**: Optimize for new protocols

### Upcoming Standards
- **Priority Hints API**: Implement resource loading priorities
- **Container Queries**: Responsive images based on container size
- **Native Lazy Loading**: Enhanced browser implementation
- **HDR Support**: Prepare for wider HDR display adoption

## Summary

The ImageMagick Web Optimization Agent should prioritize:

1. **Modern Formats**: AVIF and WebP with JPEG fallbacks
2. **Responsive Design**: Multiple sizes for different viewports
3. **Performance**: Aggressive optimization while maintaining quality
4. **Automation**: Batch processing and CI/CD integration
5. **Monitoring**: Track metrics and continuously improve

By following these guidelines, the agent will effectively optimize images for modern web use, improving performance, user experience, and SEO while reducing bandwidth costs.