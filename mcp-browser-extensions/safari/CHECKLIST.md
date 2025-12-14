# Safari Extension Setup Checklist

Use this checklist to ensure successful Safari extension setup.

## ✅ Pre-Setup Requirements

- [ ] **macOS Big Sur (11.0) or later** installed
- [ ] **Xcode 13.0+** installed from Mac App Store
- [ ] **Safari 14.0+** installed (Safari 17+ recommended)
- [ ] **Apple Developer account** (free account sufficient for development)
- [ ] **MCP Browser server** installed and working with Chrome extension

## ✅ Automated Setup (Recommended)

### Step 1: Run Conversion Script
```bash
cd /Users/masa/Projects/mcp-browser
bash scripts/create-safari-extension.sh
```

- [ ] Script completed without errors
- [ ] All green checkmarks displayed
- [ ] Xcode project created in `mcp-browser-extension-safari/`

### Step 2: Open Xcode Project
```bash
open "mcp-browser-extension-safari/MCP Browser.xcodeproj"
```

- [ ] Xcode opened successfully
- [ ] Project structure visible in sidebar
- [ ] "MCP Browser" scheme selected

### Step 3: Configure Code Signing

In Xcode:
1. Click on project name in sidebar
2. Select "MCP Browser" app target
3. Go to "Signing & Capabilities" tab

- [ ] "Automatically manage signing" is checked
- [ ] Team selected (your Apple ID)
- [ ] No signing errors displayed
- [ ] Bundle identifier shows: `com.mcpbrowser.extension`

### Step 4: Build and Run

In Xcode:
- [ ] Click Run button (⌘R) or Product → Run
- [ ] Build succeeds (no errors)
- [ ] App launches and appears in Dock
- [ ] App window opens showing extension info

### Step 5: Enable in Safari

1. Open Safari
2. Go to Safari → Settings (⌘,)
3. Click "Extensions" tab

- [ ] "MCP Browser Extension" appears in list
- [ ] Extension checkbox is checked
- [ ] "Always Allow on Every Website" is selected (or configure per-site)

### Step 6: Enable Developer Mode

1. Safari → Settings → Advanced
2. Check "Show Develop menu in menu bar"
3. Develop menu appears in menu bar
4. Develop → Allow Unsigned Extensions

- [ ] "Show Develop menu" is checked
- [ ] Develop menu visible in Safari menu bar
- [ ] "Allow Unsigned Extensions" is checked

### Step 7: Test Extension

1. Navigate to any website (e.g., https://example.com)
2. Right-click → Inspect Element (or ⌘⌥I)
3. In Console tab, type: `console.log('Safari MCP test')`
4. Check your MCP server logs

- [ ] Console.log executed in Safari
- [ ] Message appeared in MCP server logs
- [ ] Extension icon shows connection status (port number badge)

## ✅ Troubleshooting

### Extension doesn't appear in Safari Extensions

If MCP Browser Extension is missing:
- [ ] Verify app is running (check Dock or menubar)
- [ ] Restart Safari completely (Quit Safari, reopen)
- [ ] Re-run the app from Xcode
- [ ] Check Console.app for errors (filter by "MCP Browser")

### WebSocket connection fails

If extension shows disconnected status:
- [ ] MCP server is running (`mcp-browser run`)
- [ ] Port 8875-8895 range is available
- [ ] No firewall blocking localhost connections
- [ ] Check Safari Web Inspector for WebSocket errors

To debug:
1. Safari → Develop → Web Extension Background Pages → MCP Browser Extension
2. Check Console for connection errors
3. Look for WebSocket connection attempts

### Code signing errors

If Xcode shows signing errors:
- [ ] Logged into Xcode with Apple ID (Xcode → Settings → Accounts)
- [ ] Team selected in project settings
- [ ] "Automatically manage signing" is enabled
- [ ] Try: Product → Clean Build Folder (⌘⇧K)

### Extension not capturing console logs

If messages aren't reaching MCP server:
- [ ] Extension is enabled in Safari Settings → Extensions
- [ ] "Allow Unsigned Extensions" is checked in Develop menu
- [ ] MCP server is running and shows port in logs
- [ ] Test with: `console.log('[MCP TEST] Hello')`

Check extension status:
1. Click extension icon in Safari toolbar
2. Verify "Connected" status
3. Note the port number
4. Click "Generate Test Message" button

## ✅ Advanced Setup

### For Distribution

If planning to distribute outside development:

- [ ] Enrolled in Apple Developer Program ($99/year)
- [ ] Created Developer ID Application certificate
- [ ] Configured App Sandbox capabilities
- [ ] Enabled hardened runtime
- [ ] Prepared for notarization

See: [docs/SAFARI_EXTENSION.md](../docs/SAFARI_EXTENSION.md) - Code Signing section

### For App Store Submission

If submitting to Mac App Store:

- [ ] App Store Connect account created
- [ ] App listing created in App Store Connect
- [ ] Screenshots prepared (required sizes)
- [ ] Privacy policy URL available
- [ ] App description and metadata ready

See: [docs/SAFARI_EXTENSION.md](../docs/SAFARI_EXTENSION.md) - Distribution section

## ✅ Verification Commands

Run these to verify setup:

```bash
# Check Xcode installation
xcode-select -p
# Expected: /Applications/Xcode.app/Contents/Developer

# Check Safari version
defaults read /Applications/Safari.app/Contents/Info CFBundleShortVersionString
# Expected: 17.x or higher recommended

# Check safari-web-extension-converter
xcrun --find safari-web-extension-converter
# Expected: Path to converter tool

# Check if Xcode project exists
ls -la mcp-browser-extension-safari/*.xcodeproj
# Expected: MCP Browser.xcodeproj directory

# Check if resources are copied
ls -la mcp-browser-extension-safari/Resources/
# Expected: manifest.json, background.js, content.js, popup.html, etc.
```

## ✅ Quick Reference

### Rebuild Extension

After making changes:
```bash
# In Xcode: Product → Clean Build Folder (⌘⇧K)
# Then: Product → Run (⌘R)
```

### View Extension Logs

```bash
# Background script console
Safari → Develop → Web Extension Background Pages → MCP Browser Extension

# Content script console
Open Web Inspector on any page (⌘⌥I)

# System logs
Console.app → search "MCP Browser"
```

### Reinstall Extension

```bash
# 1. Quit Safari completely
# 2. In Xcode: Product → Clean Build Folder
# 3. Product → Run
# 4. Re-enable in Safari Settings → Extensions
```

## ✅ Success Criteria

Your Safari extension is working correctly when:

- [x] Extension appears in Safari Settings → Extensions
- [x] Extension icon shows in Safari toolbar
- [x] Clicking icon shows popup with connection status
- [x] Status shows "Connected" with port number (8875-8895)
- [x] Test message button generates console logs
- [x] Console.log() on any page reaches MCP server
- [x] All MCP Browser features work (navigation, DOM interaction, etc.)

## 📚 Additional Resources

- **Complete Guide**: [docs/SAFARI_EXTENSION.md](../docs/SAFARI_EXTENSION.md)
- **Safari Resources README**: [README.md](README.md)
- **Apple Documentation**: [Safari Web Extensions](https://developer.apple.com/documentation/safariservices/safari_web_extensions)
- **Main MCP Browser README**: [../README.md](../README.md)

## 🆘 Getting Help

If you encounter issues:

1. **Check the comprehensive guide**: [docs/SAFARI_EXTENSION.md](../docs/SAFARI_EXTENSION.md)
2. **Review Common Issues section** in the guide
3. **Check Console.app** for system errors
4. **Use Safari Web Inspector** for extension debugging
5. **Run MCP Browser doctor**: `mcp-browser doctor`
6. **Open GitHub issue** with error details

---

**Last Updated**: 2024-12-11
**Safari Extension Version**: 2.0.8
**Compatible with**: MCP Browser 2.1.0+
