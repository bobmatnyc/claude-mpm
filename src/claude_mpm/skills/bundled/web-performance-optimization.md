---
skill_id: web-performance-optimization
skill_version: 0.1.0
description: Comprehensive guide to optimizing web performance using Lighthouse metrics and Core Web Vitals, covering modern optimization techniques and measurement strategies.
updated_at: 2025-10-30T17:00:00Z
tags: [performance, optimization, lighthouse, core-web-vitals, frontend]
---

# Web Performance Optimization

## Overview

Comprehensive guide to optimizing web performance using Lighthouse metrics and Core Web Vitals (updated for 2024-2025). This skill covers modern performance optimization techniques, measurement strategies, and framework-specific optimizations to deliver fast, responsive user experiences.

Web performance directly impacts user experience, conversions, and SEO rankings. Studies show that a 1-second delay can result in 7% conversion loss, while 0.1s improvements can increase conversions by 8%. This guide provides actionable strategies to optimize every aspect of web performance.

## When to Use This Skill

- Auditing website performance metrics
- Improving Lighthouse scores and Core Web Vitals
- Optimizing page load times and interactivity
- Reducing resource sizes and improving caching
- Enhancing SEO rankings through performance signals
- Improving user experience and conversion rates
- Debugging performance bottlenecks
- Setting up performance monitoring and budgets
- Implementing modern performance patterns (streaming SSR, islands architecture)

## Core Web Vitals (2024-2025)

Core Web Vitals are Google's essential metrics for measuring user experience. These metrics are ranking factors for SEO and directly correlate with user satisfaction and conversions.

### LCP (Largest Contentful Paint)

**Target:** ≤2.5 seconds (Good), 2.5-4.0s (Needs Improvement), >4.0s (Poor)

**What it Measures:** Time until the largest content element (image, video, or text block) becomes visible in the viewport. For 73% of sites, LCP is caused by images.

**Optimization Strategies:**

#### 1. Image Optimization
```html
<!-- Use modern formats with fallbacks -->
<picture>
  <source srcset="hero.avif" type="image/avif">
  <source srcset="hero.webp" type="image/webp">
  <img src="hero.jpg" alt="Hero image" fetchpriority="high">
</picture>

<!-- Responsive images with srcset -->
<img
  srcset="hero-400.webp 400w, hero-800.webp 800w, hero-1200.webp 1200w"
  sizes="(max-width: 600px) 400px, (max-width: 1200px) 800px, 1200px"
  src="hero-800.webp"
  alt="Hero image"
  fetchpriority="high"
>
```

#### 2. Preload Critical Resources
```html
<!-- Preload LCP image -->
<link rel="preload" as="image" href="hero.webp" fetchpriority="high">

<!-- Preload critical fonts -->
<link rel="preload" as="font" type="font/woff2" href="/fonts/main.woff2" crossorigin>
```

#### 3. Server-Side Optimizations
```nginx
# Enable 103 Early Hints (25-37% improvement)
# Nginx configuration
add_header Link "</css/critical.css>; rel=preload; as=style" always;
add_header Link "</fonts/main.woff2>; rel=preload; as=font; crossorigin" always;
```

#### 4. CDN and Image Services
```javascript
// Cloudinary automatic optimization
const imageUrl = cloudinary.url('sample.jpg', {
  fetch_format: 'auto',  // Automatically choose WebP/AVIF
  quality: 'auto',       // Optimize quality
  width: 800,
  crop: 'scale'
});
```

#### 5. Lazy Loading (Non-LCP Images Only)
```html
<!-- DO NOT lazy load LCP images -->
<img src="hero.webp" alt="Hero" fetchpriority="high">

<!-- DO lazy load below-the-fold images -->
<img src="content.webp" alt="Content" loading="lazy">
```

### INP (Interaction to Next Paint) - NEW March 2024

**Target:** ≤200ms (Good), 200-500ms (Needs Improvement), >500ms (Poor)

**What it Measures:** Responsiveness to user interactions (clicks, taps, keyboard input). INP replaced FID (First Input Delay) as a Core Web Vital in March 2024, providing a more comprehensive measure of interaction responsiveness throughout the page lifecycle.

**Optimization Strategies:**

#### 1. Reduce Long Tasks
```javascript
// BAD: Long blocking task
function processLargeDataset(data) {
  data.forEach(item => heavyComputation(item));
}

// GOOD: Break into smaller tasks with yielding
async function processLargeDataset(data) {
  for (let i = 0; i < data.length; i++) {
    heavyComputation(data[i]);

    // Yield to main thread every 50ms
    if (i % 100 === 0) {
      await new Promise(resolve => setTimeout(resolve, 0));
    }
  }
}

// BETTER: Use scheduler.yield() (when available)
async function processLargeDataset(data) {
  for (let i = 0; i < data.length; i++) {
    heavyComputation(data[i]);

    if (i % 100 === 0 && 'scheduler' in window) {
      await scheduler.yield();
    }
  }
}
```

#### 2. Debounce Input Handlers
```javascript
// Debounce expensive operations
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Usage
const handleSearch = debounce((query) => {
  fetchSearchResults(query);
}, 300);

input.addEventListener('input', (e) => handleSearch(e.target.value));
```

#### 3. Use Web Workers for Heavy Computations
```javascript
// main.js
const worker = new Worker('worker.js');

button.addEventListener('click', () => {
  worker.postMessage({ data: largeDataset });
});

worker.onmessage = (e) => {
  updateUI(e.data.result);
};

// worker.js
self.onmessage = (e) => {
  const result = heavyComputation(e.data);
  self.postMessage({ result });
};
```

#### 4. Optimize React Event Handlers
```javascript
// BAD: Creating new function on every render
function SearchComponent() {
  return <input onChange={(e) => handleChange(e.target.value)} />;
}

// GOOD: Memoized callback
function SearchComponent() {
  const handleChange = useCallback((e) => {
    // Handle change
  }, []);

  return <input onChange={handleChange} />;
}
```

#### 5. CSS Containment for Faster Rendering
```css
/* Isolate rendering work to specific containers */
.card {
  contain: layout style paint;
}

.list-item {
  content-visibility: auto;
  contain-intrinsic-size: 0 200px;
}
```

### CLS (Cumulative Layout Shift)

**Target:** ≤0.1 (Good), 0.1-0.25 (Needs Improvement), >0.25 (Poor)

**What it Measures:** Visual stability - unexpected layout shifts during page load and user interaction.

**Optimization Strategies:**

#### 1. Reserve Space for Images and Embeds
```html
<!-- Always include width and height attributes -->
<img src="photo.jpg" alt="Photo" width="800" height="600">

<!-- CSS aspect ratio (modern) -->
<style>
  .image-container {
    aspect-ratio: 16 / 9;
    width: 100%;
  }

  .image-container img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
</style>
```

#### 2. Reserve Space for Dynamic Content
```css
/* Reserve minimum height for dynamic content */
.dynamic-content {
  min-height: 400px;
}

/* Skeleton screens */
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

#### 3. Avoid Inserting Content Above Existing Content
```javascript
// BAD: Prepending content causes shift
container.innerHTML = newContent + container.innerHTML;

// GOOD: Append or use proper animations
container.insertAdjacentHTML('beforeend', newContent);

// BETTER: Animate new content in
container.style.transform = 'translateY(100px)';
container.innerHTML = newContent;
requestAnimationFrame(() => {
  container.style.transform = 'translateY(0)';
  container.style.transition = 'transform 0.3s';
});
```

#### 4. Font Loading Optimization
```html
<!-- Preload critical fonts -->
<link rel="preload" as="font" type="font/woff2" href="/fonts/main.woff2" crossorigin>

<style>
  /* font-display: swap prevents invisible text but may cause shift */
  /* font-display: optional is better for CLS */
  @font-face {
    font-family: 'Main Font';
    src: url('/fonts/main.woff2') format('woff2');
    font-display: optional;
  }

  /* Fallback font metrics matching */
  body {
    font-family: 'Main Font', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
  }
</style>
```

#### 5. Ad and Embed Containers
```html
<!-- Reserve space for ads -->
<div class="ad-container" style="min-height: 250px;">
  <!-- Ad loads here -->
</div>

<!-- YouTube embed with aspect ratio -->
<div style="aspect-ratio: 16/9; width: 100%;">
  <iframe
    src="https://www.youtube.com/embed/VIDEO_ID"
    style="width: 100%; height: 100%;"
    loading="lazy"
  ></iframe>
</div>
```

### Supporting Metrics

#### FCP (First Contentful Paint)

**Target:** <1.8 seconds (Good), 1.8-3.0s (Needs Improvement), >3.0s (Poor)

**What it Measures:** Time until the first text or image is painted.

**Optimization:**
- Minimize render-blocking resources (CSS, JS)
- Use critical CSS inline in `<head>`
- Defer non-critical JavaScript
- Optimize server response times (TTFB)

```html
<!-- Inline critical CSS -->
<style>
  /* Above-the-fold styles */
  body { margin: 0; font-family: system-ui; }
  .hero { height: 100vh; }
</style>

<!-- Defer non-critical CSS -->
<link rel="preload" as="style" href="main.css" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="main.css"></noscript>
```

#### TTFB (Time to First Byte)

**Target:** <800ms (Good), 800-1800ms (Needs Improvement), >1800ms (Poor)

**What it Measures:** Server response time.

**Optimization:**
- Use CDN edge caching
- Enable server-side caching (Redis, Memcached)
- Optimize database queries
- Enable HTTP/2 or HTTP/3
- Use 103 Early Hints

#### TBT (Total Blocking Time)

**Weight:** 30% (highest in Lighthouse v12)

**Target:** <200ms (Good), 200-600ms (Needs Improvement), >600ms (Poor)

**What it Measures:** Total time the main thread was blocked by long tasks (>50ms).

**Optimization:**
- Code splitting to reduce JavaScript execution time
- Defer non-critical JavaScript
- Break up long tasks
- Remove unused code
- Optimize third-party scripts

## Lighthouse Scoring (v12 - August 2024)

### Performance Score Weights

Lighthouse v12 (released August 2024) updated performance scoring weights:

- **Total Blocking Time (TBT):** 30% - HIGHEST WEIGHT
- **Largest Contentful Paint (LCP):** 25%
- **Cumulative Layout Shift (CLS):** 25%
- **First Contentful Paint (FCP):** 10%
- **Speed Index:** 10%

### Scoring Calculation

Each metric has a curve that maps raw values to scores (0-100):

```javascript
// Example scoring curve (simplified)
function calculateScore(metrics) {
  const weights = {
    TBT: 0.30,
    LCP: 0.25,
    CLS: 0.25,
    FCP: 0.10,
    SI: 0.10
  };

  // Each metric is scored on a curve
  const scores = {
    TBT: scoreFromValue(metrics.TBT, TBT_CURVE),
    LCP: scoreFromValue(metrics.LCP, LCP_CURVE),
    CLS: scoreFromValue(metrics.CLS, CLS_CURVE),
    FCP: scoreFromValue(metrics.FCP, FCP_CURVE),
    SI: scoreFromValue(metrics.SI, SI_CURVE)
  };

  // Weighted average
  return Object.keys(weights).reduce((total, metric) => {
    return total + (scores[metric] * weights[metric]);
  }, 0);
}
```

### Running Lighthouse

```bash
# CLI audit
lighthouse https://example.com --view --output html --output-path ./report.html

# With specific categories
lighthouse https://example.com --only-categories=performance

# Mobile simulation (default)
lighthouse https://example.com --preset=mobile

# Desktop audit
lighthouse https://example.com --preset=desktop

# CI/CD integration
lighthouse https://example.com --output=json --output-path=./lighthouse.json
```

## Image Optimization

Images account for 73% of LCP elements and are the largest contributor to page weight. Modern image optimization is essential for performance.

### Modern Formats

**WebP/AVIF:** 96% browser support (2024)

```html
<!-- Progressive enhancement with multiple formats -->
<picture>
  <source srcset="image.avif" type="image/avif">
  <source srcset="image.webp" type="image/webp">
  <img src="image.jpg" alt="Description" width="800" height="600">
</picture>
```

**Format Comparison:**
- AVIF: 50% smaller than JPEG, excellent quality
- WebP: 30% smaller than JPEG, great browser support
- JPEG: Universal support, baseline format

### Responsive Images

```html
<!-- Density descriptors for different screen densities -->
<img
  srcset="image-1x.jpg 1x, image-2x.jpg 2x, image-3x.jpg 3x"
  src="image-1x.jpg"
  alt="Description"
>

<!-- Width descriptors with sizes attribute -->
<img
  srcset="
    image-400.jpg 400w,
    image-800.jpg 800w,
    image-1200.jpg 1200w,
    image-1600.jpg 1600w
  "
  sizes="
    (max-width: 600px) 100vw,
    (max-width: 1200px) 50vw,
    800px
  "
  src="image-800.jpg"
  alt="Description"
>

<!-- Art direction with picture element -->
<picture>
  <source media="(min-width: 1200px)" srcset="hero-wide.jpg">
  <source media="(min-width: 600px)" srcset="hero-medium.jpg">
  <img src="hero-small.jpg" alt="Hero image">
</picture>
```

### Lazy Loading

```html
<!-- Native lazy loading (DO NOT use on LCP images) -->
<img src="image.jpg" loading="lazy" alt="Below fold image">

<!-- Eager loading for above-fold images -->
<img src="hero.jpg" loading="eager" fetchpriority="high" alt="Hero">
```

**JavaScript lazy loading with Intersection Observer:**

```javascript
const imageObserver = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const img = entry.target;
      img.src = img.dataset.src;
      img.classList.remove('lazy');
      observer.unobserve(img);
    }
  });
});

document.querySelectorAll('img.lazy').forEach(img => {
  imageObserver.observe(img);
});
```

### Image CDN Strategies

**Cloudinary:**
```javascript
// Automatic format and quality optimization
const url = cloudinary.url('sample.jpg', {
  fetch_format: 'auto',
  quality: 'auto',
  width: 800,
  crop: 'scale',
  dpr: 'auto'  // Automatically handle device pixel ratio
});
```

**Imgix:**
```javascript
// Dynamic image transformation
const imgixUrl = `https://domain.imgix.net/image.jpg?w=800&auto=format,compress&fit=crop`;
```

**Next.js Image Component:**
```jsx
import Image from 'next/image';

// Automatic optimization, lazy loading, and responsive images
<Image
  src="/hero.jpg"
  alt="Hero image"
  width={1200}
  height={600}
  priority  // Disable lazy loading for LCP image
  quality={85}
/>
```

## JavaScript Optimization

JavaScript is often the primary bottleneck for TBT and INP. Optimizing JavaScript delivery and execution is critical.

### Code Splitting

**Impact:** 40-60% bundle size reduction

```javascript
// React lazy loading
import React, { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <HeavyComponent />
    </Suspense>
  );
}

// Route-based code splitting
import { lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

const Home = lazy(() => import('./pages/Home'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
```

**Webpack configuration:**
```javascript
// webpack.config.js
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10
        },
        common: {
          minChunks: 2,
          name: 'common',
          priority: 5
        }
      }
    }
  }
};
```

### Tree Shaking

Remove unused code from bundles:

```javascript
// package.json
{
  "sideEffects": false  // Enable tree shaking
}

// Or specify files with side effects
{
  "sideEffects": ["*.css", "*.scss"]
}

// Import only what you need
import { debounce } from 'lodash-es';  // Good: ES modules
import debounce from 'lodash/debounce';  // Good: Individual module

import _ from 'lodash';  // Bad: Imports entire library
```

**Vite tree shaking (automatic):**
```javascript
// vite.config.js
export default {
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log']
      }
    }
  }
};
```

### Lazy Loading Modules

```javascript
// Dynamic imports
button.addEventListener('click', async () => {
  const { default: Chart } = await import('chart.js');
  const chart = new Chart(ctx, config);
});

// Preload for faster loading
const ChartPromise = import(/* webpackPrefetch: true */ 'chart.js');

button.addEventListener('click', async () => {
  const { default: Chart } = await ChartPromise;
  const chart = new Chart(ctx, config);
});
```

### Bundle Analysis

```bash
# webpack-bundle-analyzer
npm install --save-dev webpack-bundle-analyzer

# Add to webpack config
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

module.exports = {
  plugins: [
    new BundleAnalyzerPlugin()
  ]
};

# Run build
npm run build
```

**Vite bundle analysis:**
```bash
# Install rollup-plugin-visualizer
npm install --save-dev rollup-plugin-visualizer

# vite.config.js
import { visualizer } from 'rollup-plugin-visualizer';

export default {
  plugins: [
    visualizer({
      open: true,
      gzipSize: true,
      brotliSize: true
    })
  ]
};
```

### Third-Party Scripts

**Problem:** 90%+ sites affected by third-party bloat

**Strategies:**

```html
<!-- 1. Defer non-critical scripts -->
<script src="analytics.js" defer></script>

<!-- 2. Use async for independent scripts -->
<script src="tracking.js" async></script>

<!-- 3. Lazy load based on user interaction -->
<script>
  let analyticsLoaded = false;

  function loadAnalytics() {
    if (analyticsLoaded) return;
    analyticsLoaded = true;

    const script = document.createElement('script');
    script.src = 'https://analytics.example.com/script.js';
    document.head.appendChild(script);
  }

  // Load on first interaction
  ['click', 'scroll', 'keydown'].forEach(event => {
    window.addEventListener(event, loadAnalytics, { once: true });
  });

  // Fallback: load after 5 seconds
  setTimeout(loadAnalytics, 5000);
</script>

<!-- 4. Use facade pattern for heavy embeds -->
<div class="youtube-facade" data-video-id="VIDEO_ID">
  <button class="play-button">Play Video</button>
</div>

<script>
  document.querySelectorAll('.youtube-facade').forEach(facade => {
    facade.addEventListener('click', function() {
      const iframe = document.createElement('iframe');
      iframe.src = `https://www.youtube.com/embed/${this.dataset.videoId}?autoplay=1`;
      iframe.allow = 'autoplay';
      this.replaceWith(iframe);
    });
  });
</script>
```

**Partytown for web workers:**
```html
<!-- Move third-party scripts to web worker -->
<script type="text/partytown" src="analytics.js"></script>
<script type="text/partytown">
  // This runs in a web worker
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

## CSS Optimization

### Critical CSS Extraction

Extract and inline above-the-fold CSS:

```bash
# Using Critical package
npm install --save-dev critical

# Generate critical CSS
npx critical https://example.com --inline --minify
```

```javascript
// Build script with critical CSS
const critical = require('critical');

critical.generate({
  inline: true,
  base: 'dist/',
  src: 'index.html',
  target: {
    html: 'index-critical.html',
    css: 'critical.css'
  },
  dimensions: [
    { width: 375, height: 667 },   // Mobile
    { width: 1920, height: 1080 }  // Desktop
  ]
});
```

### Unused CSS Removal

**Impact:** 80-90% reduction with PurgeCSS

```javascript
// PostCSS with PurgeCSS
// postcss.config.js
module.exports = {
  plugins: [
    require('@fullhuman/postcss-purgecss')({
      content: ['./src/**/*.html', './src/**/*.js', './src/**/*.jsx'],
      defaultExtractor: content => content.match(/[\w-/:]+(?<!:)/g) || [],
      safelist: ['active', 'disabled', /^data-/]  // Preserve dynamic classes
    })
  ]
};
```

**Tailwind CSS automatic purging:**
```javascript
// tailwind.config.js
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx,html}',
    './public/index.html'
  ],
  theme: {
    extend: {}
  }
};
```

### Modern CSS Features

```css
/* Container queries for responsive components */
.card-container {
  container-type: inline-size;
}

@container (min-width: 400px) {
  .card {
    display: grid;
    grid-template-columns: 1fr 2fr;
  }
}

/* :has() for parent selection */
.article:has(img) {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

/* CSS containment for performance */
.card {
  contain: layout style paint;
}

.list-item {
  content-visibility: auto;
  contain-intrinsic-size: 0 200px;
}

/* Native CSS nesting */
.component {
  padding: 1rem;

  & .title {
    font-size: 1.5rem;
  }

  &:hover {
    background: #f0f0f0;
  }
}
```

## Resource Loading Optimization

### Resource Hints

```html
<!-- Preconnect: Establish early connections to critical third-party origins -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://cdn.example.com">

<!-- DNS-prefetch: Resolve DNS only (lighter than preconnect) -->
<link rel="dns-prefetch" href="https://analytics.example.com">

<!-- Preload: Fetch critical resources early -->
<link rel="preload" as="image" href="hero.webp" fetchpriority="high">
<link rel="preload" as="font" type="font/woff2" href="main.woff2" crossorigin>
<link rel="preload" as="script" href="critical.js">
<link rel="preload" as="style" href="critical.css">

<!-- Prefetch: Fetch resources for next navigation (low priority) -->
<link rel="prefetch" as="document" href="/next-page.html">
<link rel="prefetch" as="script" href="next-page.js">

<!-- Modulepreload: Preload ES modules -->
<link rel="modulepreload" href="app.js">
```

### Priority Hints API

```html
<!-- High priority for critical images -->
<img src="hero.jpg" fetchpriority="high" alt="Hero">

<!-- Low priority for below-fold images -->
<img src="footer-logo.jpg" fetchpriority="low" alt="Logo">

<!-- Script prioritization -->
<script src="critical.js" fetchpriority="high"></script>
<script src="analytics.js" fetchpriority="low" async></script>
```

### 103 Early Hints

**Impact:** 25-37% improvement in page load times

**Server configuration (Nginx):**
```nginx
location / {
  add_header Link "</css/critical.css>; rel=preload; as=style" always;
  add_header Link "</js/main.js>; rel=preload; as=script" always;
  add_header Link "</fonts/main.woff2>; rel=preload; as=font; crossorigin" always;

  # Return 103 Early Hints
  return 103;
}
```

**Node.js/Express:**
```javascript
app.use((req, res, next) => {
  res.writeProcessing();  // 103 Early Hints
  res.setHeader('Link', [
    '</css/critical.css>; rel=preload; as=style',
    '</js/main.js>; rel=preload; as=script',
    '</fonts/main.woff2>; rel=preload; as=font; crossorigin'
  ].join(', '));
  next();
});
```

### HTTP/2 and HTTP/3

**Benefits:**
- Multiplexing: Multiple requests over single connection
- Header compression (HPACK)
- Server push (HTTP/2)
- Improved reliability over UDP (HTTP/3 with QUIC)

**Enable in Nginx:**
```nginx
server {
  listen 443 ssl http2;
  listen 443 http3 reuseport;  # HTTP/3

  add_header Alt-Svc 'h3=":443"; ma=86400';  # Advertise HTTP/3

  ssl_certificate /path/to/cert.pem;
  ssl_certificate_key /path/to/key.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
}
```

## Caching Strategies

### Cache-Control Headers

```nginx
# Nginx configuration
location ~* \.(jpg|jpeg|png|gif|webp|avif)$ {
  expires 1y;
  add_header Cache-Control "public, immutable";
}

location ~* \.(css|js)$ {
  expires 1y;
  add_header Cache-Control "public, immutable";
}

location ~* \.(html)$ {
  expires -1;
  add_header Cache-Control "no-cache, must-revalidate";
}

# Stale-while-revalidate for API responses
location /api/ {
  add_header Cache-Control "max-age=60, stale-while-revalidate=600";
}
```

**Express.js:**
```javascript
// Static assets with long cache
app.use('/static', express.static('public', {
  maxAge: '1y',
  immutable: true
}));

// API with stale-while-revalidate
app.get('/api/data', (req, res) => {
  res.set('Cache-Control', 'max-age=60, stale-while-revalidate=600');
  res.json(data);
});
```

### Service Workers

```javascript
// sw.js - Service worker with Workbox
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { ExpirationPlugin } from 'workbox-expiration';

// Precache static assets
precacheAndRoute(self.__WB_MANIFEST);

// Cache images with CacheFirst strategy
registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({
    cacheName: 'images',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 60,
        maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
      }),
    ],
  })
);

// Cache API requests with NetworkFirst
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 50,
        maxAgeSeconds: 5 * 60, // 5 minutes
      }),
    ],
  })
);

// Cache CSS/JS with StaleWhileRevalidate
registerRoute(
  ({ request }) => request.destination === 'script' || request.destination === 'style',
  new StaleWhileRevalidate({
    cacheName: 'static-resources',
  })
);
```

### CDN Edge Caching

**Cloudflare configuration:**
```javascript
// Cloudflare Worker for edge caching
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const cache = caches.default;
  let response = await cache.match(request);

  if (!response) {
    response = await fetch(request);

    // Cache for 1 hour if successful
    if (response.ok) {
      const headers = new Headers(response.headers);
      headers.set('Cache-Control', 'public, max-age=3600');
      response = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers
      });
      event.waitUntil(cache.put(request, response.clone()));
    }
  }

  return response;
}
```

## Framework-Specific Optimizations

### Next.js

```jsx
// next.config.js
module.exports = {
  // Image optimization
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },

  // Font optimization
  optimizeFonts: true,

  // Script optimization
  swcMinify: true,

  // Compression
  compress: true,

  // Generate static pages
  output: 'standalone',
};

// Using Next.js Image component
import Image from 'next/image';

export default function Hero() {
  return (
    <Image
      src="/hero.jpg"
      alt="Hero image"
      width={1200}
      height={600}
      priority  // Preload LCP image
      quality={85}
    />
  );
}

// Font optimization with next/font
import { Inter } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter'
});

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}

// Static generation for performance
export async function generateStaticParams() {
  const posts = await getPosts();
  return posts.map(post => ({ slug: post.slug }));
}

// Streaming SSR with Suspense
import { Suspense } from 'react';

export default function Page() {
  return (
    <>
      <Header />
      <Suspense fallback={<Skeleton />}>
        <DynamicContent />
      </Suspense>
      <Footer />
    </>
  );
}
```

### React

```jsx
// Component memoization
import { memo, useMemo, useCallback } from 'react';

const ExpensiveComponent = memo(({ data }) => {
  const processedData = useMemo(() => {
    return data.map(item => expensiveOperation(item));
  }, [data]);

  const handleClick = useCallback(() => {
    // Handle click
  }, []);

  return <div onClick={handleClick}>{processedData}</div>;
});

// Code splitting with React.lazy
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./Dashboard'));
const Settings = lazy(() => import('./Settings'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  );
}

// Virtual scrolling for large lists
import { FixedSizeList } from 'react-window';

function VirtualList({ items }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={items.length}
      itemSize={80}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>{items[index].name}</div>
      )}
    </FixedSizeList>
  );
}

// React 18 transitions for better INP
import { useTransition } from 'react';

function SearchComponent() {
  const [isPending, startTransition] = useTransition();
  const [query, setQuery] = useState('');

  const handleSearch = (e) => {
    const value = e.target.value;
    setQuery(value);

    startTransition(() => {
      // This update is marked as non-urgent
      setSearchResults(performExpensiveSearch(value));
    });
  };

  return (
    <>
      <input value={query} onChange={handleSearch} />
      {isPending && <Spinner />}
      <Results />
    </>
  );
}
```

### Vue

```vue
<!-- Async components -->
<script>
import { defineAsyncComponent } from 'vue';

export default {
  components: {
    HeavyComponent: defineAsyncComponent(() =>
      import('./HeavyComponent.vue')
    )
  }
};
</script>

<!-- Keep-alive for component caching -->
<template>
  <keep-alive :max="10">
    <component :is="currentView" />
  </keep-alive>
</template>

<!-- Virtual scrolling -->
<script setup>
import { VirtualScroller } from 'vue-virtual-scroller';

const items = ref([/* thousands of items */]);
</script>

<template>
  <VirtualScroller
    :items="items"
    :item-height="80"
    key-field="id"
  >
    <template #default="{ item }">
      <div>{{ item.name }}</div>
    </template>
  </VirtualScroller>
</template>

<!-- Vue 3 performance optimizations -->
<script setup>
import { computed, watchEffect } from 'vue';

// Computed values are cached
const filteredItems = computed(() => {
  return items.value.filter(item => item.active);
});

// Use v-memo for expensive renders
</script>

<template>
  <div v-for="item in list" :key="item.id" v-memo="[item.id, item.selected]">
    <ExpensiveComponent :item="item" />
  </div>
</template>
```

### Vite

```javascript
// vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    // Manual chunk splitting (70% faster builds)
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['react', 'react-dom'],
          'ui': ['@mui/material', '@mui/icons-material'],
          'utils': ['lodash-es', 'date-fns']
        }
      }
    },

    // Minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },

    // CSS code splitting
    cssCodeSplit: true,

    // Source maps only for development
    sourcemap: process.env.NODE_ENV === 'development'
  },

  // Dependency pre-bundling
  optimizeDeps: {
    include: ['react', 'react-dom', 'lodash-es']
  },

  // Development optimizations
  server: {
    hmr: {
      overlay: true
    }
  }
});
```

## Modern Performance Patterns (2024)

### Streaming SSR

```jsx
// React 18 streaming with Suspense
import { Suspense } from 'react';
import { renderToReadableStream } from 'react-dom/server';

async function handler(req, res) {
  const stream = await renderToReadableStream(
    <App />,
    {
      onError(error) {
        console.error(error);
      }
    }
  );

  res.setHeader('Content-Type', 'text/html');
  stream.pipeTo(new WritableStream({
    write(chunk) {
      res.write(chunk);
    },
    close() {
      res.end();
    }
  }));
}

// Component with streaming
function App() {
  return (
    <html>
      <body>
        <Header />
        <Suspense fallback={<Spinner />}>
          <Comments />  {/* Streams in when ready */}
        </Suspense>
        <Footer />
      </body>
    </html>
  );
}
```

### Islands Architecture

**Astro example:**
```astro
---
// Static content by default
import Header from '../components/Header.astro';
import InteractiveWidget from '../components/InteractiveWidget.jsx';
---

<html>
  <body>
    <Header />

    <!-- Static content -->
    <article>
      <h1>Blog Post</h1>
      <p>Static content...</p>
    </article>

    <!-- Interactive island: only this hydrates -->
    <InteractiveWidget client:visible />

    <footer>Static footer</footer>
  </body>
</html>
```

**Hydration strategies:**
```astro
<!-- Load immediately -->
<Component client:load />

<!-- Load when idle -->
<Component client:idle />

<!-- Load when visible -->
<Component client:visible />

<!-- Load on media query -->
<Component client:media="(max-width: 768px)" />

<!-- Only render server-side (no JS) -->
<Component />
```

### Progressive Hydration

```jsx
// Progressive hydration with react-lazy-hydration
import { LazyHydrate } from 'react-lazy-hydration';

function App() {
  return (
    <>
      <Header />

      {/* Hydrate immediately */}
      <HeroSection />

      {/* Hydrate when visible */}
      <LazyHydrate whenVisible>
        <CommentsSection />
      </LazyHydrate>

      {/* Hydrate when idle */}
      <LazyHydrate whenIdle>
        <RelatedArticles />
      </LazyHydrate>

      {/* Hydrate on interaction */}
      <LazyHydrate on:click>
        <ShareButtons />
      </LazyHydrate>
    </>
  );
}
```

## Performance Monitoring

### Lighthouse CI

```yaml
# .github/workflows/lighthouse.yml
name: Lighthouse CI
on: [push, pull_request]

jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: npm ci
      - name: Build
        run: npm run build
      - name: Run Lighthouse CI
        uses: treosh/lighthouse-ci-action@v10
        with:
          urls: |
            http://localhost:3000
            http://localhost:3000/about
          uploadArtifacts: true
          temporaryPublicStorage: true
```

**lighthouserc.json:**
```json
{
  "ci": {
    "collect": {
      "numberOfRuns": 3,
      "startServerCommand": "npm run serve",
      "url": ["http://localhost:3000/"]
    },
    "assert": {
      "assertions": {
        "categories:performance": ["error", {"minScore": 0.9}],
        "categories:accessibility": ["error", {"minScore": 0.9}],
        "first-contentful-paint": ["error", {"maxNumericValue": 2000}],
        "largest-contentful-paint": ["error", {"maxNumericValue": 2500}],
        "cumulative-layout-shift": ["error", {"maxNumericValue": 0.1}],
        "total-blocking-time": ["error", {"maxNumericValue": 300}]
      }
    },
    "upload": {
      "target": "temporary-public-storage"
    }
  }
}
```

### Performance Budgets

```json
// budget.json
[
  {
    "resourceSizes": [
      {
        "resourceType": "document",
        "budget": 50
      },
      {
        "resourceType": "script",
        "budget": 300
      },
      {
        "resourceType": "stylesheet",
        "budget": 50
      },
      {
        "resourceType": "image",
        "budget": 500
      },
      {
        "resourceType": "font",
        "budget": 100
      },
      {
        "resourceType": "total",
        "budget": 1000
      }
    ],
    "resourceCounts": [
      {
        "resourceType": "third-party",
        "budget": 10
      }
    ]
  }
]
```

**Webpack bundle size budget:**
```javascript
// webpack.config.js
module.exports = {
  performance: {
    maxAssetSize: 300000,  // 300KB
    maxEntrypointSize: 500000,  // 500KB
    hints: 'error'
  }
};
```

### Real User Monitoring (RUM)

```javascript
// Using web-vitals library
import { onCLS, onFCP, onINP, onLCP, onTTFB } from 'web-vitals';

function sendToAnalytics(metric) {
  const body = JSON.stringify({
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    delta: metric.delta,
    id: metric.id,
    navigationType: metric.navigationType
  });

  // Use sendBeacon for reliable delivery
  if (navigator.sendBeacon) {
    navigator.sendBeacon('/analytics', body);
  } else {
    fetch('/analytics', { body, method: 'POST', keepalive: true });
  }
}

// Measure all Core Web Vitals
onCLS(sendToAnalytics);
onFCP(sendToAnalytics);
onINP(sendToAnalytics);
onLCP(sendToAnalytics);
onTTFB(sendToAnalytics);

// Attribution for debugging
import { onLCP } from 'web-vitals/attribution';

onLCP((metric) => {
  console.log('LCP element:', metric.attribution.element);
  console.log('LCP resource:', metric.attribution.url);
  console.log('LCP time:', metric.value);
  sendToAnalytics(metric);
});
```

**RUM vs Lab Data:**
- Lab data (Lighthouse): Controlled environment, consistent results
- RUM: Real user conditions, network variability, device diversity
- Use both: Lab for development, RUM for production monitoring

### Chrome DevTools Performance Panel

**2024 updates:**
- Live Core Web Vitals overlay
- INP debugging (replaced FID)
- Enhanced flame chart
- Interaction tracking

**Workflow:**
1. Open DevTools (F12) → Performance tab
2. Click Record, interact with page, stop recording
3. Analyze:
   - Main thread activity (find long tasks)
   - Network waterfall (identify bottlenecks)
   - Core Web Vitals annotations
   - Frame rate drops
4. Use bottom-up view to identify expensive functions

## Common Performance Issues

### Issue 1: Unoptimized Images

**Impact:** 73% of sites have image LCP

**Symptoms:**
- Slow LCP (>2.5s)
- High bandwidth usage
- Large LCP element in Lighthouse

**Solution:**

1. **Convert to modern formats:**
```bash
# Using ImageMagick
magick input.jpg -quality 85 output.webp
magick input.jpg -quality 85 output.avif

# Using cwebp/cavif
cwebp -q 85 input.jpg -o output.webp
avifenc -s 5 input.jpg output.avif
```

2. **Implement responsive images:**
```html
<picture>
  <source
    srcset="hero-400.avif 400w, hero-800.avif 800w, hero-1200.avif 1200w"
    type="image/avif"
  >
  <source
    srcset="hero-400.webp 400w, hero-800.webp 800w, hero-1200.webp 1200w"
    type="image/webp"
  >
  <img
    srcset="hero-400.jpg 400w, hero-800.jpg 800w, hero-1200.jpg 1200w"
    sizes="(max-width: 600px) 400px, (max-width: 1200px) 800px, 1200px"
    src="hero-800.jpg"
    alt="Hero image"
    fetchpriority="high"
  >
</picture>
```

3. **Use image CDN:**
```javascript
// Cloudinary automatic optimization
const imageUrl = cloudinary.url('hero.jpg', {
  fetch_format: 'auto',
  quality: 'auto',
  width: 'auto',
  dpr: 'auto',
  crop: 'scale'
});
```

### Issue 2: Render-Blocking Resources

**Impact:** Delays FCP/LCP by seconds

**Symptoms:**
- "Eliminate render-blocking resources" in Lighthouse
- Long white screen time
- Delayed FCP

**Solution:**

1. **Inline critical CSS:**
```html
<head>
  <style>
    /* Critical above-the-fold CSS */
    body { margin: 0; font-family: system-ui; }
    .hero { height: 100vh; background: #f0f0f0; }
  </style>

  <!-- Defer non-critical CSS -->
  <link rel="preload" as="style" href="main.css" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="main.css"></noscript>
</head>
```

2. **Defer JavaScript:**
```html
<!-- Defer non-critical scripts -->
<script src="main.js" defer></script>

<!-- Async for independent scripts -->
<script src="analytics.js" async></script>

<!-- Module scripts are deferred by default -->
<script type="module" src="app.js"></script>
```

3. **Remove unused CSS:**
```bash
# Using PurgeCSS
npm install --save-dev @fullhuman/postcss-purgecss
```

### Issue 3: Third-Party Script Bloat

**Impact:** 90%+ sites affected, major contributor to TBT

**Symptoms:**
- High TBT (>200ms)
- "Reduce JavaScript execution time" in Lighthouse
- Slow INP

**Solution:**

1. **Audit third-party scripts:**
```javascript
// Find third-party impact in DevTools
// Coverage tab → Show third-party badges

// Performance Insights → Third-party usage
```

2. **Lazy load non-critical scripts:**
```javascript
// Load on interaction
let analyticsLoaded = false;

function loadAnalytics() {
  if (analyticsLoaded) return;
  analyticsLoaded = true;

  const script = document.createElement('script');
  script.src = 'https://analytics.example.com/script.js';
  document.head.appendChild(script);
}

['click', 'scroll', 'keydown'].forEach(event => {
  window.addEventListener(event, loadAnalytics, { once: true });
});

setTimeout(loadAnalytics, 5000);  // Fallback
```

3. **Use facades for heavy embeds:**
```javascript
// YouTube facade (save ~500KB)
class YoutubeFacade extends HTMLElement {
  connectedCallback() {
    const videoId = this.getAttribute('videoid');
    this.innerHTML = `
      <div class="facade" style="cursor: pointer;">
        <img src="https://i.ytimg.com/vi/${videoId}/hqdefault.jpg">
        <button class="play-button">▶</button>
      </div>
    `;

    this.querySelector('.facade').addEventListener('click', () => {
      this.innerHTML = `
        <iframe
          src="https://www.youtube.com/embed/${videoId}?autoplay=1"
          allow="autoplay"
          allowfullscreen
        ></iframe>
      `;
    });
  }
}

customElements.define('youtube-facade', YoutubeFacade);
```

### Issue 4: Layout Shifts

**Impact:** Poor CLS score (>0.1)

**Symptoms:**
- Content jumping during load
- "Avoid large layout shifts" in Lighthouse
- Elements moving unexpectedly

**Solution:**

1. **Reserve space for images:**
```html
<!-- Always include dimensions -->
<img src="photo.jpg" width="800" height="600" alt="Photo">

<!-- Or use aspect-ratio -->
<style>
  .image-container {
    aspect-ratio: 16 / 9;
  }
  .image-container img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
</style>
```

2. **Prevent font layout shifts:**
```css
/* Use font-display: optional for best CLS */
@font-face {
  font-family: 'Main Font';
  src: url('/fonts/main.woff2') format('woff2');
  font-display: optional;  /* Prevents FOIT and minimizes shift */
}

/* Or use fallback font metrics matching */
@font-face {
  font-family: 'Main Font Fallback';
  src: local('Arial');
  ascent-override: 95%;
  descent-override: 25%;
  line-gap-override: 0%;
  size-adjust: 100%;
}

body {
  font-family: 'Main Font', 'Main Font Fallback', sans-serif;
}
```

3. **Use skeleton screens:**
```css
.skeleton {
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e0e0e0 50%,
    #f0f0f0 75%
  );
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  min-height: 200px;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### Issue 5: Large JavaScript Bundles

**Impact:** Slow TTI, high TBT (>200ms)

**Symptoms:**
- "Reduce JavaScript execution time" in Lighthouse
- Large bundle sizes (>300KB)
- Slow initial load

**Solution:**

1. **Analyze bundle:**
```bash
# webpack-bundle-analyzer
npm install --save-dev webpack-bundle-analyzer
npm run build -- --analyze
```

2. **Code splitting:**
```javascript
// Route-based splitting
const Home = lazy(() => import('./pages/Home'));
const Dashboard = lazy(() => import('./pages/Dashboard'));

// Component-based splitting
const Chart = lazy(() => import('./components/Chart'));

// Vendor splitting
// webpack.config.js
optimization: {
  splitChunks: {
    chunks: 'all',
    cacheGroups: {
      vendor: {
        test: /[\\/]node_modules[\\/]/,
        name: 'vendors',
        priority: 10
      }
    }
  }
}
```

3. **Tree shaking:**
```javascript
// Import only what you need
import { debounce } from 'lodash-es';  // Good
import debounce from 'lodash/debounce';  // Good
import _ from 'lodash';  // Bad: imports entire library
```

### Issue 6: Poor Font Loading

**Impact:** FOIT/FOUT, layout shifts, delayed FCP

**Symptoms:**
- Invisible text during load (FOIT)
- Flash of unstyled text (FOUT)
- Layout shifts when font loads

**Solution:**

1. **Preload critical fonts:**
```html
<link rel="preload" as="font" type="font/woff2" href="/fonts/main.woff2" crossorigin>
```

2. **Optimize font-display:**
```css
@font-face {
  font-family: 'Main Font';
  src: url('/fonts/main.woff2') format('woff2');
  font-display: optional;  /* Best for CLS */
  /* font-display: swap;  Prevents FOIT but may cause shift */
}
```

3. **Subset fonts:**
```bash
# Using pyftsubset (fonttools)
pyftsubset font.ttf \
  --output-file=font-subset.woff2 \
  --flavor=woff2 \
  --unicodes="U+0020-007E"  # ASCII characters
```

4. **Use system fonts:**
```css
body {
  font-family:
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    Roboto,
    'Helvetica Neue',
    Arial,
    sans-serif;
}
```

## Performance Audit Workflow

### 1. Baseline Measurement

**Run Lighthouse:**
```bash
lighthouse https://example.com --view --output html json --output-path ./report
```

**Run WebPageTest:**
- Visit webpagetest.org
- Enter URL, select location and device
- Run test 3 times for median results

**Collect field data:**
```javascript
// Chrome User Experience Report (CrUX) via PageSpeed Insights API
const url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed';
const params = `?url=https://example.com&key=YOUR_API_KEY`;

fetch(url + params)
  .then(res => res.json())
  .then(data => {
    console.log('Field data:', data.loadingExperience.metrics);
  });
```

### 2. Identify Bottlenecks

**Priority order:**
1. LCP issues (25% weight) - Images, fonts, server response
2. TBT issues (30% weight) - JavaScript execution, long tasks
3. CLS issues (25% weight) - Images without dimensions, fonts, dynamic content
4. FCP issues (10% weight) - Render-blocking resources
5. Other metrics (10% weight)

### 3. Implement Optimizations

**High-impact changes first:**
1. Optimize LCP image (modern format, CDN, preload)
2. Reduce JavaScript (code splitting, remove unused code)
3. Fix layout shifts (reserve space, font-display)
4. Eliminate render-blocking resources (defer, async, inline critical)
5. Optimize third-party scripts (lazy load, facades)

### 4. Measure Impact

**Before/after comparison:**
```javascript
// Track metrics over time
const metrics = {
  before: {
    LCP: 3200,
    INP: 450,
    CLS: 0.18,
    TBT: 580,
    score: 62
  },
  after: {
    LCP: 2100,  // 34% improvement
    INP: 180,   // 60% improvement
    CLS: 0.05,  // 72% improvement
    TBT: 150,   // 74% improvement
    score: 94   // 52% improvement
  }
};
```

### 5. Set Up Monitoring

**Lighthouse CI:**
```yaml
# .github/workflows/lighthouse.yml
- name: Run Lighthouse CI
  uses: treosh/lighthouse-ci-action@v10
```

**Real User Monitoring:**
```javascript
import { onCLS, onFCP, onINP, onLCP } from 'web-vitals';

[onCLS, onFCP, onINP, onLCP].forEach(fn => fn(sendToAnalytics));
```

## Performance Budget Template

```json
{
  "performance": {
    "score": 90,
    "metrics": {
      "first-contentful-paint": 1800,
      "largest-contentful-paint": 2500,
      "interaction-to-next-paint": 200,
      "cumulative-layout-shift": 0.1,
      "total-blocking-time": 200,
      "speed-index": 3000
    }
  },
  "resourceSizes": {
    "document": 50,
    "script": 300,
    "stylesheet": 50,
    "image": 500,
    "font": 100,
    "total": 1000
  },
  "resourceCounts": {
    "third-party": 10,
    "total": 50
  }
}
```

## Business Impact

### Conversion Impact

- **1 second delay = 7% conversion loss** (Amazon)
- **0.1s improvement = 8% increase in conversions** (Walmart)
- **3s load time = 32% abandon rate** (Google)
- **53% mobile users abandon after 3s** (Google)
- **Page speed is a ranking factor** (Google)

**Case Studies:**

- **Pinterest:** Reduced perceived wait times by 40%, increased SEO traffic by 15%, increased sign-ups by 15%
- **Zalando:** 0.1s improvement = 0.7% increase in revenue
- **AutoAnything:** 50% faster page load = 12-13% increase in sales
- **BBC:** Lost 10% of users for every additional second of load time

### SEO Impact

- **Core Web Vitals as ranking factor** (June 2021+)
- **Page experience signals** affect rankings
- **Mobile-first indexing** prioritizes mobile performance
- **75% of users pass Core Web Vitals = ranking boost**

## Quick Reference

### Commands

```bash
# Lighthouse CLI
lighthouse https://example.com --view

# Lighthouse CI
lhci autorun

# WebPageTest CLI
webpagetest test https://example.com --key YOUR_KEY

# Chrome DevTools headless
chrome --headless --disable-gpu --screenshot https://example.com

# Image optimization
cwebp -q 85 input.jpg -o output.webp
avifenc -s 5 input.jpg output.avif

# Bundle analysis
webpack-bundle-analyzer dist/stats.json
```

### Optimization Checklist

**Images:**
- [ ] Convert to WebP/AVIF
- [ ] Implement responsive images with srcset
- [ ] Add width/height attributes
- [ ] Lazy load below-fold images
- [ ] Preload LCP image with fetchpriority="high"
- [ ] Use CDN with automatic optimization

**JavaScript:**
- [ ] Code splitting (route-based and component-based)
- [ ] Tree shaking enabled
- [ ] Remove unused code
- [ ] Defer non-critical scripts
- [ ] Lazy load third-party scripts
- [ ] Use web workers for heavy computations

**CSS:**
- [ ] Extract and inline critical CSS
- [ ] Remove unused CSS (PurgeCSS)
- [ ] Defer non-critical CSS
- [ ] Minify CSS
- [ ] Use modern CSS features (containment, content-visibility)

**Fonts:**
- [ ] Preload critical fonts
- [ ] Use font-display: optional or swap
- [ ] Subset fonts
- [ ] Consider system fonts

**Caching:**
- [ ] Set Cache-Control headers
- [ ] Implement service worker
- [ ] Use CDN edge caching
- [ ] Enable stale-while-revalidate

**Server:**
- [ ] Enable HTTP/2 or HTTP/3
- [ ] Implement 103 Early Hints
- [ ] Optimize TTFB (<800ms)
- [ ] Enable compression (Brotli/gzip)

**Monitoring:**
- [ ] Set up Lighthouse CI
- [ ] Implement Real User Monitoring
- [ ] Define performance budgets
- [ ] Set up alerting

### Tools List

**Measurement:**
- Lighthouse (CLI, DevTools, CI)
- WebPageTest
- Chrome DevTools Performance Panel
- PageSpeed Insights (includes CrUX data)

**Monitoring:**
- web-vitals library
- Lighthouse CI
- SpeedCurve
- Calibre
- Vercel Analytics
- Cloudflare Web Analytics

**Optimization:**
- ImageMagick, cwebp, avifenc (images)
- webpack-bundle-analyzer (bundle analysis)
- PurgeCSS (unused CSS)
- Critical (critical CSS extraction)
- Workbox (service workers)
- Partytown (third-party scripts in web workers)

**Testing:**
- Lighthouse
- Chrome DevTools
- WebPageTest
- GTmetrix
- Pingdom

## Anti-Patterns

### What NOT to Do

❌ **Loading all resources eagerly**
- Don't load all JavaScript upfront
- Don't load all images without lazy loading
- Don't preload everything

❌ **Ignoring image optimization**
- Don't use unoptimized JPEGs/PNGs
- Don't skip responsive images
- Don't forget width/height attributes

❌ **No caching strategy**
- Don't skip Cache-Control headers
- Don't forget service worker caching
- Don't ignore CDN caching

❌ **Blocking render with non-critical resources**
- Don't include all CSS in head without deferring
- Don't use synchronous scripts in head
- Don't skip async/defer on third-party scripts

❌ **Ignoring third-party script impact**
- Don't load analytics/ads synchronously
- Don't embed heavy widgets without facades
- Don't skip third-party script auditing

❌ **No performance monitoring**
- Don't skip Lighthouse CI
- Don't ignore Real User Monitoring
- Don't forget performance budgets

❌ **Optimizing without measurement**
- Don't optimize blindly
- Don't skip baseline measurements
- Don't forget A/B testing

❌ **Premature optimization**
- Don't optimize before profiling
- Don't add complexity without data
- Don't optimize the wrong things

## Related Skills

- **nextjs-local-dev** - Next.js-specific optimizations
- **vite-local-dev** - Vite build optimizations
- **docker-containerization** - Optimizing Docker images for performance
- **systematic-debugging** - Debugging performance issues

---

**Remember:** Performance is a feature, not an afterthought. Every millisecond counts toward user experience, conversions, and SEO. Measure, optimize, and monitor continuously.
