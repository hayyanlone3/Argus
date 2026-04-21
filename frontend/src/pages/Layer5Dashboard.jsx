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
        <h1>Layer 5: Learning Engine</h1>
        <p className="text-gray-600">Continuous model improvement via weekly retraining and feedback</p>
      </div>

      {/* Key Components */}
      <div className="max-w-3xl mx-auto space-y-8 py-4">
        <ModelMaturity />
        <RetrainingLog />
      </div>

      {/* False Positive Rate */}
      <FPRateChart />


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