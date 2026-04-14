// src/components/common/Sidebar.jsx
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const navItems = [
    { path: '/', label: '📊 Dashboard', color: 'text-gray-600' },
    { path: '/layer0', label: '🔒 Layer 0: Bouncer', color: 'text-layer0' },
    { path: '/layer1', label: '🌳 Layer 1: Graph', color: 'text-layer1' },
    { path: '/layer2', label: '📈 Layer 2: Scoring', color: 'text-layer2' },
    { path: '/layer3', label: '🔗 Layer 3: Correlator', color: 'text-layer3' },
    { path: '/layer4', label: '🛡️  Layer 4: Response', color: 'text-layer4' },
    { path: '/layer5', label: '🧠 Layer 5: Learning', color: 'text-layer5' },
  ];

  return (
    <aside className="w-64 bg-gray-800 text-white min-h-screen shadow-lg">
      <nav className="p-4 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`block px-4 py-3 rounded-lg transition-all duration-200 ${
              isActive(item.path)
                ? 'bg-red-600 text-white font-semibold'
                : `hover:bg-gray-700 ${item.color}`
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}