// src/components/learning/RetrainingLog.jsx
import React, { useState } from 'react';
import { learningService } from '../../services/learningService';

export default function RetrainingLog() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleRetrain = async () => {
    try {
      setLoading(true);
      const data = await learningService.retrain();
      setResult(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-lg">🔄 Retraining</h3>
        <button
          onClick={handleRetrain}
          disabled={loading}
          className="btn-primary btn-sm"
        >
          {loading ? 'Retraining...' : 'Manual Retrain'}
        </button>
      </div>

      <p className="text-sm text-gray-600 mb-4">
        Automatic weekly retraining: <strong>Friday 23:00 UTC</strong>
      </p>

      {error && <p className="text-critical text-sm mb-3">{error}</p>}

      {result && (
        <div className={`p-3 rounded-lg border mb-3 ${
          result.status === 'completed' ? 'border-benign bg-green-50' : 'border-critical bg-red-50'
        }`}>
          <p className="font-semibold text-sm mb-1">Status: {result.status}</p>
          <p className="text-xs text-gray-700">{result.reason}</p>
          {result.metrics && (
            <div className="text-xs text-gray-600 mt-2 space-y-1">
              <p>Quality: {result.metrics.quality_score?.toFixed(1)}/100</p>
              <p>FP Rate: {result.metrics.fp_rate?.toFixed(2)}%</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}