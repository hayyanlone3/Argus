import apiClient from '../config/api';

export const incidentService = {
  // GET INCIDENTS
  getIncidents: async (severity = null, status = null, limit = 100) => {
    const params = { limit };
    if (severity) params.severity = severity;
    if (status) params.status = status;

    const response = await apiClient.get('/layer3/incidents', { params });
    return response.data;
  },

  getIncident: async (sessionId) => {
    const response = await apiClient.get(`/layer3/incidents/${sessionId}`);
    return response.data;
  },

  getIncidentsByStatus: async (status, limit = 100) => {
    return incidentService.getIncidents(null, status, limit);
  },

  getIncidentsBySeverity: async (severity, limit = 100) => {
    return incidentService.getIncidents(severity, null, limit);
  },

  // UPDATE INCIDENTS

  updateIncident: async (sessionId, updateData) => {
    const response = await apiClient.patch(`/layer3/incidents/${sessionId}`, updateData);
    return response.data;
  },

  updateStatus: async (sessionId, newStatus) => {
    return incidentService.updateIncident(sessionId, { status: newStatus });
  },

  addAnalystNotes: async (sessionId, notes) => {
    return incidentService.updateIncident(sessionId, { analyst_notes: notes });
  },

  // FEEDBACK
  submitFeedback: async (sessionId, feedbackData) => {
    const response = await apiClient.post(
      `/layer3/incidents/${sessionId}/feedback`,
      feedbackData
    );
    return response.data;
  },

  markTruePositive: async (sessionId, comment = '') => {
    return incidentService.submitFeedback(sessionId, {
      feedback_type: 'TP',
      analyst_comment: comment,
    });
  },

  markFalsePositive: async (sessionId, comment = '') => {
    return incidentService.submitFeedback(sessionId, {
      feedback_type: 'FP',
      analyst_comment: comment,
    });
  },

  // STATISTICS
  getStats: async () => {
    const response = await apiClient.get('/layer3/stats');
    return response.data;
  },

  //Get MTTI (Mean Time To Identify) average
  getMTTI: async () => {
    const stats = await incidentService.getStats();
    return stats.metrics?.mean_time_to_identify_seconds || 0;
  },
  
  getFPRate: async () => {
    const stats = await incidentService.getStats();
    return stats.metrics?.false_positive_rate_percent || 0;
  },

  // RESPONSE ACTIONS
  terminateProcess: async (pid) => {
    const response = await apiClient.post(`/layer4/isolate/process/${pid}?force=true`);
    return response.data;
  },
};