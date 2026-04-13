// src/pages/Layer2Dashboard.jsx
import React, { useState } from 'react';

export default function Layer2Dashboard() {
  const [score2a, setScore2a] = useState(0.5);
  const [score2b, setScore2b] = useState(0.5);
  const [score2c, setScore2c] = useState(0.5);
  const [result, setResult] = useState(null);

  const handleCalculate = () => {
    // Simple voting logic for demo
    let severity = 'BENIGN';
    
    if (score2a > 0.7 && score2c > 0.75) {
      severity = 'CRITICAL';
    } else if ((score2a > 0.7 || score2b > 0.8) && score2c > 0.7) {
      severity = 'CRITICAL';
    } else if (score2a > 0.7 || score2b > 0.8 || score2c > 0.85) {
      severity = 'WARNING';
    } else if (score2a > 0.6 || score2b > 0.6 || score2c > 0.6) {
      severity = 'UNKNOWN';
    }

    const confidence = (score2a + score2b + score2c) / 3;
    
    setResult({ severity, confidence });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1>📈 Layer 2: Scoring Engine</h1>
        <p className="text-gray-600">3-channel anomaly detection: Math • Statistical • ML</p>
      </div>

      {/* Channel Sliders */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Channel 2A */}
        <div className="card">
          <h3 className="font-bold mb-3">2A: Math Certainty</h3>
          <div className="mb-4">
            <input
              type="range"
              min="0"
              max="100"
              value={score2a * 100}
              onChange={(e) => setScore2a(e.target.value / 100)}
              className="w-full"
            />
            <p className="text-2xl font-bold text-critical mt-2">{(score2a * 100).toFixed(0)}%</p>
          </div>
          <div className="text-xs text-gray-600 space-y-1">
            <p>• Spawn rate anomaly</p>
            <p>• File rename burst</p>
            <p>• Edge burst detection</p>
          </div>
        </div>

        {/* Channel 2B */}
        <div className="card">
          <h3 className="font-bold mb-3">2B: Statistical</h3>
          <div className="mb-4">
            <input
              type="range"
              min="0"
              max="100"
              value={score2b * 100}
              onChange={(e) => setScore2b(e.target.value / 100)}
              className="w-full"
            />
            <p className="text-2xl font-bold text-warning mt-2">{(score2b * 100).toFixed(0)}%</p>
          </div>
          <div className="text-xs text-gray-600 space-y-1">
            <p>• BETH baseline</p>
            <p>• P-matrix anomaly</p>
            <p>• Statistical impossibility</p>
          </div>
        </div>

        {/* Channel 2C */}
        <div className="card">
          <h3 className="font-bold mb-3">2C: ML Anomaly</h3>
          <div className="mb-4">
            <input
              type="range"
              min="0"
              max="100"
              value={score2c * 100}
              onChange={(e) => setScore2c(e.target.value / 100)}
              className="w-full"
            />
            <p className="text-2xl font-bold text-unknown mt-2">{(score2c * 100).toFixed(0)}%</p>
          </div>
          <div className="text-xs text-gray-600 space-y-1">
            <p>• River HalfSpaceTrees</p>
            <p>• Graph topology</p>
            <p>• Online learning</p>
          </div>
        </div>
      </div>

      {/* Voting Logic */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-lg">🤖 Voting Logic</h3>
          <button onClick={handleCalculate} className="btn-primary btn-sm">
            Calculate Decision
          </button>
        </div>

        {result && (
          <div className={`p-4 rounded-lg border-2 ${
            result.severity === 'CRITICAL' ? 'border-critical bg-red-50'
            : result.severity === 'WARNING' ? 'border-warning bg-yellow-50'
            : result.severity === 'UNKNOWN' ? 'border-unknown bg-blue-50'
            : 'border-benign bg-green-50'
          }`}>
            <p className="font-bold text-lg mb-1">Decision: {result.severity}</p>
            <p className="text-sm">Confidence: {(result.confidence * 100).toFixed(0)}%</p>
          </div>
        )}
      </div>

      {/* Decision Tree */}
      <div className="card">
        <h3 className="font-bold text-lg mb-4">Decision Tree</h3>
        <div className="space-y-2 text-sm">
          <div className="border-l-4 border-critical pl-3">
            <p className="font-semibold">CRITICAL</p>
            <p className="text-gray-600 text-xs">2A AND 2C both high, OR (2A OR 2B) AND 2C high, OR injection detected</p>
          </div>
          <div className="border-l-4 border-warning pl-3">
            <p className="font-semibold">WARNING</p>
            <p className="text-gray-600 text-xs">Single channel {'>='} threshold, weak multi-signal</p>
          </div>
          <div className="border-l-4 border-unknown pl-3">
            <p className="font-semibold">UNKNOWN</p>
            <p className="text-gray-600 text-xs">Multiple moderate signals, insufficient confidence</p>
          </div>
          <div className="border-l-4 border-benign pl-3">
            <p className="font-semibold">BENIGN</p>
            <p className="text-gray-600 text-xs">No anomalies detected across channels</p>
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="card">
        <h3 className="font-bold text-lg mb-3">📖 About Layer 2</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>✓ <strong>3 Parallel Channels:</strong> Math certainty, statistical impossibility, ML anomaly</li>
          <li>✓ <strong>Voting Logic:</strong> Combine signals for final severity decision</li>
          <li>✓ <strong>Output:</strong> BENIGN | UNKNOWN | WARNING | CRITICAL + confidence</li>
          <li>✓ <strong>Goal:</strong> Reduce false positives while catching true threats</li>
        </ul>
      </div>
    </div>
  );
}