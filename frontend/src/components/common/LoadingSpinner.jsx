// src/components/common/LoadingSpinner.jsx
import React from 'react';

export default function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="spinner"></div>
      <span className="ml-3 text-gray-600">Loading...</span>
    </div>
  );
}