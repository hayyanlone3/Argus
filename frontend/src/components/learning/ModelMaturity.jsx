// src/components/learning/ModelMaturity.jsx
import React, { useEffect, useState } from 'react';
import { learningService } from '../../services/learningService';
import LoadingSpinner from '../common/LoadingSpinner';

export default function ModelMaturity() {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        setLoading(true);
        const data = await learningService.getTrainingProgress();
        setProgress(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchProgress();
    const interval = setInterval(fetchProgress, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="card border border-critical text-critical">Error: {error}</div>;

  const percent = progress?.model_maturity_percent || 0;

  return (
    <div className="card">
      <h3 className="font-bold text-lg mb-4">🧠 Model Maturity</h3>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold">Progress</span>
          <span className="text-sm font-bold text-critical">{percent.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-critical h-2 rounded-full transition-all duration-500"
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      <div className="text-sm text-gray-600 mb-4">
        <p>Days Deployed: <strong>{progress?.days_deployed}</strong></p>
        <p>Status: <strong>{progress?.status}</strong></p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs">
        <p className="text-blue-800">
          Model matures after 14 days. Current: {progress?.days_deployed} days
        </p>
      </div>
    </div>
  );
}