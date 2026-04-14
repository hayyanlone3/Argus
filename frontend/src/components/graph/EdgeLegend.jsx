// src/components/graph/EdgeLegend.jsx
import React from 'react';

export default function EdgeLegend() {
  const edgeTypes = [
    { type: 'SPAWNED', icon: '👶', color: 'text-blue-600', desc: 'Process spawned' },
    { type: 'READ', icon: '📖', color: 'text-gray-600', desc: 'File read' },
    { type: 'WROTE', icon: '✏️', color: 'text-gray-600', desc: 'File write' },
    { type: 'INJECTED_INTO', icon: '💉', color: 'text-red-600', desc: 'Code injection' },
    { type: 'EXECUTED_SCRIPT', icon: '⚙️', color: 'text-warning', desc: 'Script executed' },
    { type: 'SUBSCRIBED_WMI', icon: '📡', color: 'text-unknown', desc: 'WMI subscription' },
    { type: 'MODIFIED_REG', icon: '🔧', color: 'text-warning', desc: 'Registry modified' },
    { type: 'DISABLED_AMSI', icon: '🚫', color: 'text-red-600', desc: 'AMSI disabled' },
  ];

  return (
    <div className="mt-4 border-t pt-4">
      <h4 className="font-semibold text-sm mb-2">Edge Types</h4>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {edgeTypes.map((et) => (
          <div key={et.type} className="text-xs">
            <span className="mr-1">{et.icon}</span>
            <span className={`${et.color} font-mono`}>{et.type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}