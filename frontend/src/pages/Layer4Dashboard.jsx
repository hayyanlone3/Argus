// src/pages/Layer4Dashboard.jsx
import React, { useState } from 'react';
import QuarantineList from '../components/quarantine/QuarantineList';
import WhitelistManager from '../components/whitelist/WhitelistManager';

export default function Layer4Dashboard() {
  const [activeTab, setActiveTab] = useState('quarantine');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1>🛡️  Layer 4: Response Engine</h1>
        <p className="text-gray-600">Automated threat containment: quarantine, whitelist, isolation</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('quarantine')}
          className={`px-4 py-2 rounded-lg font-medium transition-all ${
            activeTab === 'quarantine'
              ? 'bg-red-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          🚫 Quarantine
        </button>
        <button
          onClick={() => setActiveTab('whitelist')}
          className={`px-4 py-2 rounded-lg font-medium transition-all ${
            activeTab === 'whitelist'
              ? 'bg-red-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          ✅ Whitelist
        </button>
        <button
          onClick={() => setActiveTab('about')}
          className={`px-4 py-2 rounded-lg font-medium transition-all ${
            activeTab === 'about'
              ? 'bg-red-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          ℹ️  About
        </button>
      </div>

      {/* Quarantine Tab */}
      {activeTab === 'quarantine' && (
        <div className="space-y-6">
          <QuarantineList />
          <div className="card">
            <h3 className="font-bold text-lg mb-3">Quarantine Directory</h3>
            <p className="text-sm text-gray-600 font-mono bg-gray-50 p-3 rounded">
              C:\ProgramData\ARGUS\quarantine
            </p>
            <p className="text-xs text-gray-600 mt-2">
              Files moved here are safe from execution. Restore after analyst verification.
            </p>
          </div>
        </div>
      )}

      {/* Whitelist Tab */}
      {activeTab === 'whitelist' && (
        <div className="space-y-6">
          <WhitelistManager />
          <div className="card">
            <h3 className="font-bold text-lg mb-3">Tier System</h3>
            <div className="space-y-3 text-sm">
              <div className="border-l-4 border-green-500 pl-3">
                <p className="font-semibold">Tier 1: Path Only</p>
                <p className="text-gray-600">Lowest FP rate, trust path location</p>
              </div>
              <div className="border-l-4 border-blue-500 pl-3">
                <p className="font-semibold">Tier 2: Path + Hash</p>
                <p className="text-gray-600">Version-controlled trust</p>
              </div>
              <div className="border-l-4 border-purple-500 pl-3">
                <p className="font-semibold">Tier 3: Hash Only</p>
                <p className="text-gray-600">Trust specific file version anywhere</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* About Tab */}
      {activeTab === 'about' && (
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-bold text-lg mb-3">📖 Layer 4 Capabilities</h3>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>✓ <strong>File Quarantine:</strong> Move suspicious files to isolated directory</li>
              <li>✓ <strong>Hash Calculation:</strong> SHA256, MD5, SHA1 support</li>
              <li>✓ <strong>Safe Restoration:</strong> Analyst-approved file recovery</li>
              <li>✓ <strong>Whitelist Management:</strong> 3-tier trust system</li>
              <li>✓ <strong>Process Isolation:</strong> Kill malicious processes by PID/name</li>
              <li>✓ <strong>Feedback Loop:</strong> Analyst FP/TP marking for learning</li>
            </ul>
          </div>

          <div className="card">
            <h3 className="font-bold text-lg mb-3">Key Metrics</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="text-gray-600 text-sm">Quarantine Directory</p>
                <p className="text-lg font-bold text-red-600">C:\ProgramData\ARGUS\...</p>
              </div>
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="text-gray-600 text-sm">Auto-Isolation</p>
                <p className="text-lg font-bold text-red-600">CRITICAL severity</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}