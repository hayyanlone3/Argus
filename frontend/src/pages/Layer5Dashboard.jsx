// src/pages/Layer5Dashboard.jsx
import React from 'react';
import ModelMaturity from '../components/learning/ModelMaturity';
import RetrainingLog from '../components/learning/RetrainingLog';
import FPRateChart from '../components/learning/FPRateChart';

export default function Layer5Dashboard() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1>🧠 Layer 5: Learning Engine</h1>
        <p className="text-gray-600">Continuous model improvement via weekly retraining and feedback</p>
      </div>

      {/* Key Components */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ModelMaturity />
        <RetrainingLog />
      </div>

      {/* False Positive Rate */}
      <FPRateChart />

      {/* Retraining Schedule */}
      <div className="card">
        <h3 className="font-bold text-lg mb-3">📅 Retraining Schedule</h3>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="font-semibold text-blue-900 mb-2">Weekly Automated Retrain</p>
          <p className="text-sm text-blue-800 mb-3">Friday at 23:00 UTC</p>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>✓ Collect verified feedback (TP/FP/UNKNOWN)</li>
            <li>✓ Evaluate model quality (FP rate, data quality)</li>
            <li>✓ Reject if FP rate &gt; 5%</li>
            <li>✓ Retrain models if quality approved</li>
          </ul>
        </div>
      </div>

      {/* Info */}
      <div className="card">
        <h3 className="font-bold text-lg mb-3">📖 About Layer 5</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>✓ <strong>Weekly Retraining:</strong> Automated Friday 23:00 UTC</li>
          <li>✓ <strong>Feedback Loop:</strong> Analyst TP/FP marking drives learning</li>
          <li>✓ <strong>Model Channels:</strong> River HalfSpaceTrees, BETH baseline, P-matrix</li>
          <li>✓ <strong>Quality Metrics:</strong> FP rate, data quality, MTTI tracking</li>
          <li>✓ <strong>Model Maturity:</strong> 100% at 14 days deployment</li>
        </ul>
      </div>

      {/* Performance Targets */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card border-2 border-green-600">
          <p className="text-gray-600 text-sm mb-2">FP Rate Target</p>
          <p className="text-3xl font-bold text-green-600">&lt; 5%</p>
        </div>
        <div className="card border-2 border-unknown">
          <p className="text-gray-600 text-sm mb-2">Data Quality</p>
          <p className="text-3xl font-bold text-unknown">&gt; 30%</p>
        </div>
        <div className="card border-2 border-warning">
          <p className="text-gray-600 text-sm mb-2">Maturity Time</p>
          <p className="text-3xl font-bold text-warning">14 days</p>
        </div>
      </div>
    </div>
  );
}