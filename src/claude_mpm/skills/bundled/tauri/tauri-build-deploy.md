---
name: tauri-build-deploy
description: Build configuration, release optimization, code signing, updater setup, and deployment strategies for Tauri applications
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Production deployment: build optimization, code signing, auto-updater, CI/CD integration, platform-specific packaging"
    when_to_use: "Preparing Tauri apps for production release, implementing auto-updates, or setting up CI/CD pipelines"
    quick_start: "1. Configure tauri.conf.json 2. Set up code signing 3. Implement updater 4. Optimize build 5. CI/CD pipeline"
context_limit: 600
tags:
  - tauri
  - build
  - deployment
  - release
  - code-signing
  - updater
requires_tools: []
---

# Tauri Build and Deployment

## Build Configuration

### Basic tauri.conf.json Structure

```json
{
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devPath": "http://localhost:5173",
    "distDir": "../dist",
    "withGlobalTauri": false
  },
  "package": {
    "productName": "MyApp",
    "version": "1.0.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "fs": {
        "all": false,
        "readFile": true,
        "writeFile": true,
        "scope": ["$APPDATA/*"]
      }
    },
    "bundle": {
      "active": true,
      "identifier": "com.mycompany.myapp",
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ],
      "resources": ["resources/*"],
      "externalBin": [],
      "copyright": "",
      "category": "DeveloperTool",
      "shortDescription": "",
      "longDescription": "",
      "deb": {
        "depends": []
      },
      "macOS": {
        "frameworks": [],
        "minimumSystemVersion": "10.13",
        "exceptionDomain": "",
        "signingIdentity": null,
        "entitlements": null
      },
      "windows": {
        "certificateThumbprint": null,
        "digestAlgorithm": "sha256",
        "timestampUrl": ""
      }
    }
  }
}
```

### Production Build Optimization

**Cargo.toml configuration**:
```toml
[profile.release]
opt-level = "z"     # Optimize for size
lto = true          # Link-time optimization
codegen-units = 1   # Better optimization
panic = "abort"     # Smaller binary
strip = true        # Remove symbols
```

**Frontend optimization**:
```json
// vite.config.ts
export default {
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom']
        }
      }
    }
  }
}
```

## Code Signing

### macOS Code Signing

**1. Certificate Setup**:
```bash
# Import certificate to keychain
security import certificate.p12 -k ~/Library/Keychains/login.keychain

# Verify certificate
security find-identity -v -p codesigning
```

**2. Configure tauri.conf.json**:
```json
{
  "tauri": {
    "bundle": {
      "macOS": {
        "signingIdentity": "Developer ID Application: Your Name (TEAM_ID)",
        "entitlements": "src-tauri/entitlements.plist",
        "exceptionDomain": null
      }
    }
  }
}
```

**3. entitlements.plist**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
</dict>
</plist>
```

**4. Notarization**:
```bash
# Build and sign
npm run tauri build

# Create zip for notarization
ditto -c -k --keepParent "src-tauri/target/release/bundle/macos/MyApp.app" MyApp.zip

# Submit to Apple
xcrun notarytool submit MyApp.zip \
  --apple-id "your@email.com" \
  --password "app-specific-password" \
  --team-id "TEAM_ID" \
  --wait

# Staple notarization
xcrun stapler staple "src-tauri/target/release/bundle/macos/MyApp.app"
```

### Windows Code Signing

**1. Configure tauri.conf.json**:
```json
{
  "tauri": {
    "bundle": {
      "windows": {
        "certificateThumbprint": "YOUR_CERT_THUMBPRINT",
        "digestAlgorithm": "sha256",
        "timestampUrl": "http://timestamp.digicert.com"
      }
    }
  }
}
```

**2. Sign with signtool**:
```powershell
# Find certificate thumbprint
Get-ChildItem -Path Cert:\CurrentUser\My

# Sign executable
signtool sign /sha1 THUMBPRINT /tr http://timestamp.digicert.com /td sha256 /fd sha256 MyApp.exe
```

## Auto-Updater

### Backend Updater Configuration

**tauri.conf.json**:
```json
{
  "tauri": {
    "updater": {
      "active": true,
      "endpoints": [
        "https://releases.myapp.com/{{target}}/{{current_version}}"
      ],
      "dialog": true,
      "pubkey": "YOUR_PUBLIC_KEY_HERE"
    }
  }
}
```

### Generate Signing Keys

```bash
# Install Tauri CLI
cargo install tauri-cli

# Generate keypair
tauri signer generate -w ~/.tauri/myapp.key

# Output:
# Private key: ~/.tauri/myapp.key
# Public key: dW50cnVzdGVkIGNvbW1lbnQ6...
```

### Signing Releases

```bash
# Build release
npm run tauri build

# Sign the update
tauri signer sign target/release/bundle/macos/MyApp.app.tar.gz \
  -k ~/.tauri/myapp.key \
  -p ""

# Creates MyApp.app.tar.gz.sig
```

### Update Server Response

```json
{
  "version": "1.0.1",
  "notes": "Bug fixes and performance improvements",
  "pub_date": "2024-01-15T12:00:00Z",
  "platforms": {
    "darwin-x86_64": {
      "signature": "dGhlIG1lc3NhZ2U=",
      "url": "https://releases.myapp.com/MyApp_1.0.1_x64.app.tar.gz"
    },
    "darwin-aarch64": {
      "signature": "dGhlIG1lc3NhZ2U=",
      "url": "https://releases.myapp.com/MyApp_1.0.1_aarch64.app.tar.gz"
    },
    "windows-x86_64": {
      "signature": "dGhlIG1lc3NhZ2U=",
      "url": "https://releases.myapp.com/MyApp_1.0.1_x64.msi.zip"
    }
  }
}
```

### Frontend Updater Implementation

```rust
use tauri::updater::UpdateResponse;

#[tauri::command]
async fn check_for_updates(app: tauri::AppHandle) -> Result<Option<UpdateInfo>, String> {
    let update_resp = app.updater()
        .check()
        .await
        .map_err(|e| e.to_string())?;

    if update_resp.is_update_available() {
        Ok(Some(UpdateInfo {
            version: update_resp.latest_version().to_string(),
            date: update_resp.date().map(|d| d.to_string()),
            body: update_resp.body().map(|b| b.to_string()),
        }))
    } else {
        Ok(None)
    }
}

#[tauri::command]
async fn install_update(app: tauri::AppHandle) -> Result<(), String> {
    let update_resp = app.updater()
        .check()
        .await
        .map_err(|e| e.to_string())?;

    if update_resp.is_update_available() {
        update_resp.download_and_install()
            .await
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}

#[derive(serde::Serialize)]
struct UpdateInfo {
    version: String,
    date: Option<String>,
    body: Option<String>,
}
```

**Frontend usage**:
```typescript
import { invoke } from '@tauri-apps/api/core';
import { relaunch } from '@tauri-apps/api/process';

async function checkUpdates() {
    const update = await invoke<UpdateInfo | null>('check_for_updates');

    if (update) {
        const install = confirm(
            `Update ${update.version} available!\n\n${update.body}\n\nInstall now?`
        );

        if (install) {
            await invoke('install_update');
            await relaunch();
        }
    }
}
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    strategy:
      fail-fast: false
      matrix:
        platform: [macos-latest, ubuntu-20.04, windows-latest]

    runs-on: ${{ matrix.platform }}

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Install dependencies (Ubuntu)
        if: matrix.platform == 'ubuntu-20.04'
        run: |
          sudo apt-get update
          sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.0-dev libappindicator3-dev librsvg2-dev patchelf

      - name: Install frontend dependencies
        run: npm ci

      - name: Build app
        run: npm run tauri build
        env:
          TAURI_PRIVATE_KEY: ${{ secrets.TAURI_PRIVATE_KEY }}
          TAURI_KEY_PASSWORD: ${{ secrets.TAURI_KEY_PASSWORD }}

      - name: Upload Release Assets
        uses: softprops/action-gh-release@v1
        with:
          files: |
            src-tauri/target/release/bundle/macos/*.dmg
            src-tauri/target/release/bundle/macos/*.app.tar.gz
            src-tauri/target/release/bundle/macos/*.app.tar.gz.sig
            src-tauri/target/release/bundle/deb/*.deb
            src-tauri/target/release/bundle/appimage/*.AppImage
            src-tauri/target/release/bundle/msi/*.msi
            src-tauri/target/release/bundle/msi/*.msi.zip
            src-tauri/target/release/bundle/msi/*.msi.zip.sig
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Platform-Specific Builds

**macOS Universal Binary**:
```bash
# Install targets
rustup target add x86_64-apple-darwin aarch64-apple-darwin

# Build for both architectures
npm run tauri build -- --target universal-apple-darwin
```

**Windows ARM**:
```bash
# Install target
rustup target add aarch64-pc-windows-msvc

# Build
npm run tauri build -- --target aarch64-pc-windows-msvc
```

**Linux AppImage**:
```bash
# Install dependencies
sudo apt-get install libfuse2

# Build
npm run tauri build -- --bundles appimage
```

## Environment-Specific Configuration

### Development vs Production

**config/dev.conf.json**:
```json
{
  "build": {
    "devPath": "http://localhost:5173",
    "beforeDevCommand": "npm run dev"
  },
  "tauri": {
    "allowlist": {
      "all": true  // Permissive for development
    }
  }
}
```

**config/prod.conf.json**:
```json
{
  "build": {
    "distDir": "../dist",
    "beforeBuildCommand": "npm run build"
  },
  "tauri": {
    "allowlist": {
      "all": false,  // Restrictive for production
      "fs": {
        "scope": ["$APPDATA/*"]
      }
    }
  }
}
```

**Build script**:
```bash
#!/bin/bash

if [ "$NODE_ENV" = "production" ]; then
    cp config/prod.conf.json src-tauri/tauri.conf.json
else
    cp config/dev.conf.json src-tauri/tauri.conf.json
fi

npm run tauri build
```

## Resource Bundling

### Including External Files

**tauri.conf.json**:
```json
{
  "tauri": {
    "bundle": {
      "resources": [
        "resources/*",
        "templates/*.html",
        "assets/fonts/*"
      ],
      "externalBin": [
        "binaries/ffmpeg",
        "binaries/imagemagick"
      ]
    }
  }
}
```

**Accessing bundled resources**:
```rust
use tauri::Manager;

#[tauri::command]
async fn read_bundled_resource(
    app: tauri::AppHandle,
    path: String,
) -> Result<String, String> {
    let resource_path = app.path_resolver()
        .resolve_resource(&path)
        .ok_or("Resource not found")?;

    tokio::fs::read_to_string(resource_path)
        .await
        .map_err(|e| e.to_string())
}
```

## Best Practices

1. **Optimize bundle size** - Use LTO, strip symbols, minimize frontend
2. **Sign all releases** - Code signing for trust and security
3. **Implement auto-updater** - Keep users on latest version
4. **Use CI/CD** - Automate builds for all platforms
5. **Test on all platforms** - macOS, Windows, Linux variations
6. **Version consistently** - Sync package.json, Cargo.toml, tauri.conf.json
7. **Secure signing keys** - Use environment variables, never commit
8. **Generate release notes** - Document changes for users
9. **Monitor update success** - Track adoption rates
10. **Rollback capability** - Keep previous versions available

## Common Pitfalls

❌ **Hardcoding dev URLs in production**:
```json
// WRONG - dev URL in production config
{
  "build": {
    "distDir": "http://localhost:5173"
  }
}

// CORRECT
{
  "build": {
    "distDir": "../dist"
  }
}
```

❌ **Committing private keys**:
```bash
# WRONG - private key in repo
git add .tauri/myapp.key

# CORRECT - add to .gitignore
echo ".tauri/*.key" >> .gitignore
```

❌ **Not testing signed builds**:
```bash
# WRONG - only testing debug builds

# CORRECT - test release builds
npm run tauri build
# Then manually test the built app
```

## Summary

- **Build optimization** with Cargo profile and frontend minification
- **Code signing** for macOS (notarization) and Windows (signtool)
- **Auto-updater** with signed releases and update server
- **CI/CD integration** with GitHub Actions for all platforms
- **Platform-specific builds** for universal binaries and ARM
- **Environment configs** separate dev and production settings
- **Resource bundling** for assets and external binaries
- **Security** with key management and signing verification
- **Testing** release builds on all target platforms
- **Monitoring** update adoption and rollback capability
