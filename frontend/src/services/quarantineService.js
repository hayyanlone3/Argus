// src/services/quarantineService.js
/**
 * Quarantine Service
 * Handles file quarantine and restoration
 */

import apiClient from '../config/api';

export const quarantineService = {
  quarantineFile: async (quarantineData) => {
    const response = await apiClient.post('/layer4/quarantine', quarantineData);
    return response.data;
  },

  getQuarantined: async (limit = 100) => {
    const response = await apiClient.get('/layer4/quarantine', { params: { limit } });
    return response.data;
  },

  /**
   * Get single quarantine record
   */
  getQuarantineRecord: async (quarantineId) => {
    const response = await apiClient.get(`/layer4/quarantine/${quarantineId}`);
    return response.data;
  },

  /**
   * Restore quarantined file
   */
  restoreFile: async (quarantineId, restoreData) => {
    const response = await apiClient.post(
      `/layer4/quarantine/${quarantineId}/restore`,
      restoreData
    );
    return response.data;
  },

  /**
   * Restore with reason
   */
  restoreWithReason: async (quarantineId, reason) => {
    return quarantineService.restoreFile(quarantineId, {
      restore_reason: reason,
    });
  },

  // ═══════════════════════════════════════════════════════════════
  // STATISTICS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get quarantine statistics
   */
  getStats: async () => {
    const response = await apiClient.get('/layer4/quarantine/stats');
    return response.data;
  },

  /**
   * Get total quarantined count
   */
  getQuarantinedCount: async () => {
    const stats = await quarantineService.getStats();
    return stats.total_quarantined || 0;
  },

  /**
   * Get quarantine by detection layer
   */
  getQuarantineByLayer: async () => {
    const stats = await quarantineService.getStats();
    return stats.by_detection_layer || {};
  },

  filterByHash: async (hash, limit = 100) => {
    const all = await quarantineService.getQuarantined(limit);
    return all.quarantine.filter((q) => q.hash_sha256 === hash);
  },

  filterByPath: async (path, limit = 100) => {
    const all = await quarantineService.getQuarantined(limit);
    return all.quarantine.filter((q) => q.original_path.includes(path));
  },

  filterByLayer: async (layer, limit = 100) => {
    const all = await quarantineService.getQuarantined(limit);
    return all.quarantine.filter((q) => q.detection_layer === layer);
  },
};