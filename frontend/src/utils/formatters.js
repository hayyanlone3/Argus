// src/utils/formatters.js

export const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString();
};

export const formatTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleTimeString();
};

export const formatBytes = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

export const formatHash = (hash, length = 16) => {
  if (!hash) return 'N/A';
  return hash.substring(0, length) + '...';
};

export const formatPath = (path, maxLength = 50) => {
  if (!path) return 'N/A';
  if (path.length <= maxLength) return path;
  return path.substring(0, maxLength - 3) + '...';
};

export const formatPercent = (value, decimals = 1) => {
  if (typeof value !== 'number') return 'N/A';
  return (value * 100).toFixed(decimals) + '%';
};

export const formatSeconds = (seconds) => {
  if (!seconds) return '0s';
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (minutes === 0) return `${secs}s`;
  return `${minutes}m ${secs}s`;
};