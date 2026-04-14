// src/pages/Layer0Dashboard.jsx
import React, { useState } from 'react';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function Layer0Dashboard() {
  const [file, setFile] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file');
      return;
    }

    try {
      setAnalyzing(true);
      setError(null);
      
      // In real implementation, use actual backend API
      // For now, show mock result
      setTimeout(() => {
        setResult({
          status: 'PASS',
          file_hash: 'abc123def456' + Math.random().toString().substring(2),
          entropy: (Math.random() * 8).toFixed(2),
          vt_score: (Math.random() * 0.5).toFixed(3),
          signals: ['Low entropy detected', 'Microsoft signed'],
          message: 'No anomalies detected',
        });
        setAnalyzing(false);
      }, 2000);
    } catch (err) {
      setError(err.message);
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1>🔒 Layer 0: Bouncer</h1>
        <p className="text-gray-600">Fast-path file rejection via entropy, VT lookup, signatures</p>
      </div>

      {/* Analysis Form */}
      <div className="card max-w-2xl">
        <h3 className="font-bold text-lg mb-4">📊 File Analysis</h3>

        <form onSubmit={handleAnalyze} className="space-y-4">
          <div className="form-group">
            <label className="form-label">Select File</label>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0])}
              className="form-input"
            />
          </div>

          {error && <p className="text-red-600 text-sm">{error}</p>}

          <button type="submit" disabled={analyzing} className="btn-primary w-full">
            {analyzing ? 'Analyzing...' : 'Analyze File'}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="card">
          <h3 className="font-bold text-lg mb-4">Analysis Result</h3>

          <div className={`p-4 rounded-lg mb-4 ${
            result.status === 'PASS'
              ? 'bg-green-50 border border-green-200'
              : result.status === 'WARN'
              ? 'bg-yellow-50 border border-yellow-200'
              : 'bg-red-50 border border-red-200'
          }`}>
            <p className="font-bold mb-2">Status: {result.status}</p>
            <p className="text-sm">{result.message}</p>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div>
              <p className="text-gray-600">File Hash</p>
              <p className="font-mono text-xs bg-gray-50 p-2 rounded">{result.file_hash}</p>
            </div>
            <div>
              <p className="text-gray-600">Entropy</p>
              <p className="font-bold">{result.entropy}</p>
            </div>
            <div>
              <p className="text-gray-600">VT Score</p>
              <p className="font-bold">{result.vt_score}</p>
            </div>
            <div>
              <p className="text-gray-600">Threshold</p>
              <p className="font-bold">7.9</p>
            </div>
          </div>

          {result.signals && (
            <div>
              <p className="text-sm font-semibold mb-2">Signals</p>
              <div className="space-y-1">
                {result.signals.map((signal, idx) => (
                  <p key={idx} className="text-xs text-gray-700">✓ {signal}</p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Info */}
      <div className="card">
        <h3 className="font-bold text-lg mb-3">📖 About Layer 0</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>✓ <strong>VirusTotal Lookup:</strong> Query file hash against 70+ AV engines</li>
          <li>✓ <strong>Entropy Analysis:</strong> Multi-tier entropy checking (Tier 2/3)</li>
          <li>✓ <strong>Digital Signatures:</strong> Verify Microsoft-signed binaries</li>
          <li>✓ <strong>Packer Detection:</strong> Identify known packing tools</li>
        </ul>
      </div>
    </div>
  );
}