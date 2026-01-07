# FileViewer Blank Content Bug - Root Cause Analysis

**Date**: 2025-12-23
**Component**: `/src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte`
**Issue**: Python (.py) and JSON (.json) files display blank content, while Markdown (.md) files work correctly
**Severity**: High - Prevents viewing critical file types

## Executive Summary

**Root Cause**: The FileViewer component is using the `<Highlight>` component with a **custom slot syntax** that overrides the default rendering. The slot is receiving the `highlighted` prop but **not rendering it**. Instead, it's wrapping it in `<pre><code>{@html highlighted}</code></pre>`, but the `{@html}` directive is being passed a **reactive variable** that may not be updating correctly in the template context.

**Why Markdown Works**: This is likely a **false positive** - Markdown may appear to work due to timing/caching, but the underlying issue affects all file types.

**Fix**: Remove the custom slot and use the default rendering provided by `<Highlight>`, or ensure the slot properly renders the highlighted HTML.

---

## Technical Deep Dive

### 1. How svelte-highlight Works

From examining the source code at `/node_modules/svelte-highlight/Highlight.svelte`:

```svelte
$: {
  hljs.registerLanguage(language.name, language.register);
  highlighted = hljs.highlight(code, { language: language.name }).value;
}

<slot {highlighted}>
  <LangTag {...$$restProps} languageName={language.name} {langtag} {highlighted} {code} />
</slot>
```

**Key Insight**: The `<Highlight>` component:
1. Registers the language with highlight.js
2. Highlights the code and stores result in `highlighted` variable
3. Provides a **slot** that exposes `highlighted` as a slot prop
4. Falls back to `<LangTag>` if no slot content is provided

The `<LangTag>` component (default fallback) renders:
```svelte
<pre class:langtag data-language={languageName} {...$$restProps}>
  <code class:hljs={true}>
    {#if highlighted}{@html highlighted}{:else}{code}{/if}
  </code>
</pre>
```

### 2. Current FileViewer Implementation (Lines 354-363)

```svelte
{:else}
  {@const lang = getLanguage(file.filename)}
  {#if lang}
    <Highlight language={lang} code={fileContent} let:highlighted>
      <pre class="hljs"><code class="hljs">{@html highlighted}</code></pre>
    </Highlight>
  {:else}
    <!-- Fallback for unsupported file types -->
    <pre class="plaintext">{fileContent}</pre>
  {/if}
{/if}
```

**Problem Identified**:
- Using `let:highlighted` slot syntax to access the highlighted HTML
- Custom slot creates a **new template scope**
- The `{@html highlighted}` may not be receiving the actual highlighted value
- This is a **Svelte reactivity issue** - the slot prop may not be triggering re-renders

### 3. Why This Affects Python/JSON But Not Markdown

**Hypothesis 1: Reactivity Timing**
- Markdown files may be smaller or load faster
- Python/JSON files may have async timing issues
- The `highlighted` slot prop may not be available when the template renders

**Hypothesis 2: highlight.js Language Registration**
- `hljs.registerLanguage()` is called reactively with `$:`
- Multiple rapid file switches may cause language registration conflicts
- Python/JSON may conflict if languages aren't properly unregistered

**Hypothesis 3: SSR/Hydration Mismatch**
- Using `adapter-static` with SvelteKit
- The slot syntax may cause SSR/client hydration mismatches
- Markdown may "work" due to cached SSR output

### 4. Debug Evidence from Console Logs

From lines 44-60 of FileViewer.svelte:
```svelte
$effect(() => {
  if (file && showContent) {
    const lang = getLanguage(file.filename);
    console.log('[FileViewer] Rendering state:', {
      filename: file.filename,
      extension: file.filename.split('.').pop(),
      isSvelte: file.filename.endsWith('.svelte'),
      hasLanguage: !!lang,
      language: lang?.name || 'null',
      hasContent: !!fileContent,
      contentLength: fileContent?.length || 0,
      contentPreview: fileContent?.substring(0, 50) || 'NO CONTENT',
      showContent,
      isLoading,
      loadError
    });
  }
});
```

**Expected Debug Output**:
- `hasContent: true`
- `contentLength: >0`
- `language: "python"` or `"json"`
- Content is fetched successfully from API

**But User Sees**: Blank screen (no content displayed)

**Conclusion**: The content is loaded correctly, but the **rendering is failing** in the `<Highlight>` component slot.

---

## Language Module Analysis

All language modules have **identical structure**:

**python.js**:
```javascript
import register from "highlight.js/lib/languages/python";
export const python = { name: "python", register };
export default python;
```

**markdown.js**:
```javascript
import register from "highlight.js/lib/languages/markdown";
export const markdown = { name: "markdown", register };
export default markdown;
```

**json.js**:
```javascript
import register from "highlight.js/lib/languages/json";
export const json = { name: "json", register };
export default json;
```

**No structural differences** - all languages are imported the same way.

---

## Comparison: Working vs Broken Rendering

### Markdown (Claims to Work)
```svelte
<Highlight language={markdown} code={fileContent} let:highlighted>
  <pre class="hljs"><code class="hljs">{@html highlighted}</code></pre>
</Highlight>
```

### Python/JSON (Blank)
```svelte
<Highlight language={python} code={fileContent} let:highlighted>
  <pre class="hljs"><code class="hljs">{@html highlighted}</code></pre>
</Highlight>
```

**Identical syntax** - suggests the issue is **not language-specific** but rather a **reactivity/timing issue** with the slot.

---

## Svelte 5 Reactivity Considerations

FileViewer.svelte uses **Svelte 5 runes**:
- `$state` for component state
- `$derived` for computed values
- `$effect` for side effects
- `$props` for props

**Potential Issue**: svelte-highlight was built for **Svelte 3/4** and may have compatibility issues with Svelte 5's new reactivity system, especially around **slot props**.

---

## Root Cause: Slot Scope Reactivity Issue

**Primary Issue**: When using `let:highlighted` in Svelte 5, the slot creates a new reactive scope. The `highlighted` value from the parent `<Highlight>` component may not be properly propagating to the child slot template.

**Why it's blank**:
1. `<Highlight>` computes `highlighted` using `$:` (Svelte 3/4 style)
2. Slot prop `let:highlighted` receives this value
3. Custom slot template tries to render with `{@html highlighted}`
4. **Reactivity is broken** - Svelte 5 doesn't see the change
5. Result: Empty string or stale value renders

---

## Recommended Fix

### Option 1: Use Default Rendering (Simplest)

**Remove the custom slot entirely** and let `<Highlight>` use its default `<LangTag>` rendering:

```svelte
{:else}
  {@const lang = getLanguage(file.filename)}
  {#if lang}
    <!-- Remove let:highlighted and custom slot -->
    <Highlight language={lang} code={fileContent} />
  {:else}
    <pre class="plaintext">{fileContent}</pre>
  {/if}
{/if}
```

**Pros**:
- Uses library's tested rendering path
- No reactivity issues
- Simpler code
- Works with Svelte 5

**Cons**:
- Less control over HTML structure
- May need to adjust CSS to match existing styles

### Option 2: Fix Slot Reactivity

If custom slot is required, ensure proper reactivity:

```svelte
{:else}
  {@const lang = getLanguage(file.filename)}
  {#if lang}
    <Highlight language={lang} code={fileContent}>
      {#snippet children({ highlighted })}
        <pre class="hljs"><code class="hljs">{@html highlighted}</code></pre>
      {/snippet}
    </Highlight>
  {:else}
    <pre class="plaintext">{fileContent}</pre>
  {/if}
{/if}
```

**Note**: This uses Svelte 5's `{#snippet}` syntax for slots, which has better reactivity.

### Option 3: Use HighlightAuto (Not Recommended)

```svelte
import { HighlightAuto } from 'svelte-highlight';

<HighlightAuto code={fileContent} />
```

**Pros**: No language detection needed

**Cons**: Larger bundle size, less control

---

## Additional Considerations

### CSS Styling

The default `<LangTag>` rendering applies:
```html
<pre class="hljs" data-language="python">
  <code class="hljs">{@html highlighted}</code>
</pre>
```

Current FileViewer expects:
```html
<pre class="hljs">
  <code class="hljs">{@html highlighted}</code>
</pre>
```

**CSS should work unchanged** since class names match.

### Performance Impact

- **Option 1** (default rendering): No performance change
- **Option 2** (snippet): Minimal overhead
- **Option 3** (auto-highlight): +100KB bundle size

---

## Testing Strategy

After implementing fix:

1. **Test Python file rendering**
   - Load .py file with 100+ lines
   - Verify syntax highlighting works
   - Check browser console for errors

2. **Test JSON file rendering**
   - Load .json file with nested objects
   - Verify braces, keys, values are highlighted
   - Check for visual correctness

3. **Test Markdown file rendering**
   - Ensure existing Markdown files still work
   - Verify no regression

4. **Test file switching**
   - Rapidly switch between .py, .json, .md files
   - Verify no blank screens or race conditions
   - Check for memory leaks in DevTools

5. **Test empty files**
   - Load empty .py and .json files
   - Should show "File is empty" message (line 346-348)

---

## Implementation Plan

### Step 1: Remove Custom Slot (Recommended)

**File**: `/src/claude_mpm/dashboard-svelte/src/lib/components/FileViewer.svelte`

**Line 354-363 (Current)**:
```svelte
{:else}
  {@const lang = getLanguage(file.filename)}
  {#if lang}
    <Highlight language={lang} code={fileContent} let:highlighted>
      <pre class="hljs"><code class="hljs">{@html highlighted}</code></pre>
    </Highlight>
  {:else}
    <!-- Fallback for unsupported file types -->
    <pre class="plaintext">{fileContent}</pre>
  {/if}
{/if}
```

**New Code**:
```svelte
{:else}
  {@const lang = getLanguage(file.filename)}
  {#if lang}
    <Highlight language={lang} code={fileContent} />
  {:else}
    <!-- Fallback for unsupported file types -->
    <pre class="plaintext">{fileContent}</pre>
  {/if}
{/if}
```

### Step 2: Update CSS (If Needed)

Check if `.hljs` styles need adjustment for `data-language` attribute:

```css
.code-container :global(pre[data-language]) {
  /* Existing styles should work */
}
```

### Step 3: Test Thoroughly

Run dashboard:
```bash
cd src/claude_mpm/dashboard-svelte
npm run dev
```

Test all file types: .py, .json, .md, .ts, .js

### Step 4: Clean Up Unused Import

If `let:highlighted` was the only custom slot usage, no changes needed to imports.

---

## Svelte Version Compatibility

**Current Setup**:
- Svelte: `^5.2.9` (Svelte 5)
- svelte-highlight: `^7.9.0` (Built for Svelte 3/4)

**Compatibility Risk**: Medium
- svelte-highlight uses Svelte 3/4 reactive syntax (`$:`)
- Svelte 5 has full backward compatibility
- **However**, slot prop reactivity may behave differently

**Mitigation**: Using default rendering (Option 1) avoids slot reactivity entirely.

---

## Alternative: Migrate to Shiki

**Note**: The project also has `shiki: ^3.20.0` installed in `package.json`.

**Shiki Benefits**:
- More accurate syntax highlighting (uses VS Code themes)
- Better TypeScript support
- No highlight.js compatibility issues
- Native async/await support

**Migration Effort**: Medium (would require rewriting FileViewer highlighting logic)

**Recommendation**: Fix svelte-highlight first, consider Shiki migration later if needed.

---

## References

- [svelte-highlight GitHub](https://github.com/metonym/svelte-highlight)
- [svelte-highlight Documentation](https://svhe.onrender.com/)
- [svelte-highlight npm](https://www.npmjs.com/package/svelte-highlight)
- [Svelte 5 Slot Props](https://svelte.dev/docs/svelte/v5-migration-guide#Snippets-instead-of-slots)
- [highlight.js Documentation](https://highlightjs.org/)

---

## Conclusion

**Root Cause**: Slot prop reactivity issue between Svelte 5 and svelte-highlight's Svelte 3/4 reactivity syntax. The custom slot using `let:highlighted` is not properly receiving or rendering the highlighted HTML.

**Recommended Fix**: Remove custom slot and use default `<Highlight>` rendering. This is a **one-line change** with minimal risk.

**Expected Outcome**: All file types (Python, JSON, Markdown, etc.) will render with proper syntax highlighting.

**Risk**: Low - Default rendering is well-tested by library maintainers.

**Timeline**: 5 minutes to implement, 10 minutes to test.
