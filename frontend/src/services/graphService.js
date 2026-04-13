// src/services/graphService.js
/**
 * Graph Service
 * Handles graph node and edge operations
 */

import apiClient from '../config/api';

export const graphService = {
  // ═══════════════════════════════════════════════════════════════
  // NODES
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get all nodes
   */
  getNodes: async (limit = 100, nodeType = null) => {
    const params = { limit };
    if (nodeType) params.node_type = nodeType;

    const response = await apiClient.get('/layer1/nodes', { params });
    return response.data;
  },

  /**
   * Get single node
   */
  getNode: async (nodeId) => {
    const response = await apiClient.get(`/layer1/nodes/${nodeId}`);
    return response.data;
  },

  /**
   * Create node
   */
  createNode: async (nodeData) => {
    const response = await apiClient.post('/layer1/nodes', nodeData);
    return response.data;
  },

  /**
   * Get nodes by type
   */
  getNodesByType: async (type, limit = 100) => {
    return graphService.getNodes(limit, type);
  },

  // ═══════════════════════════════════════════════════════════════
  // EDGES
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get all edges
   */
  getEdges: async (limit = 100, edgeType = null, sessionId = null) => {
    const params = { limit };
    if (edgeType) params.edge_type = edgeType;
    if (sessionId) params.session_id = sessionId;

    const response = await apiClient.get('/layer1/edges', { params });
    return response.data;
  },

  /**
   * Get single edge
   */
  getEdge: async (edgeId) => {
    const response = await apiClient.get(`/layer1/edges/${edgeId}`);
    return response.data;
  },

  /**
   * Create edge
   */
  createEdge: async (edgeData) => {
    const response = await apiClient.post('/layer1/edges', edgeData);
    return response.data;
  },

  /**
   * Get edges by type
   */
  getEdgesByType: async (edgeType, limit = 100) => {
    return graphService.getEdges(limit, edgeType);
  },

  /**
   * Get edges by session
   */
  getEdgesBySession: async (sessionId, limit = 100) => {
    return graphService.getEdges(limit, null, sessionId);
  },

  // ═══════════════════════════════════════════════════════════════
  // GRAPH TRAVERSAL
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get node neighbors within N hops
   */
  getNeighbors: async (nodeId, hops = 2) => {
    const response = await apiClient.get(`/layer1/neighbors/${nodeId}`, {
      params: { hops },
    });
    return response.data;
  },

  /**
   * Get path to root (process parent chain)
   */
  getPathToRoot: async (nodeId) => {
    const response = await apiClient.get(`/layer1/path-to-root/${nodeId}`);
    return response.data;
  },

  // ═══════════════════════════════════════════════════════════════
  // STATISTICS
  // ═══════════════════════════════════════════════════════════════

  /**
   * Get graph statistics
   */
  getStats: async () => {
    const response = await apiClient.get('/layer1/stats');
    return response.data;
  },

  /**
   * Get total node count
   */
  getNodeCount: async () => {
    const stats = await graphService.getStats();
    return stats.total_nodes || 0;
  },

  /**
   * Get total edge count
   */
  getEdgeCount: async () => {
    const stats = await graphService.getStats();
    return stats.total_edges || 0;
  },

  // ═══════════════════════════════════════════════════════════════
  // REAL-TIME STREAMING
  // ═══════════════════════════════════════════════════════════════

  /**
   * Subscribe to graph updates via SSE
   * Returns EventSource object
   */
  streamUpdates: (onUpdate, onError) => {
    const eventSource = new EventSource(`${apiClient.defaults.baseURL}/layer1/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onUpdate?.(data);
      } catch (err) {
        console.error('Failed to parse SSE data:', err);
      }
    };

    eventSource.onerror = () => {
      onError?.('Stream connection lost');
      eventSource.close();
    };

    return eventSource;
  },
};