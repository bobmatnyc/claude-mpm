# Safari Extension Resources for MCP Browser

This directory contains Safari-compatible web extension resources for MCP Browser.

## Contents

- **manifest.json** - Safari-compatible Manifest V3 configuration
- **background.js** - Service worker with cross-browser API support
- **popup.html** - Extension popup UI (Safari-optimized)
- **popup.js** - Popup logic with Safari-compatible APIs

## Safari-Specific Modifications

### manifest.json

The Safari version includes:
- `browser_specific_settings` section for Safari minimum version
- `type: "module"` in background service worker definition
- Same permissions as Chrome, but Safari may require additional entitlements

### background.js

Key differences from Chrome version:
- Uses cross-browser API detection: `typeof browser !== 'undefined' ? browser : chrome`
- Handles both Chrome and Safari API namespaces
- Filters out `safari://` URLs (in addition to `chrome://`)
- All WebSocket code remains the same (Safari supports standard WebSocket API)

### popup.html & popup.js

Safari-specific changes:
- Added Safari badge indicator
- Uses cross-browser API throughout
- Better error handling for Safari's callback format
- Handles `browser.runtime.lastError` in Safari style

## How to Use These Resources

These files are automatically used by the `create-safari-extension.sh` script:

```bash
cd /Users/masa/Projects/mcp-browser
bash scripts/create-safari-extension.sh
```

The script will:
1. Create `mcp-browser-extension-safari/Resources/` directory
2. Copy these Safari-specific files
3. Copy shared files from the Chrome extension (content.js, Readability.js, icons)
4. Run Apple's converter to create the Xcode project

## Manual Installation

If you want to manually set up the Safari extension:

1. **Create Resources directory:**
   ```bash
   mkdir -p mcp-browser-extension-safari/Resources
   ```

2. **Copy Safari-specific files:**
   ```bash
   cp mcp-browser-extension-safari-resources/manifest.json mcp-browser-extension-safari/Resources/
   cp mcp-browser-extension-safari-resources/background.js mcp-browser-extension-safari/Resources/
   cp mcp-browser-extension-safari-resources/popup.html mcp-browser-extension-safari/Resources/
   cp mcp-browser-extension-safari-resources/popup.js mcp-browser-extension-safari/Resources/
   ```

3. **Copy shared files from Chrome extension:**
   ```bash
   cp mcp-browser-extension/content.js mcp-browser-extension-safari/Resources/
   cp mcp-browser-extension/Readability.js mcp-browser-extension-safari/Resources/
   cp mcp-browser-extension/icon-*.png mcp-browser-extension-safari/Resources/
   ```

4. **Run safari-web-extension-converter:**
   ```bash
   xcrun safari-web-extension-converter \
     mcp-browser-extension-safari/Resources \
     --project-location mcp-browser-extension-safari \
     --app-name "MCP Browser" \
     --bundle-identifier com.mcpbrowser.extension \
     --swift
   ```

## Compatibility Notes

### Safari Version Support

- **Safari 17+**: Full Manifest V3 support including service workers ✅
- **Safari 16**: Limited MV3 support, background pages work ⚠️
- **Safari 14-15**: Basic extension support, may need modifications ⚠️

### API Compatibility

The code uses cross-browser patterns that work in both Chrome and Safari:

```javascript
// ✅ Cross-browser API detection
const browserAPI = typeof browser !== 'undefined' ? browser : chrome;

// ✅ Promise-based APIs (Safari prefers these)
const tabs = await browserAPI.tabs.query({active: true});

// ✅ WebSocket connections (standard API)
const ws = new WebSocket('ws://localhost:8875');

// ✅ Storage API (compatible)
await browserAPI.storage.local.set({key: value});
```

### Known Limitations

1. **App Sandbox**: Safari extensions run in App Sandbox, which may restrict:
   - Network connections (requires entitlements)
   - File system access (limited)
   - Some browser APIs

2. **WebSocket Connections**: Requires "Outgoing Connections (Client)" capability in Xcode

3. **Localhost Access**: May need explicit `host_permissions` for localhost

## Testing

After building the Safari extension:

1. **Load extension in Safari:**
   - Run app from Xcode
   - Enable in Safari Settings → Extensions
   - Allow unsigned extensions (Develop menu)

2. **Test console capture:**
   - Open any webpage
   - Open Web Inspector (right-click → Inspect Element)
   - Run: `console.log('test')`
   - Check MCP server receives the message

3. **Debug background script:**
   - Safari → Develop → Web Extension Background Pages → MCP Browser Extension
   - View console logs and network activity

## Differences from Chrome Extension

| Feature | Chrome | Safari |
|---------|--------|--------|
| API Namespace | `chrome.*` | `chrome.*` or `browser.*` |
| Service Workers | Full support | Safari 17+ full support |
| WebSockets | No restrictions | Requires app capabilities |
| Installation | `.crx` or unpacked | `.app` bundle with extension |
| Distribution | Chrome Web Store | Mac App Store or Developer ID |
| Signing | Optional | Required for distribution |

## Related Documentation

- [Complete Safari Extension Guide](../docs/SAFARI_EXTENSION.md)
- [Safari Web Extensions (Apple)](https://developer.apple.com/documentation/safariservices/safari_web_extensions)
- [Converting Extensions for Safari](https://developer.apple.com/documentation/safariservices/safari_web_extensions/converting_a_web_extension_for_safari)

## Support

For Safari-specific issues:
- Check the comprehensive guide: `docs/SAFARI_EXTENSION.md`
- Apple Developer Forums: Safari Extensions section
- Open an issue on the GitHub repository
