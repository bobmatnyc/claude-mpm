---
name: tauri-error-handling
description: Comprehensive error handling in Tauri using custom error types, thiserror, structured errors, and frontend error management
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Production error handling: custom types with thiserror, structured errors, error context, frontend integration"
    when_to_use: "Building production Tauri apps requiring robust error handling, debugging, and user-friendly error messages"
    quick_start: "1. Define custom errors with thiserror 2. Convert to String for IPC 3. Handle in frontend 4. Log appropriately"
context_limit: 500
tags:
  - tauri
  - error-handling
  - thiserror
  - debugging
  - production
requires_tools: []
---

# Tauri Error Handling

## Custom Error Types with thiserror

### Basic Error Definition

```rust
// src-tauri/src/error.rs
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("File not found: {0}")]
    FileNotFound(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Database error: {0}")]
    DatabaseError(#[from] sqlx::Error),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    SerdeError(#[from] serde_json::Error),

    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    #[error("Operation failed: {0}")]
    OperationFailed(String),
}

// Convert to String for Tauri commands
impl From<AppError> for String {
    fn from(error: AppError) -> Self {
        error.to_string()
    }
}
```

### Usage in Commands

```rust
#[tauri::command]
async fn load_config(path: String) -> Result<Config, String> {
    read_config(&path).await?  // AppError auto-converts to String
}

async fn read_config(path: &str) -> Result<Config, AppError> {
    let content = tokio::fs::read_to_string(path)
        .await
        .map_err(|_| AppError::FileNotFound(path.to_string()))?;

    let config: Config = serde_json::from_str(&content)?;  // Auto-converts SerdeError

    Ok(config)
}
```

## Structured Error Returns

### Error Response Type

```rust
#[derive(serde::Serialize)]
#[serde(tag = "type")]
pub enum CommandResult<T> {
    #[serde(rename = "success")]
    Success {
        data: T,
    },
    #[serde(rename = "error")]
    Error {
        code: String,
        message: String,
        details: Option<serde_json::Value>,
    },
}

#[derive(serde::Serialize)]
pub struct ErrorDetails {
    timestamp: u64,
    operation: String,
    context: Option<String>,
}

#[tauri::command]
async fn complex_operation() -> CommandResult<String> {
    match perform_operation().await {
        Ok(result) => CommandResult::Success { data: result },
        Err(e) => CommandResult::Error {
            code: "OPERATION_FAILED".to_string(),
            message: e.to_string(),
            details: Some(serde_json::json!({
                "timestamp": std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs(),
                "operation": "complex_operation"
            })),
        },
    }
}
```

**Frontend handling**:
```typescript
type CommandResult<T> =
    | { type: 'success'; data: T }
    | { type: 'error'; code: string; message: string; details?: any };

const result = await invoke<CommandResult<string>>('complex_operation');

if (result.type === 'success') {
    console.log('Data:', result.data);
} else {
    console.error(`Error ${result.code}: ${result.message}`);
    if (result.details) {
        console.error('Details:', result.details);
    }
}
```

## Error Context and Chaining

### Adding Context to Errors

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Failed to load user data: {0}")]
    UserLoadError(#[source] Box<dyn std::error::Error + Send + Sync>),

    #[error("Database connection failed: {0}")]
    DatabaseError(String),
}

async fn load_user_with_context(id: u64) -> Result<User, AppError> {
    let db = connect_db()
        .await
        .map_err(|e| AppError::DatabaseError(e.to_string()))?;

    let user = db.query_user(id)
        .await
        .map_err(|e| AppError::UserLoadError(Box::new(e)))?;

    Ok(user)
}
```

### Error Context Pattern

```rust
pub trait ErrorContext<T> {
    fn context(self, ctx: &str) -> Result<T, AppError>;
}

impl<T, E> ErrorContext<T> for Result<T, E>
where
    E: std::error::Error + Send + Sync + 'static,
{
    fn context(self, ctx: &str) -> Result<T, AppError> {
        self.map_err(|e| AppError::OperationFailed(
            format!("{}: {}", ctx, e)
        ))
    }
}

#[tauri::command]
async fn save_with_context(data: String) -> Result<(), String> {
    let parsed = parse_data(&data)
        .context("Failed to parse data")?;

    write_to_disk(&parsed)
        .await
        .context("Failed to write to disk")?;

    Ok(())
}
```

## Domain-Specific Error Types

### Multiple Error Enums

```rust
// Auth errors
#[derive(Error, Debug)]
pub enum AuthError {
    #[error("Invalid credentials")]
    InvalidCredentials,

    #[error("Token expired")]
    TokenExpired,

    #[error("Insufficient permissions")]
    InsufficientPermissions,
}

// File errors
#[derive(Error, Debug)]
pub enum FileError {
    #[error("File not found: {0}")]
    NotFound(String),

    #[error("File already exists: {0}")]
    AlreadyExists(String),

    #[error("Invalid file format: {0}")]
    InvalidFormat(String),
}

// Application error combines all
#[derive(Error, Debug)]
pub enum AppError {
    #[error("Authentication error: {0}")]
    Auth(#[from] AuthError),

    #[error("File error: {0}")]
    File(#[from] FileError),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

impl From<AppError> for String {
    fn from(error: AppError) -> Self {
        error.to_string()
    }
}
```

### Using Domain Errors

```rust
#[tauri::command]
async fn login(username: String, password: String) -> Result<String, String> {
    authenticate(&username, &password).await?  // AuthError auto-converts
}

async fn authenticate(username: &str, password: &str) -> Result<String, AuthError> {
    if username.is_empty() || password.is_empty() {
        return Err(AuthError::InvalidCredentials);
    }

    let token = verify_credentials(username, password)
        .await
        .ok_or(AuthError::InvalidCredentials)?;

    if is_token_expired(&token) {
        return Err(AuthError::TokenExpired);
    }

    Ok(token)
}
```

## Frontend Error Handling

### Type-Safe Error Handling

```typescript
// Define error types matching backend
type TauriError = string;

interface ErrorInfo {
    code: string;
    message: string;
    recoverable: boolean;
}

function parseError(error: TauriError): ErrorInfo {
    if (error.includes('File not found')) {
        return {
            code: 'FILE_NOT_FOUND',
            message: 'The requested file could not be found',
            recoverable: true
        };
    } else if (error.includes('Permission denied')) {
        return {
            code: 'PERMISSION_DENIED',
            message: 'You do not have permission to perform this action',
            recoverable: false
        };
    } else if (error.includes('Invalid input')) {
        return {
            code: 'INVALID_INPUT',
            message: 'The provided input is invalid',
            recoverable: true
        };
    } else {
        return {
            code: 'UNKNOWN_ERROR',
            message: error,
            recoverable: false
        };
    }
}

// Usage
async function loadDocument(filename: string) {
    try {
        const content = await invoke<string>('read_document', { filename });
        return content;
    } catch (error) {
        const errorInfo = parseError(error as TauriError);

        if (errorInfo.recoverable) {
            showNotification(errorInfo.message, 'warning');
        } else {
            showNotification(errorInfo.message, 'error');
        }

        throw errorInfo;
    }
}
```

### React Error Boundary Integration

```typescript
import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';

interface ErrorState {
    hasError: boolean;
    error: string | null;
}

function useTauriCommand<T>(command: string, args?: any) {
    const [data, setData] = useState<T | null>(null);
    const [error, setError] = useState<ErrorState>({ hasError: false, error: null });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        invoke<T>(command, args)
            .then(setData)
            .catch((err) => {
                setError({
                    hasError: true,
                    error: err.toString()
                });
            })
            .finally(() => setLoading(false));
    }, [command, JSON.stringify(args)]);

    return { data, error, loading };
}

// Usage
function DocumentView({ filename }: { filename: string }) {
    const { data, error, loading } = useTauriCommand<string>(
        'read_document',
        { filename }
    );

    if (loading) return <div>Loading...</div>;
    if (error.hasError) return <div>Error: {error.error}</div>;

    return <div>{data}</div>;
}
```

## Error Logging and Debugging

### Logging Errors

```rust
use log::{error, warn, info};

#[tauri::command]
async fn operation_with_logging() -> Result<(), String> {
    info!("Starting operation");

    match perform_operation().await {
        Ok(result) => {
            info!("Operation completed successfully");
            Ok(result)
        }
        Err(e) => {
            error!("Operation failed: {}", e);
            Err(e.to_string())
        }
    }
}

// Error with context logging
async fn load_config() -> Result<Config, AppError> {
    match tokio::fs::read_to_string("config.json").await {
        Ok(content) => {
            info!("Config file loaded");
            Ok(serde_json::from_str(&content)?)
        }
        Err(e) => {
            error!("Failed to load config: {}", e);
            warn!("Using default configuration");
            Ok(Config::default())
        }
    }
}
```

### Error Reporting to Frontend

```rust
#[tauri::command]
async fn operation_with_reporting(
    window: tauri::Window,
) -> Result<(), String> {
    match risky_operation().await {
        Ok(_) => Ok(()),
        Err(e) => {
            // Log error
            log::error!("Operation failed: {}", e);

            // Report to frontend
            window.emit("error-occurred", serde_json::json!({
                "message": e.to_string(),
                "timestamp": chrono::Utc::now().to_rfc3339(),
                "severity": "error"
            })).ok();

            Err(e.to_string())
        }
    }
}
```

**Frontend error listener**:
```typescript
import { listen } from '@tauri-apps/api/event';

listen('error-occurred', (event) => {
    const { message, timestamp, severity } = event.payload;

    console.error(`[${timestamp}] ${severity}: ${message}`);

    // Show toast notification
    showErrorToast(message);

    // Log to error tracking service
    trackError({ message, timestamp, severity });
});
```

## Retry and Recovery Patterns

### Retry with Exponential Backoff

```rust
use tokio::time::{sleep, Duration};

async fn retry_operation<F, T, E>(
    mut operation: F,
    max_attempts: u32,
) -> Result<T, E>
where
    F: FnMut() -> std::pin::Pin<Box<dyn Future<Output = Result<T, E>> + Send>>,
{
    let mut attempt = 0;

    loop {
        attempt += 1;

        match operation().await {
            Ok(result) => return Ok(result),
            Err(e) if attempt >= max_attempts => return Err(e),
            Err(_) => {
                let delay = Duration::from_millis(100 * 2u64.pow(attempt));
                sleep(delay).await;
            }
        }
    }
}

#[tauri::command]
async fn fetch_with_retry(url: String) -> Result<String, String> {
    retry_operation(
        || Box::pin(fetch_data(&url)),
        3
    )
    .await
    .map_err(|e| e.to_string())
}
```

### Graceful Degradation

```rust
#[tauri::command]
async fn load_data_with_fallback() -> Result<Data, String> {
    // Try primary source
    match load_from_primary().await {
        Ok(data) => return Ok(data),
        Err(e) => {
            log::warn!("Primary source failed: {}, trying cache", e);
        }
    }

    // Try cache
    match load_from_cache().await {
        Ok(data) => return Ok(data),
        Err(e) => {
            log::warn!("Cache failed: {}, using defaults", e);
        }
    }

    // Use defaults
    Ok(Data::default())
}
```

## Best Practices

1. **Use thiserror for custom errors** - Clean, maintainable error definitions
2. **Convert to String for IPC** - Tauri requires serializable errors
3. **Add context to errors** - Include what operation failed
4. **Log errors appropriately** - Use log levels (error, warn, info)
5. **Provide user-friendly messages** - Don't expose technical details
6. **Use domain-specific errors** - Organize by feature/module
7. **Implement retry logic** - For transient failures
8. **Report errors to frontend** - Via events for async operations
9. **Test error paths** - Ensure proper error handling
10. **Document error codes** - Help frontend developers

## Common Pitfalls

❌ **Using panic! instead of Result**:
```rust
// WRONG - panic in library code
#[tauri::command]
fn bad_command(input: String) -> String {
    if input.is_empty() {
        panic!("Empty input!");  // Crashes app!
    }
    process(input)
}

// CORRECT - return Result
#[tauri::command]
fn good_command(input: String) -> Result<String, String> {
    if input.is_empty() {
        return Err("Empty input not allowed".to_string());
    }
    Ok(process(input))
}
```

❌ **Not implementing From<AppError> for String**:
```rust
// WRONG - can't use ? operator
#[tauri::command]
async fn command() -> Result<Data, String> {
    let data = load().await?;  // AppError doesn't convert to String
    Ok(data)
}

// CORRECT - implement conversion
impl From<AppError> for String {
    fn from(error: AppError) -> Self {
        error.to_string()
    }
}
```

❌ **Exposing technical details in errors**:
```rust
// WRONG - leaks implementation details
Err(format!("Database error: {}", e))  // Shows SQL errors to user

// CORRECT - user-friendly message
Err("Failed to load data. Please try again.".to_string())
// Log technical details separately
```

## Summary

- **thiserror** for clean custom error types
- **Convert to String** for Tauri IPC compatibility
- **Add context** to errors for debugging
- **Domain-specific errors** for better organization
- **Structured errors** for complex error information
- **Log appropriately** with proper severity levels
- **Frontend error handling** with type-safe parsing
- **Retry logic** for transient failures
- **Graceful degradation** when possible
- **User-friendly messages** without technical jargon
