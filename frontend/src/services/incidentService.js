// src/services/incidentService.js
/**
 * Incident Service
 * Handles all incident-related API calls
 */

import apiClient from '../config/api';

export const incidentService = {
  // ═══════════════════════════════════════════════════════════════
  // GET INCIDENTS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get all incidents with optional filtering
   */
  getIncidents: async (severity = null, status = null, limit = 100) => {
    const params = { limit };
    if (severity) params.severity = severity;
    if (status) params.status = status;

    const response = await apiClient.get('/layer3/incidents', { params });
    return response.data;
  },

  /**
   * Get single incident by session ID
   */
  getIncident: async (sessionId) => {
    const response = await apiClient.get(`/layer3/incidents/${sessionId}`);
    return response.data;
  },

  /**
   * Get incidents by status
   */
  getIncidentsByStatus: async (status, limit = 100) => {
    return incidentService.getIncidents(null, status, limit);
  },

  /**
   * Get incidents by severity
   */
  getIncidentsBySeverity: async (severity, limit = 100) => {
    return incidentService.getIncidents(severity, null, limit);
  },

  // ═══════════════════════════════════════════════════════════════
  // UPDATE INCIDENTS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Update incident (status, notes, etc.)
   */
  updateIncident: async (sessionId, updateData) => {
    const response = await apiClient.patch(`/layer3/incidents/${sessionId}`, updateData);
    return response.data;
  },

  /**
   * Update incident status
   */
  updateStatus: async (sessionId, newStatus) => {
    return incidentService.updateIncident(sessionId, { status: newStatus });
  },

  /**
   * Add analyst notes
   */
  addAnalystNotes: async (sessionId, notes) => {
    return incidentService.updateIncident(sessionId, { analyst_notes: notes });
  },

  // ═══════════════════════════════════════════════════════════════
  // FEEDBACK
  // ═══════════════════════════════════════════════════════════════

  /**
   * Submit analyst feedback (TP/FP/UNKNOWN)
   */
  submitFeedback: async (sessionId, feedbackData) => {
    const response = await apiClient.post(
      `/layer3/incidents/${sessionId}/feedback`,
      feedbackData
    );
    return response.data;
  },

  /**
   * Mark incident as true positive
   */
  markTruePositive: async (sessionId, comment = '') => {
    return incidentService.submitFeedback(sessionId, {
      feedback_type: 'TP',
      analyst_comment: comment,
    });
  },

  /**
   * Mark incident as false positive
   */
  markFalsePositive: async (sessionId, comment = '') => {
    return incidentService.submitFeedback(sessionId, {
      feedback_type: 'FP',
      analyst_comment: comment,
    });
  },

  // ═══════════════════════════════════════════════════════════════
  // STATISTICS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get incident statistics
   */
  getStats: async () => {
    const response = await apiClient.get('/layer3/stats');
    return response.data;
  },

  /**
   * Get MTTI (Mean Time To Identify) average
   */
  getMTTI: async () => {
    const stats = await incidentService.getStats();
    return stats.metrics?.mean_time_to_identify_seconds || 0;
  },

  /**
   * Get false positive rate
   */
  getFPRate: async () => {
    const stats = await incidentService.getStats();
    return stats.metrics?.false_positive_rate_percent || 0;
  },

  // ═══════════════════════════════════════════════════════════════
  // RESPONSE ACTIONS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Terminate process by PID
   */
  terminateProcess: async (pid) => {
    const response = await apiClient.post(`/layer4/isolate/process/${pid}?force=true`);
    return response.data;
  },
};