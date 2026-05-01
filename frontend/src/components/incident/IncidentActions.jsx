// src/components/incident/IncidentActions.jsx
import React, { useState } from 'react';
import { incidentService } from '../../services/incidentService';

export default function IncidentActions({ incident, onUpdate }) {
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackType, setFeedbackType] = useState('UNKNOWN');
  const [comment, setComment] = useState('');

  const handleStatusChange = async (newStatus) => {
    try {
      setLoading(true);
      setAction(newStatus);
      await incidentService.updateIncident(incident.session_id, { status: newStatus });
      onUpdate?.();
    } catch (error) {
      alert('Error updating incident: ' + error.message);
    } finally {
      setLoading(false);
      setAction('');
    }
  };

  const handleSubmitFeedback = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setAction('FEEDBACK');
      await incidentService.submitFeedback(incident.session_id, {
        feedback_type: feedbackType,
        analyst_comment: comment,
      });
      setShowFeedback(false);
      setComment('');
      onUpdate?.();
    } catch (error) {
      alert('Error submitting feedback: ' + error.message);
    } finally {
      setLoading(false);
      setAction('');
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-black uppercase tracking-widest text-slate-500">Actions</h4>
        <p className="text-xs text-slate-500 mt-1">Update incident status or capture analyst feedback.</p>
      </div>

      <div className="grid gap-2">
        <button
          onClick={() => handleStatusChange('ACKNOWLEDGED')}
          disabled={loading}
          className="w-full rounded-lg bg-slate-900 text-white text-xs font-black uppercase py-2.5 hover:bg-slate-800 disabled:opacity-60"
        >
          {loading && action === 'ACKNOWLEDGED' ? 'Acknowledging...' : 'Acknowledge'}
        </button>
        <button
          onClick={() => setShowFeedback(!showFeedback)}
          disabled={loading}
          className="w-full rounded-lg border border-slate-200 bg-white text-slate-700 text-xs font-black uppercase py-2.5 hover:border-slate-300 hover:bg-slate-50 disabled:opacity-60"
        >
          {showFeedback ? 'Hide Feedback' : 'Submit Feedback'}
        </button>
        <button
          onClick={() => handleStatusChange('RESOLVED')}
          disabled={loading}
          className="w-full rounded-lg bg-emerald-600 text-white text-xs font-black uppercase py-2.5 hover:bg-emerald-500 disabled:opacity-60"
        >
          {loading && action === 'RESOLVED' ? 'Resolving...' : 'Resolve'}
        </button>
      </div>

      {showFeedback && (
        <form onSubmit={handleSubmitFeedback} className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Feedback Type</label>
            <select
              value={feedbackType}
              onChange={(e) => setFeedbackType(e.target.value)}
              className="mt-2 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              <option value="UNKNOWN">Unknown</option>
              <option value="TP">True Positive</option>
              <option value="FP">False Positive</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Analyst Comment</label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="mt-2 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
              rows="3"
              placeholder="Summarize why this is TP/FP..."
            />
          </div>

          <button type="submit" disabled={loading} className="w-full rounded-lg bg-slate-900 text-white text-xs font-black uppercase py-2.5 hover:bg-slate-800 disabled:opacity-60">
            {loading && action === 'FEEDBACK' ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </form>
      )}
    </div>
  );
}