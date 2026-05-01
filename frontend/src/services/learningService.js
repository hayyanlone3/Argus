import apiClient from '../config/api';

export const learningService = {
  // MODEL STATISTICS
  getStats: async () => {
    const response = await apiClient.get('/layer5/stats');
    return response.data;
  },

  getWeeklyStats: async () => {
    const stats = await learningService.getStats();
    return stats.weekly_stats || {};
  },

  getAllTimeStats: async () => {
    const stats = await learningService.getStats();
    return stats.all_time_stats || {};
  },

  getModelQuality: async () => {
    const stats = await learningService.getStats();
    return stats.model_quality || {};
  },

  // RETRAINING
  retrain: async () => {
    const response = await apiClient.post('/layer5/retrain');
    return response.data;
  },

  getModelInfo: async () => {
    const response = await apiClient.get('/layer5/model-info');
    return response.data;
  },

  // FEEDBACK QUALITY
  getFeedbackQuality: async () => {
    const response = await apiClient.get('/layer5/feedback-quality');
    return response.data;
  },

  getFPRate: async () => {
    const quality = await learningService.getFeedbackQuality();
    return quality.false_positive_rate_percent || 0;
  },

  getFeedbackBreakdown: async () => {
    const quality = await learningService.getFeedbackQuality();
    return quality.breakdown || {};
  },

  getFeedbackRate: async () => {
    const quality = await learningService.getFeedbackQuality();
    return quality.feedback_rate_percent || 0;
  },

  // TRAINING PROGRESS
  getTrainingProgress: async () => {
    const response = await apiClient.get('/layer5/training-progress');
    return response.data;
  },

  getModelMaturity: async () => {
    const progress = await learningService.getTrainingProgress();
    return progress.model_maturity_percent || 0;
  },

  getDaysDeployed: async () => {
    const progress = await learningService.getTrainingProgress();
    return progress.days_deployed || 0;
  },

  getIncidentDistribution: async () => {
    const progress = await learningService.getTrainingProgress();
    return progress.incident_distribution || {};
  },

  // METRICS
  getTPCount: async () => {
    const stats = await learningService.getStats();
    return stats.weekly_stats?.tp_count || 0;
  },

  getFPCount: async () => {
    const stats = await learningService.getStats();
    return stats.weekly_stats?.fp_count || 0;
  },

  getDataQuality: async () => {
    const stats = await learningService.getStats();
    return stats.weekly_stats?.data_quality_percent || 0;
  },

  isReadyForProduction: async () => {
    const quality = await learningService.getModelQuality();
    return quality.ready_for_production || false;
  },
  
  getRecommendations: async () => {
    const quality = await learningService.getModelQuality();
    return quality.recommendations || [];
  },
};