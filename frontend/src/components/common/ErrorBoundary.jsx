// src/components/common/ErrorBoundary.jsx
import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="card border border-critical">
          <h3 className="text-critical font-bold mb-2">❌ Error Occurred</h3>
          <p className="text-gray-600 text-sm">{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="btn-secondary btn-sm mt-3"
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}