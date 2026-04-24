// src/components/learning/FPRateChart.jsx
import React, { useEffect, useState } from 'react';
import { learningService } from '../../services/learningService';
import LoadingSpinner from '../common/LoadingSpinner';

export default function FPRateChart() {
  const [quality, setQuality] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchQuality = async () => {
      try {
        setLoading(true);
        const data = await learningService.getFeedbackQuality();
        setQuality(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchQuality();
    const interval = setInterval(fetchQuality, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="card border border-red-600 text-red-600">Error: {error}</div>;

  const fpRate = quality?.false_positive_rate_percent || 0;
  const status = fpRate < 5 ? '  Good' : fpRate < 10 ? '   Acceptable' : '  High';

  return (
    <div className="card">
      <h3 className="font-bold text-lg mb-4">False Positive Rate</h3>

      <div className="text-center mb-4">
        <div className="text-4xl font-bold text-red-600 mb-2">{fpRate.toFixed(1)}%</div>
        <p className="text-sm text-gray-600">{status}</p>
      </div>

      <div className="grid grid-cols-3 gap-3 text-sm">
        <div className="bg-green-50 p-3 rounded-lg text-center">
          <p className="text-2xl font-bold text-green-600">{quality?.breakdown?.true_positives}</p>
          <p className="text-xs text-gray-600">True Positives</p>
        </div>
        <div className="bg-red-50 p-3 rounded-lg text-center">
          <p className="text-2xl font-bold text-red-600">{quality?.breakdown?.false_positives}</p>
          <p className="text-xs text-gray-600">False Positives</p>
        </div>
        <div className="bg-blue-50 p-3 rounded-lg text-center">
          <p className="text-2xl font-bold text-unknown">{quality?.breakdown?.unknown}</p>
          <p className="text-xs text-gray-600">Unknown</p>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t text-xs text-gray-600">
        <p>Feedback Rate: <strong>{quality?.feedback_rate_percent?.toFixed(1)}%</strong></p>
        <p className="text-gray-500 mt-1">Higher feedback helps improve the model</p>
      </div>
    </div>
  );
}