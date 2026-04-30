// src/components/common/Header.jsx
import React from 'react';
import { Link } from 'react-router-dom';

export default function Header() {
  return (
    <header className="bg-gray-900 text-white shadow-lg">
      <div className="max-w-full mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          </div>
          <div>
            <h1 className="text-2xl font-bold">ARGUS</h1>
            <p className="text-xs text-gray-400">Provenance Graph Anomaly Detection</p>
          </div>
        </div>
      
    </header>
  );
}