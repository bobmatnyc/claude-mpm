---
name: tauri-testing
description: Comprehensive testing strategies for Tauri apps including unit tests, integration tests, IPC mocking, and end-to-end testing
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Complete testing: unit tests for commands, integration tests for IPC, mocking patterns, E2E with WebDriver"
    when_to_use: "Ensuring Tauri app quality with comprehensive test coverage for both Rust backend and frontend"
    quick_start: "1. Unit test commands 2. Mock IPC in frontend 3. Integration test with MockRuntime 4. E2E with tauri-driver"
context_limit: 500
tags:
  - tauri
  - testing
  - unit-tests
  - integration-tests
  - mocking
  - e2e
requires_tools: []
---

# Tauri Testing Strategies

## Unit Testing Commands

```rust
// src-tauri/src/commands/files.rs
#[tauri::command]
pub async fn read_file_content(path: String) -> Result<String, String> {
    tokio::fs::read_to_string(path)
        .await
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_read_file_content() {
        // Create temp file
        let temp_dir = std::env::temp_dir();
        let test_file = temp_dir.join("test.txt");
        tokio::fs::write(&test_file, "test content").await.unwrap();

        // Test command
        let result = read_file_content(
            test_file.to_string_lossy().to_string()
        ).await;

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "test content");

        // Cleanup
        tokio::fs::remove_file(test_file).await.unwrap();
    }

    #[tokio::test]
    async fn test_read_nonexistent_file() {
        let result = read_file_content("/nonexistent/file.txt".to_string()).await;
        assert!(result.is_err());
    }
}
```

## Testing with State

```rust
use std::sync::Arc;
use tokio::sync::Mutex;

#[cfg(test)]
mod tests {
    use super::*;

    async fn create_test_state() -> AppState {
        AppState {
            database: Arc::new(Mutex::new(Database::new_in_memory())),
            config: Arc::new(Mutex::new(Config::default())),
        }
    }

    #[tokio::test]
    async fn test_command_with_state() {
        let state = create_test_state().await;

        // Mock State wrapper
        struct MockState(AppState);

        impl<'r> tauri::State<'r, AppState> {
            fn new_mock(state: AppState) -> Self {
                // Use internal test API
                unimplemented!("Use integration test instead")
            }
        }

        // For unit tests, call inner functions directly
        let result = get_data_internal(&state).await;
        assert!(result.is_ok());
    }
}
```

## Frontend IPC Mocking

```typescript
// __mocks__/@tauri-apps/api/core.ts
export const invoke = jest.fn();

// Mock setup
import { invoke } from '@tauri-apps/api/core';

beforeEach(() => {
    (invoke as jest.Mock).mockClear();
});

test('calls read_file command', async () => {
    (invoke as jest.Mock).mockResolvedValue('file content');

    const content = await readFile('test.txt');

    expect(invoke).toHaveBeenCalledWith('read_file', {
        filename: 'test.txt'
    });
    expect(content).toBe('file content');
});

test('handles command errors', async () => {
    (invoke as jest.Mock).mockRejectedValue('File not found');

    await expect(readFile('missing.txt')).rejects.toThrow('File not found');
});
```

## Integration Testing

```rust
// tests/integration_test.rs
#[cfg(test)]
mod tests {
    use tauri::test::{mock_builder, MockRuntime, mock_context};

    #[test]
    fn test_app_creation() {
        let app = mock_builder()
            .invoke_handler(tauri::generate_handler![
                my_command,
                another_command,
            ])
            .build(MockRuntime::default())
            .expect("failed to build app");

        assert!(app.get_window("main").is_some());
    }

    #[test]
    fn test_command_invocation() {
        let app = mock_builder()
            .invoke_handler(tauri::generate_handler![test_command])
            .build(MockRuntime::default())
            .expect("failed to build app");

        // Commands can be tested via window
        let window = app.get_window("main").unwrap();
        // Test window interactions
    }
}
```

## End-to-End Testing with WebDriver

### Setup

**Add to Cargo.toml**:
```toml
[dev-dependencies]
tauri-driver = "0.1"
```

**Add test runner**:
```rust
// tests/webdriver.rs
use tauri_driver::test::*;

#[test]
fn run_webdriver_tests() {
    let mut driver = DriverBuilder::native()
        .build()
        .expect("Failed to create driver");

    // Navigate to app
    driver.goto("tauri://localhost");

    // Find element and click
    let button = driver.find_element(By::Id("my-button"))
        .expect("Button not found");
    button.click().expect("Failed to click");

    // Verify result
    let result = driver.find_element(By::Id("result"))
        .expect("Result not found");
    assert_eq!(result.text().unwrap(), "Success");
}
```

## Mock Event System

```typescript
// __mocks__/@tauri-apps/api/event.ts
type EventCallback = (event: any) => void;
const listeners = new Map<string, EventCallback[]>();

export const listen = jest.fn(async (event: string, callback: EventCallback) => {
    if (!listeners.has(event)) {
        listeners.set(event, []);
    }
    listeners.get(event)!.push(callback);

    return jest.fn(() => {
        const callbacks = listeners.get(event);
        if (callbacks) {
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    });
});

export const emit = jest.fn((event: string, payload: any) => {
    const callbacks = listeners.get(event) || [];
    callbacks.forEach(cb => cb({ payload }));
});

// Test usage
test('handles progress events', async () => {
    const progressHandler = jest.fn();
    const unlisten = await listen('progress', progressHandler);

    emit('progress', { current: 50, total: 100 });

    expect(progressHandler).toHaveBeenCalledWith({
        payload: { current: 50, total: 100 }
    });

    unlisten();
});
```

## Testing Async Commands

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tokio::time::{timeout, Duration};

    #[tokio::test]
    async fn test_long_operation_completes() {
        let result = timeout(
            Duration::from_secs(5),
            long_running_command()
        ).await;

        assert!(result.is_ok());
        assert!(result.unwrap().is_ok());
    }

    #[tokio::test]
    async fn test_operation_with_progress() {
        let (tx, mut rx) = tokio::sync::mpsc::channel(100);

        tokio::spawn(async move {
            // Simulate command emitting progress
            for i in 0..10 {
                tx.send(i).await.ok();
            }
        });

        let mut count = 0;
        while let Some(progress) = rx.recv().await {
            assert_eq!(progress, count);
            count += 1;
        }

        assert_eq!(count, 10);
    }
}
```

## Frontend Component Testing

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { invoke } from '@tauri-apps/api/core';
import { DocumentView } from './DocumentView';

jest.mock('@tauri-apps/api/core');

test('renders document content', async () => {
    (invoke as jest.Mock).mockResolvedValue('Test content');

    render(<DocumentView filename="test.txt" />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();

    await waitFor(() => {
        expect(screen.getByText('Test content')).toBeInTheDocument();
    });
});

test('displays error on failure', async () => {
    (invoke as jest.Mock).mockRejectedValue('File not found');

    render(<DocumentView filename="missing.txt" />);

    await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
});
```

## Best Practices

1. **Unit test all commands** - Test logic without Tauri runtime
2. **Mock IPC in frontend** - Use jest.mock for @tauri-apps/api
3. **Test error paths** - Verify error handling works
4. **Use integration tests** - For command registration
5. **E2E for critical flows** - User workflows with WebDriver
6. **Test async operations** - With timeouts and proper await
7. **Mock external dependencies** - Databases, APIs, file system
8. **Test state management** - Concurrent access, race conditions
9. **Coverage targets** - Aim for >80% coverage
10. **CI integration** - Run tests on every commit

## Common Pitfalls

❌ **Forgetting async in tests**:
```rust
// WRONG
#[test]
fn test_async_command() {
    let result = async_command().await;  // Won't compile
}

// CORRECT
#[tokio::test]
async fn test_async_command() {
    let result = async_command().await;
}
```

❌ **Not cleaning up temp files**:
```rust
// WRONG - leaves files behind
#[tokio::test]
async fn test() {
    tokio::fs::write("test.txt", "content").await.unwrap();
    // Test... but never removes file
}

// CORRECT
#[tokio::test]
async fn test() {
    let file = "test.txt";
    tokio::fs::write(file, "content").await.unwrap();
    // Test...
    tokio::fs::remove_file(file).await.unwrap();
}
```

## Summary

- **Unit tests** for command logic
- **Integration tests** with MockRuntime
- **Mock IPC** in frontend tests
- **E2E tests** with tauri-driver
- **Test async** with #[tokio::test]
- **Mock events** for event testing
- **Test error paths** always
- **CI integration** for automation
