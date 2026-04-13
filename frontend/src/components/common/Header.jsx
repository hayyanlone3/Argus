// src/components/common/Header.jsx
import React from 'react';
import { Link } from 'react-router-dom';

export default function Header() {
  return (
    <header className="bg-gray-900 text-white shadow-lg">
      <div className="max-w-full mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-critical rounded-lg flex items-center justify-center">
            <span className="text-white font-bold">🔍</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold">ARGUS v2.2</h1>
            <p className="text-xs text-gray-400">Provenance Graph Anomaly Detection</p>
          </div>
        </div>

        <div className="text-right">
          <p className="text-sm text-gray-300">
            <span className="text-critical font-bold">Live</span> • Backend Connected
          </p>
        </div>
      </div>
    </header>
  );
}