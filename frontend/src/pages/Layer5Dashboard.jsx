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

      <div className="max-w-3xl mx-auto space-y-8 py-4">
        <ModelMaturity />
        <RetrainingLog />
      </div>
      <FPRateChart />
      </div>
  );
}