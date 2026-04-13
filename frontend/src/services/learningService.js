// src/services/learningService.js
/**
 * Learning Service
 * Handles model training, retraining, and statistics
 */

import apiClient from '../config/api';

export const learningService = {
  // ═══════════════════════════════════════════════════════════════
  // MODEL STATISTICS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get overall learning statistics
   */
  getStats: async () => {
    const response = await apiClient.get('/layer5/stats');
    return response.data;
  },

  /**
   * Get weekly statistics
   */
  getWeeklyStats: async () => {
    const stats = await learningService.getStats();
    return stats.weekly_stats || {};
  },

  /**
   * Get all-time statistics
   */
  getAllTimeStats: async () => {
    const stats = await learningService.getStats();
    return stats.all_time_stats || {};
  },

  /**
   * Get model quality evaluation
   */
  getModelQuality: async () => {
    const stats = await learningService.getStats();
    return stats.model_quality || {};
  },

  // ════════���══════════════════════════════════════════════════════
  // RETRAINING
  // ═══════════════════════════════════════════════════════════════

  /**
   * Manually trigger retraining
   */
  retrain: async () => {
    const response = await apiClient.post('/layer5/retrain');
    return response.data;
  },

  /**
   * Get model information
   */
  getModelInfo: async () => {
    const response = await apiClient.get('/layer5/model-info');
    return response.data;
  },

  // ═══════════════════════════════════════════════════════════════
  // FEEDBACK QUALITY
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get feedback quality metrics
   */
  getFeedbackQuality: async () => {
    const response = await apiClient.get('/layer5/feedback-quality');
    return response.data;
  },

  /**
   * Get false positive rate
   */
  getFPRate: async () => {
    const quality = await learningService.getFeedbackQuality();
    return quality.false_positive_rate_percent || 0;
  },

  /**
   * Get feedback breakdown
   */
  getFeedbackBreakdown: async () => {
    const quality = await learningService.getFeedbackQuality();
    return quality.breakdown || {};
  },

  /**
   * Get feedback rate
   */
  getFeedbackRate: async () => {
    const quality = await learningService.getFeedbackQuality();
    return quality.feedback_rate_percent || 0;
  },

  // ═══════════════════════════════════════════════════════════════
  // TRAINING PROGRESS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get training progress
   */
  getTrainingProgress: async () => {
    const response = await apiClient.get('/layer5/training-progress');
    return response.data;
  },

  /**
   * Get model maturity percentage
   */
  getModelMaturity: async () => {
    const progress = await learningService.getTrainingProgress();
    return progress.model_maturity_percent || 0;
  },

  /**
   * Get days deployed
   */
  getDaysDeployed: async () => {
    const progress = await learningService.getTrainingProgress();
    return progress.days_deployed || 0;
  },

  /**
   * Get incident distribution
   */
  getIncidentDistribution: async () => {
    const progress = await learningService.getTrainingProgress();
    return progress.incident_distribution || {};
  },

  // ═══════════════════════════════════════════════════════════════
  // METRICS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get TP (true positive) count
   */
  getTPCount: async () => {
    const stats = await learningService.getStats();
    return stats.weekly_stats?.tp_count || 0;
  },

  /**
   * Get FP (false positive) count
   */
  getFPCount: async () => {
    const stats = await learningService.getStats();
    return stats.weekly_stats?.fp_count || 0;
  },

  /**
   * Get data quality percentage
   */
  getDataQuality: async () => {
    const stats = await learningService.getStats();
    return stats.weekly_stats?.data_quality_percent || 0;
  },

  /**
   * Check if model is ready for production
   */
  isReadyForProduction: async () => {
    const quality = await learningService.getModelQuality();
    return quality.ready_for_production || false;
  },

  /**
   * Get recommendations
   */
  getRecommendations: async () => {
    const quality = await learningService.getModelQuality();
    return quality.recommendations || [];
  },
};