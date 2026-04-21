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
    <div className="space-y-4">
      {error && <p className="text-red-600 text-sm mb-4 font-medium flex items-center gap-2">⚠️ {error}</p>}

      {result && (
        <div className={`p-4 rounded-lg border mb-3 ${
          result.status === 'completed' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <p className="font-bold text-sm text-slate-800">Status: {result.status.toUpperCase()}</p>
            {result.status === 'completed' && <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />}
          </div>
          <p className="text-xs text-slate-600 leading-relaxed mb-3">{result.reason}</p>
          {result.metrics && (
            <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-200/50">
              <div className="bg-white/50 p-2 rounded border border-slate-100">
                <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Quality</p>
                <p className="text-sm font-extrabold text-slate-700">{result.metrics.quality_score?.toFixed(1)}%</p>
              </div>
              <div className="bg-white/50 p-2 rounded border border-slate-100">
                <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">FP Rate</p>
                <p className="text-sm font-extrabold text-slate-700">{result.metrics.fp_rate?.toFixed(2)}%</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}