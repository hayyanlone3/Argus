// src/services/whitelistService.js
/**
 * Whitelist Service
 * Handles whitelist management (3-tier system)
 */

import apiClient from '../config/api';

export const whitelistService = {
  // ═══════════════════════════════════════════════════════════════
  // WHITELIST MANAGEMENT
  // ═══════════════════════════════════════════════════════════════

  /**
   * Add entry to whitelist
   */
  addWhitelist: async (whitelistData) => {
    const response = await apiClient.post('/layer4/whitelist', whitelistData);
    return response.data;
  },

  /**
   * Get all whitelist entries
   */
  getWhitelist: async (tier = null, limit = 100) => {
    const params = { limit };
    if (tier) params.tier = tier;

    const response = await apiClient.get('/layer4/whitelist', { params });
    return response.data;
  },

  /**
   * Get whitelist entries by tier
   */
  getByTier: async (tier, limit = 100) => {
    return whitelistService.getWhitelist(tier, limit);
  },

  /**
   * Check if file is whitelisted
   */
  checkWhitelist: async (filePath, fileHash = null) => {
    const params = { file_path: filePath };
    if (fileHash) params.file_hash = fileHash;

    const response = await apiClient.post('/layer4/whitelist/check', null, { params });
    return response.data;
  },

  /**
   * Remove whitelist entry
   */
  removeWhitelist: async (whitelistId) => {
    const response = await apiClient.delete(`/layer4/whitelist/${whitelistId}`);
    return response.data;
  },

  // ═══════════════════════════════════════════════════════════════
  // STATISTICS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get whitelist statistics
   */
  getStats: async () => {
    const response = await apiClient.get('/layer4/whitelist/stats');
    return response.data;
  },

  /**
   * Get total whitelisted count
   */
  getTotalWhitelisted: async () => {
    const stats = await whitelistService.getStats();
    return stats.total_whitelisted || 0;
  },

  /**
   * Get whitelist breakdown by tier
   */
  getByTierStats: async () => {
    const stats = await whitelistService.getStats();
    return stats.by_tier || {};
  },

  // ═══════════════════════════���═══════════════════════════════════
  // TIER OPERATIONS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Add Tier 1 (path only)
   */
  addTier1: async (path, reason = '', addedBy = '') => {
    return whitelistService.addWhitelist({
      tier: 1,
      path,
      reason,
      added_by: addedBy,
    });
  },

  /**
   * Add Tier 2 (path + hash)
   */
  addTier2: async (path, hash, reason = '', addedBy = '') => {
    return whitelistService.addWhitelist({
      tier: 2,
      path,
      hash_sha256: hash,
      reason,
      added_by: addedBy,
    });
  },

  /**
   * Add Tier 3 (hash only)
   */
  addTier3: async (hash, reason = '', addedBy = '') => {
    return whitelistService.addWhitelist({
      tier: 3,
      path: '',
      hash_sha256: hash,
      reason,
      added_by: addedBy,
    });
  },

  // ═══════════════════════════════════════════════════════════════
  // FILTERS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Filter by path
   */
  filterByPath: async (pathKeyword, limit = 100) => {
    const all = await whitelistService.getWhitelist(null, limit);
    return all.whitelist.filter((w) => w.path.includes(pathKeyword));
  },

  /**
   * Filter by hash
   */
  filterByHash: async (hash, limit = 100) => {
    const all = await whitelistService.getWhitelist(null, limit);
    return all.whitelist.filter((w) => w.hash_sha256 === hash);
  },
};