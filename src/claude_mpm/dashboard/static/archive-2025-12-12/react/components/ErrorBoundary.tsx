import React, { Component, ReactNode, ErrorInfo } from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error details
    console.error('React Error Boundary caught an error:', error);
    console.error('Error info:', errorInfo);

    this.setState({
      hasError: true,
      error,
      errorInfo
    });

    // Re-throw the error to ensure it's not silently handled
    throw new Error(`React component error: ${error.message}. Stack: ${errorInfo.componentStack}`);
  }

  render() {
    if (this.state.hasError) {
      // Custom error UI
      return this.props.fallback || (
        <div style={{
          padding: '20px',
          background: 'rgba(248, 113, 113, 0.1)',
          border: '1px solid #f87171',
          borderRadius: '8px',
          color: '#f87171',
          fontFamily: 'monospace'
        }}>
          <h2>React Component Error</h2>
          <p><strong>Error:</strong> {this.state.error?.message}</p>
          <details style={{ marginTop: '10px' }}>
            <summary>Error Details</summary>
            <pre style={{
              background: 'rgba(0, 0, 0, 0.3)',
              padding: '10px',
              borderRadius: '4px',
              fontSize: '12px',
              whiteSpace: 'pre-wrap',
              overflow: 'auto',
              maxHeight: '300px'
            }}>
              {this.state.error?.stack}
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}