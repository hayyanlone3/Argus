// src/components/incident/IncidentActions.jsx
import React, { useState } from 'react';
import { incidentService } from '../../services/incidentService';

export default function IncidentActions({ incident, onUpdate }) {
  const [loading, setLoading] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackType, setFeedbackType] = useState('UNKNOWN');
  const [comment, setComment] = useState('');

  const handleStatusChange = async (newStatus) => {
    try {
      setLoading(true);
      await incidentService.updateIncident(incident.session_id, { status: newStatus });
      onUpdate?.();
    } catch (error) {
      alert('Error updating incident: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitFeedback = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
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
    }
  };

  return (
    <div className="card">
      <h4 className="font-bold mb-4">Actions</h4>

      <div className="space-y-2 mb-4">
        <button
          onClick={() => handleStatusChange('ACKNOWLEDGED')}
          disabled={loading}
          className="btn-secondary w-full btn-sm"
        >
            Acknowledge
        </button>
        <button
          onClick={() => setShowFeedback(!showFeedback)}
          disabled={loading}
          className="btn-warning w-full btn-sm"
        >
            Submit Feedback
        </button>
        <button
          onClick={() => handleStatusChange('RESOLVED')}
          disabled={loading}
          className="btn-success w-full btn-sm"
        >
            Resolve
        </button>
      </div>

      {showFeedback && (
        <form onSubmit={handleSubmitFeedback} className="border-t pt-4">
          <div className="form-group">
            <label className="form-label">Feedback Type</label>
            <select
              value={feedbackType}
              onChange={(e) => setFeedbackType(e.target.value)}
              className="form-input"
            >
              <option value="UNKNOWN">Unknown</option>
              <option value="TP">True Positive  </option>
              <option value="FP">False Positive  </option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Comment</label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="form-input"
              rows="3"
              placeholder="Analyst notes..."
            />
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full btn-sm">
            {loading ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </form>
      )}
    </div>
  );
}