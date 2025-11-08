# Testing and Deployment

Complete guide to testing strategies, cross-platform builds, distribution, and CI/CD pipelines for Rust desktop applications.

## Testing Strategies

### Unit Testing Tauri Commands

```rust
// src/commands.rs
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: u64,
    pub name: String,
    pub email: String,
}

pub struct UserService {
    users: Vec<User>,
}

impl UserService {
    pub fn new() -> Self {
        Self { users: Vec::new() }
    }

    pub fn add_user(&mut self, name: String, email: String) -> Result<User, String> {
        if name.is_empty() {
            return Err("Name cannot be empty".to_string());
        }

        if !email.contains('@') {
            return Err("Invalid email".to_string());
        }

        let user = User {
            id: self.users.len() as u64 + 1,
            name,
            email,
        };

        self.users.push(user.clone());
        Ok(user)
    }

    pub fn get_user(&self, id: u64) -> Option<&User> {
        self.users.iter().find(|u| u.id == id)
    }

    pub fn get_all_users(&self) -> &[User] {
        &self.users
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_user_success() {
        let mut service = UserService::new();
        let result = service.add_user("John Doe".to_string(), "john@example.com".to_string());

        assert!(result.is_ok());
        let user = result.unwrap();
        assert_eq!(user.name, "John Doe");
        assert_eq!(user.email, "john@example.com");
        assert_eq!(service.get_all_users().len(), 1);
    }

    #[test]
    fn test_add_user_empty_name() {
        let mut service = UserService::new();
        let result = service.add_user("".to_string(), "john@example.com".to_string());

        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "Name cannot be empty");
    }

    #[test]
    fn test_add_user_invalid_email() {
        let mut service = UserService::new();
        let result = service.add_user("John Doe".to_string(), "invalid-email".to_string());

        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "Invalid email");
    }

    #[test]
    fn test_get_user() {
        let mut service = UserService::new();
        service.add_user("John Doe".to_string(), "john@example.com".to_string()).unwrap();

        let user = service.get_user(1);
        assert!(user.is_some());
        assert_eq!(user.unwrap().name, "John Doe");
    }

    #[test]
    fn test_get_user_not_found() {
        let service = UserService::new();
        let user = service.get_user(999);
        assert!(user.is_none());
    }
}
```

### Integration Testing with Mock State

```rust
#[cfg(test)]
mod integration_tests {
    use super::*;
    use std::sync::Mutex;

    struct TestState {
        service: Mutex<UserService>,
    }

    fn setup_test_state() -> TestState {
        TestState {
            service: Mutex::new(UserService::new()),
        }
    }

    #[test]
    fn test_user_workflow() {
        let state = setup_test_state();

        // Add multiple users
        {
            let mut service = state.service.lock().unwrap();
            service.add_user("Alice".to_string(), "alice@example.com".to_string()).unwrap();
            service.add_user("Bob".to_string(), "bob@example.com".to_string()).unwrap();
        }

        // Verify users were added
        {
            let service = state.service.lock().unwrap();
            assert_eq!(service.get_all_users().len(), 2);
        }

        // Get specific user
        {
            let service = state.service.lock().unwrap();
            let alice = service.get_user(1);
            assert!(alice.is_some());
            assert_eq!(alice.unwrap().name, "Alice");
        }
    }
}
```

### Async Testing with Tokio

```rust
#[cfg(test)]
mod async_tests {
    use super::*;
    use tokio::test;

    #[tokio::test]
    async fn test_async_operation() {
        let result = fetch_data_async().await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_concurrent_operations() {
        let futures = vec![
            fetch_data_async(),
            fetch_data_async(),
            fetch_data_async(),
        ];

        let results = futures::future::join_all(futures).await;

        assert_eq!(results.len(), 3);
        for result in results {
            assert!(result.is_ok());
        }
    }

    async fn fetch_data_async() -> Result<String, String> {
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        Ok("data".to_string())
    }
}
```

### Testing with Database

```rust
#[cfg(test)]
mod database_tests {
    use super::*;
    use sqlx::SqlitePool;

    async fn setup_test_db() -> SqlitePool {
        let pool = SqlitePool::connect(":memory:")
            .await
            .expect("Failed to create in-memory database");

        // Run migrations
        sqlx::query(
            "CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            )"
        )
        .execute(&pool)
        .await
        .expect("Failed to create table");

        pool
    }

    #[tokio::test]
    async fn test_create_user() {
        let pool = setup_test_db().await;

        let result = sqlx::query(
            "INSERT INTO users (name, email) VALUES (?, ?)"
        )
        .bind("John Doe")
        .bind("john@example.com")
        .execute(&pool)
        .await;

        assert!(result.is_ok());

        let count: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM users")
            .fetch_one(&pool)
            .await
            .unwrap();

        assert_eq!(count.0, 1);
    }
}
```

## UI Testing Approaches

### egui Testing

```rust
#[cfg(test)]
mod ui_tests {
    use super::*;
    use eframe::egui;

    #[test]
    fn test_ui_state_update() {
        let mut app = MyApp::default();

        // Simulate UI interaction
        app.counter = 0;

        // Trigger button click logic
        app.counter += 1;

        assert_eq!(app.counter, 1);
    }

    #[test]
    fn test_ui_rendering() {
        let mut app = MyApp::default();
        let ctx = egui::Context::default();

        // Test that UI can be rendered without panic
        app.update(&ctx, &mut eframe::Frame::new(eframe::FrameData {
            info: eframe::IntegrationInfo::default(),
            output: Default::default(),
            repaint_signal: std::sync::Arc::new(eframe::RepaintSignal::default()),
        }));
    }
}
```

### Tauri Frontend-Backend Integration Tests

```typescript
// src/tests/integration.test.ts
import { invoke } from '@tauri-apps/api/core';

describe('User Management', () => {
    beforeEach(async () => {
        // Reset state
        await invoke('reset_users');
    });

    test('should add user', async () => {
        const user = await invoke<User>('add_user', {
            name: 'John Doe',
            email: 'john@example.com',
        });

        expect(user.name).toBe('John Doe');
        expect(user.email).toBe('john@example.com');
    });

    test('should reject invalid email', async () => {
        await expect(
            invoke('add_user', {
                name: 'John Doe',
                email: 'invalid',
            })
        ).rejects.toThrow('Invalid email');
    });

    test('should get all users', async () => {
        await invoke('add_user', {
            name: 'Alice',
            email: 'alice@example.com',
        });

        await invoke('add_user', {
            name: 'Bob',
            email: 'bob@example.com',
        });

        const users = await invoke<User[]>('get_all_users');
        expect(users).toHaveLength(2);
    });
});
```

### E2E Testing with WebDriver

```typescript
// tests/e2e/app.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Desktop App E2E', () => {
    test('should load application', async ({ page }) => {
        await page.goto('http://localhost:1420'); // Tauri dev server

        await expect(page.locator('h1')).toContainText('My App');
    });

    test('should add user through UI', async ({ page }) => {
        await page.goto('http://localhost:1420');

        await page.fill('input[name="name"]', 'John Doe');
        await page.fill('input[name="email"]', 'john@example.com');
        await page.click('button:has-text("Add User")');

        await expect(page.locator('.user-item')).toContainText('John Doe');
    });

    test('should show error for invalid input', async ({ page }) => {
        await page.goto('http://localhost:1420');

        await page.fill('input[name="name"]', '');
        await page.fill('input[name="email"]', 'invalid');
        await page.click('button:has-text("Add User")');

        await expect(page.locator('.error')).toBeVisible();
    });
});
```

## Cross-Compilation and Builds

### Build Scripts

```bash
#!/bin/bash
# scripts/build.sh

set -e

TARGET_TRIPLE="${1:-}"
BUILD_TYPE="${2:-release}"

if [ -z "$TARGET_TRIPLE" ]; then
    echo "Building for current platform..."
    cargo tauri build
else
    echo "Building for $TARGET_TRIPLE..."

    # Install target if needed
    rustup target add "$TARGET_TRIPLE"

    # Build
    if [ "$BUILD_TYPE" = "debug" ]; then
        cargo tauri build --debug --target "$TARGET_TRIPLE"
    else
        cargo tauri build --target "$TARGET_TRIPLE"
    fi
fi

echo "Build completed successfully!"
```

### Cross-Compilation Setup

**For Windows from Linux/macOS:**
```bash
# Install cross-compilation tools
cargo install cargo-xwin

# Add Windows target
rustup target add x86_64-pc-windows-msvc

# Build for Windows
cargo xwin build --release --target x86_64-pc-windows-msvc
```

**For macOS from Linux:**
```bash
# Install osxcross (complex setup, see osxcross documentation)
# Add macOS targets
rustup target add x86_64-apple-darwin
rustup target add aarch64-apple-darwin

# Build for macOS
CROSS_COMPILE=x86_64-apple-darwin- \
cargo build --release --target x86_64-apple-darwin
```

**For Linux from macOS/Windows:**
```bash
# Install cross
cargo install cross

# Build for Linux
cross build --release --target x86_64-unknown-linux-gnu
```

### Universal Binaries (macOS)

```bash
#!/bin/bash
# scripts/build-universal-macos.sh

set -e

echo "Building universal macOS binary..."

# Build for both architectures
cargo tauri build --target x86_64-apple-darwin
cargo tauri build --target aarch64-apple-darwin

# Create universal binary
lipo -create \
    target/x86_64-apple-darwin/release/bundle/macos/MyApp.app/Contents/MacOS/MyApp \
    target/aarch64-apple-darwin/release/bundle/macos/MyApp.app/Contents/MacOS/MyApp \
    -output target/universal-apple-darwin/release/MyApp

echo "Universal binary created!"
```

## Platform-Specific Installers

### Windows Installer (WiX)

**wix/main.wxs:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
    <Product
        Id="*"
        Name="My Application"
        Language="1033"
        Version="1.0.0"
        Manufacturer="My Company"
        UpgradeCode="PUT-GUID-HERE">

        <Package
            InstallerVersion="200"
            Compressed="yes"
            InstallScope="perMachine" />

        <MajorUpgrade
            DowngradeErrorMessage="A newer version is already installed." />

        <MediaTemplate EmbedCab="yes" />

        <Feature
            Id="MainApplication"
            Title="My Application"
            Level="1">
            <ComponentGroupRef Id="AppFiles" />
        </Feature>

        <Directory Id="TARGETDIR" Name="SourceDir">
            <Directory Id="ProgramFilesFolder">
                <Directory Id="INSTALLFOLDER" Name="MyApp" />
            </Directory>
            <Directory Id="ProgramMenuFolder">
                <Directory Id="ApplicationProgramsFolder" Name="MyApp"/>
            </Directory>
        </Directory>

        <ComponentGroup Id="AppFiles" Directory="INSTALLFOLDER">
            <Component Id="MainExecutable">
                <File
                    Id="MainExe"
                    Source="$(var.SourceDir)\MyApp.exe"
                    KeyPath="yes">
                    <Shortcut
                        Id="ApplicationStartMenuShortcut"
                        Directory="ApplicationProgramsFolder"
                        Name="MyApp"
                        Description="My Application"
                        WorkingDirectory="INSTALLFOLDER"
                        Icon="AppIcon.exe"
                        IconIndex="0"
                        Advertise="yes" />
                </File>
            </Component>
        </ComponentGroup>
    </Product>
</Wix>
```

### macOS DMG Creation

```bash
#!/bin/bash
# scripts/create-dmg.sh

set -e

APP_NAME="MyApp"
VERSION="1.0.0"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
SOURCE_FOLDER="target/release/bundle/macos/${APP_NAME}.app"
DMG_FOLDER="dmg_temp"

echo "Creating DMG for ${APP_NAME}..."

# Create temporary folder
mkdir -p "$DMG_FOLDER"

# Copy app
cp -R "$SOURCE_FOLDER" "$DMG_FOLDER/"

# Create symbolic link to Applications
ln -s /Applications "$DMG_FOLDER/Applications"

# Create DMG
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$DMG_FOLDER" \
    -ov \
    -format UDZO \
    "$DMG_NAME"

# Cleanup
rm -rf "$DMG_FOLDER"

echo "DMG created: $DMG_NAME"
```

### Linux Packages

**Debian Package (.deb):**
```bash
#!/bin/bash
# scripts/build-deb.sh

set -e

APP_NAME="myapp"
VERSION="1.0.0"
ARCH="amd64"

DEB_DIR="target/debian"
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/usr/bin"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/share/icons/hicolor/256x256/apps"

# Create control file
cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Your Name <your@email.com>
Description: My Application
 A desktop application built with Tauri
EOF

# Copy binary
cp "target/release/$APP_NAME" "$DEB_DIR/usr/bin/"

# Create desktop entry
cat > "$DEB_DIR/usr/share/applications/$APP_NAME.desktop" << EOF
[Desktop Entry]
Name=My App
Exec=/usr/bin/$APP_NAME
Icon=$APP_NAME
Type=Application
Categories=Utility;
EOF

# Copy icon
cp "icons/icon.png" "$DEB_DIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"

# Build package
dpkg-deb --build "$DEB_DIR" "${APP_NAME}_${VERSION}_${ARCH}.deb"

echo "Debian package created!"
```

**AppImage:**
```bash
#!/bin/bash
# scripts/build-appimage.sh

set -e

APP_NAME="MyApp"
APPDIR="AppDir"

# Create AppDir structure
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy files
cp "target/release/myapp" "$APPDIR/usr/bin/"
cp "myapp.desktop" "$APPDIR/usr/share/applications/"
cp "icons/icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/myapp.png"

# Create AppRun
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/myapp" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Download appimagetool
wget -O appimagetool "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x appimagetool

# Build AppImage
./appimagetool "$APPDIR" "${APP_NAME}.AppImage"

echo "AppImage created!"
```

## Code Signing and Notarization

### macOS Code Signing

```bash
#!/bin/bash
# scripts/sign-macos.sh

set -e

APP_PATH="$1"
IDENTITY="Developer ID Application: Your Name (TEAMID)"

echo "Signing $APP_PATH..."

# Sign all frameworks and dylibs first
find "$APP_PATH/Contents" -name "*.framework" -or -name "*.dylib" | while read file; do
    codesign --force --sign "$IDENTITY" \
        --options runtime \
        --timestamp \
        "$file"
done

# Sign the app bundle
codesign --force --deep --sign "$IDENTITY" \
    --options runtime \
    --entitlements entitlements.plist \
    --timestamp \
    "$APP_PATH"

# Verify signature
codesign --verify --verbose=4 "$APP_PATH"

echo "Signing completed!"
```

**entitlements.plist:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

### macOS Notarization

```bash
#!/bin/bash
# scripts/notarize-macos.sh

set -e

APP_PATH="$1"
BUNDLE_ID="com.yourcompany.myapp"
APPLE_ID="your@email.com"
TEAM_ID="TEAMID"
APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"

# Create DMG
DMG_PATH="MyApp.dmg"
hdiutil create -volname "MyApp" \
    -srcfolder "$APP_PATH" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

# Submit for notarization
echo "Submitting for notarization..."
xcrun notarytool submit "$DMG_PATH" \
    --apple-id "$APPLE_ID" \
    --team-id "$TEAM_ID" \
    --password "$APP_SPECIFIC_PASSWORD" \
    --wait

# Staple the ticket
echo "Stapling ticket..."
xcrun stapler staple "$DMG_PATH"

echo "Notarization completed!"
```

### Windows Code Signing

```powershell
# scripts/sign-windows.ps1

param(
    [string]$FilePath,
    [string]$CertPath,
    [string]$Password
)

# Sign executable
& "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe" sign `
    /f $CertPath `
    /p $Password `
    /tr http://timestamp.digicert.com `
    /td sha256 `
    /fd sha256 `
    $FilePath

# Verify signature
& "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe" verify /pa $FilePath

Write-Host "Signing completed!"
```

## CI/CD Pipelines

### GitHub Actions Workflow

```yaml
# .github/workflows/build.yml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        platform: [macos-latest, ubuntu-20.04, windows-latest]

    runs-on: ${{ matrix.platform }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Install dependencies (Ubuntu only)
        if: matrix.platform == 'ubuntu-20.04'
        run: |
          sudo apt-get update
          sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.0-dev libappindicator3-dev librsvg2-dev patchelf

      - name: Install frontend dependencies
        run: npm install

      - name: Build application
        run: npm run tauri build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.platform }}-build
          path: |
            src-tauri/target/release/bundle/*

  release:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            macos-latest-build/**/*
            ubuntu-20.04-build/**/*
            windows-latest-build/**/*
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Multi-Platform Build Matrix

```yaml
# .github/workflows/release.yml
name: Release

on:
  workflow_dispatch:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: ubuntu-20.04
            target: x86_64-unknown-linux-gnu
            artifact: deb, appimage
          - os: macos-latest
            target: x86_64-apple-darwin
            artifact: dmg, app
          - os: macos-latest
            target: aarch64-apple-darwin
            artifact: dmg, app
          - os: windows-latest
            target: x86_64-pc-windows-msvc
            artifact: msi, exe

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Build
        run: cargo tauri build --target ${{ matrix.target }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.target }}
          path: src-tauri/target/${{ matrix.target }}/release/bundle/
```

### Auto-Update Server

```rust
// Simple update server
use actix_web::{web, App, HttpResponse, HttpServer};
use serde::Serialize;

#[derive(Serialize)]
struct UpdateManifest {
    version: String,
    notes: String,
    pub_date: String,
    platforms: Platforms,
}

#[derive(Serialize)]
struct Platforms {
    #[serde(rename = "darwin-x86_64")]
    darwin_x86_64: Platform,
    #[serde(rename = "darwin-aarch64")]
    darwin_aarch64: Platform,
    #[serde(rename = "linux-x86_64")]
    linux_x86_64: Platform,
    #[serde(rename = "windows-x86_64")]
    windows_x86_64: Platform,
}

#[derive(Serialize)]
struct Platform {
    signature: String,
    url: String,
}

async fn update_manifest() -> HttpResponse {
    let manifest = UpdateManifest {
        version: "1.0.1".to_string(),
        notes: "Bug fixes and improvements".to_string(),
        pub_date: "2024-01-15T00:00:00Z".to_string(),
        platforms: Platforms {
            darwin_x86_64: Platform {
                signature: "BASE64_SIGNATURE".to_string(),
                url: "https://releases.myapp.com/myapp-1.0.1-x64.dmg".to_string(),
            },
            darwin_aarch64: Platform {
                signature: "BASE64_SIGNATURE".to_string(),
                url: "https://releases.myapp.com/myapp-1.0.1-arm64.dmg".to_string(),
            },
            linux_x86_64: Platform {
                signature: "BASE64_SIGNATURE".to_string(),
                url: "https://releases.myapp.com/myapp-1.0.1-amd64.AppImage".to_string(),
            },
            windows_x86_64: Platform {
                signature: "BASE64_SIGNATURE".to_string(),
                url: "https://releases.myapp.com/myapp-1.0.1-x64-setup.exe".to_string(),
            },
        },
    };

    HttpResponse::Ok().json(manifest)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .route("/update-manifest.json", web::get().to(update_manifest))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
```

This comprehensive testing and deployment guide covers everything from unit tests to production CI/CD pipelines, enabling reliable cross-platform distribution of Rust desktop applications.
