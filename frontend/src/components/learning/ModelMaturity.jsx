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
  if (error) return <div className="card border border-red-600 text-red-600">Error: {error}</div>;

  const percent = progress?.model_maturity_percent || 0;

  return (
    <div className="card h-full flex flex-col items-center text-center p-8 border border-slate-200 bg-white rounded-2xl shadow-sm">
      <div className="w-full max-w-md">
        <h3 className="font-extrabold text-xl text-slate-800 mb-1 tracking-tight">Model Maturity</h3>
        <p className="text-slate-500 text-sm mb-8 font-medium italic">Establishing baseline behavioral patterns</p>

        <div className="relative mb-8">
          <div className="flex items-end justify-between mb-3 px-1">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Training Progress</span>
            <span className={`text-sm font-black ${percent >= 100 ? 'text-emerald-600' : 'text-indigo-600'}`}>
              {percent.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-4 overflow-hidden border border-slate-200 p-1 shadow-inner">
            <div
              className={`h-full rounded-full transition-all duration-1000 ease-out shadow-sm ${
                percent >= 100 ? 'bg-gradient-to-r from-emerald-500 to-teal-500' : 'bg-gradient-to-r from-indigo-600 to-purple-600'
              }`}
              style={{ width: `${percent}%` }}
            />
          </div>
          {percent < 100 && (
            <div className="mt-2 text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 shadow-sm">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 text-center">Time Elapsed</p>
            <p className="text-xl font-extrabold text-slate-800">{progress?.days_deployed || 0} <span className="text-xs font-medium text-slate-500">Days</span></p>
          </div>
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 shadow-sm">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 text-center">Engine State</p>
            <p className={`text-xl font-bold uppercase tracking-tighter ${progress?.status === 'matured' ? 'text-emerald-600' : 'text-amber-600'}`}>
              {progress?.status || 'Learning'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}