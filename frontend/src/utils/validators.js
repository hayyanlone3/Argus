// src/utils/validators.js

export const validateHash = (hash) => {
  if (!hash) return false;
  return /^[a-f0-9]{64}$/.test(hash.toLowerCase());
};

export const validatePath = (path) => {
  if (!path) return false;
  return path.length > 0 && path.length < 512;
};

export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export const validateConfidence = (value) => {
  return typeof value === 'number' && value >= 0 && value <= 1;
};

export const validateTier = (tier) => {
  return [1, 2, 3].includes(tier);
};

export const validateFeedback = (feedbackType) => {
  return ['TP', 'FP', 'UNKNOWN'].includes(feedbackType);
};