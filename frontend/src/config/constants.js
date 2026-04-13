// src/config/constants.js
/**
 * Global constants for ARGUS Dashboard
 */

// ═══════════════════════════════════════════════════════════════
// SEVERITY COLORS & STYLING
// ═══════════════════════════════════════════════════════════════

export const SEVERITY_COLORS = {
  CRITICAL: '#dc3545',
  WARNING: '#ffc107',
  UNKNOWN: '#17a2b8',
  BENIGN: '#28a745',
};

export const SEVERITY_BG = {
  CRITICAL: 'bg-red-50',
  WARNING: 'bg-yellow-50',
  UNKNOWN: 'bg-blue-50',
  BENIGN: 'bg-green-50',
};

export const SEVERITY_BADGE = {
  CRITICAL: 'badge-critical',
  WARNING: 'badge-warning',
  UNKNOWN: 'badge-unknown',
  BENIGN: 'badge-benign',
};

export const SEVERITY_BORDER = {
  CRITICAL: 'border-l-4 border-red-500',
  WARNING: 'border-l-4 border-yellow-500',
  UNKNOWN: 'border-l-4 border-blue-500',
  BENIGN: 'border-l-4 border-green-500',
};

// ═══════════════════════════════════════════════════════════════
// LAYER COLORS & NAMES
// ═══════════════════════════════════════════════════════════════

export const LAYER_COLORS = {
  0: '#6f42c1',
  1: '#0dcaf0',
  2: '#fd7e14',
  3: '#0d6efd',
  4: '#198754',
  5: '#6c757d',
};

export const LAYER_NAMES = {
  0: 'Bouncer',
  1: 'Graph Engine',
  2: 'Scoring',
  3: 'Correlator',
  4: 'Response',
  5: 'Learning',
};

export const LAYER_DESCRIPTIONS = {
  0: 'Fast-path file rejection via entropy, VT lookup, signatures',
  1: 'Provenance graph construction from ETW events',
  2: 'Parallel anomaly detection: Math, Statistical, ML',
  3: 'Group related events into incidents',
  4: 'Quarantine, whitelist, process isolation',
  5: 'Continuous model improvement via retraining',
};

export const LAYER_ICONS = {
  0: '🔒',
  1: '🌳',
  2: '📈',
  3: '🔗',
  4: '🛡️',
  5: '🧠',
};

// ═══════════════════════════════════════════════════════════════
// EDGE TYPES
// ═══════════════════════════════════════════════════════════════

export const EDGE_TYPES = [
  'SPAWNED',
  'READ',
  'WROTE',
  'INJECTED_INTO',
  'EXECUTED_SCRIPT',
  'SUBSCRIBED_WMI',
  'MODIFIED_REG',
  'DISABLED_AMSI',
];

export const EDGE_TYPE_ICONS = {
  SPAWNED: '👶',
  READ: '📖',
  WROTE: '✏️',
  INJECTED_INTO: '💉',
  EXECUTED_SCRIPT: '⚙️',
  SUBSCRIBED_WMI: '📡',
  MODIFIED_REG: '🔧',
  DISABLED_AMSI: '🚫',
};

export const EDGE_TYPE_COLORS = {
  SPAWNED: '#0dcaf0',
  READ: '#6c757d',
  WROTE: '#6c757d',
  INJECTED_INTO: '#dc3545',
  EXECUTED_SCRIPT: '#ffc107',
  SUBSCRIBED_WMI: '#17a2b8',
  MODIFIED_REG: '#ffc107',
  DISABLED_AMSI: '#dc3545',
};

// ═══════════════════════════════════════════════════════════════
// NODE TYPES
// ═══════════════════════════════════════════════════════════════

export const NODE_TYPES = [
  'process',
  'file',
  'script',
  'wmi_object',
  'reg_key',
];

export const NODE_TYPE_ICONS = {
  process: '⚙️',
  file: '📄',
  script: '📜',
  wmi_object: '📡',
  reg_key: '🔑',
};

export const NODE_TYPE_COLORS = {
  process: '#0d6efd',
  file: '#6c757d',
  script: '#ffc107',
  wmi_object: '#17a2b8',
  reg_key: '#6f42c1',
};

// ═══════════════════════════════════════════════════════════════
// MITRE ATT&CK STAGES
// ═══════════════════════════════════════════════════════════════

export const MITRE_STAGES = [
  'Reconnaissance',
  'Resource Development',
  'Initial Access',
  'Execution',
  'Persistence',
  'Privilege Escalation',
  'Defense Evasion',
  'Credential Access',
  'Discovery',
  'Lateral Movement',
  'Collection',
  'Command and Control',
  'Exfiltration',
  'Impact',
];

export const MITRE_COLORS = {
  'Execution': '#dc3545',
  'Defense Evasion': '#ffc107',
  'Persistence': '#fd7e14',
  'Privilege Escalation': '#ff6b6b',
  'Credential Access': '#ee5a6f',
  'Discovery': '#0dcaf0',
  'Lateral Movement': '#0d6efd',
  'Command and Control': '#6f42c1',
  'Exfiltration': '#198754',
  'Collection': '#20c997',
};

// ═══════════════════════════════════════════════════════════════
// STATUS VALUES
// ═══════════════════════════════════════════════════════════════

export const INCIDENT_STATUSES = [
  'OPEN',
  'ACKNOWLEDGED',
  'FP',
  'TP',
  'RESOLVED',
];

export const INCIDENT_STATUS_ICONS = {
  OPEN: '🔴',
  ACKNOWLEDGED: '🟡',
  FP: '✅',
  TP: '⚠️',
  RESOLVED: '✔️',
};

export const INCIDENT_STATUS_COLORS = {
  OPEN: 'text-critical',
  ACKNOWLEDGED: 'text-warning',
  FP: 'text-benign',
  TP: 'text-unknown',
  RESOLVED: 'text-benign',
};

// ═══════════════════════════════════════════════════════════════
// FEEDBACK TYPES
// ═══════════════════════════════════════════════════════════════

export const FEEDBACK_TYPES = {
  TP: { label: 'True Positive', color: 'text-critical', icon: '⚠️' },
  FP: { label: 'False Positive', color: 'text-benign', icon: '✅' },
  UNKNOWN: { label: 'Unknown', color: 'text-unknown', icon: '❓' },
};

// ═══════════════════════════════════════════════════════════════
// WHITELIST TIERS
// ═══════════════════════════════════════════════════════════════

export const WHITELIST_TIERS = {
  1: {
    name: 'Tier 1: Path Only',
    description: 'Path-only matching (lowest false positives)',
    color: 'border-green-500',
    bg: 'bg-green-50',
    icon: '🟢',
  },
  2: {
    name: 'Tier 2: Path + Hash',
    description: 'Path AND hash match required (version-controlled)',
    color: 'border-blue-500',
    bg: 'bg-blue-50',
    icon: '🔵',
  },
  3: {
    name: 'Tier 3: Hash Only',
    description: 'Hash-only matching (file moved to different location)',
    color: 'border-purple-500',
    bg: 'bg-purple-50',
    icon: '🟣',
  },
};

// ═══════════════════════════════════════════════════════════════
// PAGE NAVIGATION
// ═══════════════════════════════════════════════════════════════

export const NAV_ITEMS = [
  { path: '/', label: '📊 Dashboard', color: 'text-gray-600' },
  { path: '/layer0', label: '🔒 Layer 0: Bouncer', color: 'text-layer0' },
  { path: '/layer1', label: '🌳 Layer 1: Graph', color: 'text-layer1' },
  { path: '/layer2', label: '📈 Layer 2: Scoring', color: 'text-layer2' },
  { path: '/layer3', label: '🔗 Layer 3: Correlator', color: 'text-layer3' },
  { path: '/layer4', label: '🛡️ Layer 4: Response', color: 'text-layer4' },
  { path: '/layer5', label: '🧠 Layer 5: Learning', color: 'text-layer5' },
];

// ═══════════════════════════════════════════════════════════════
// API ENDPOINTS (relative to base URL)
// ═══════════════════════════════════════════════════════════════

export const API_ENDPOINTS = {
  // Layer 0
  LAYER0_HEALTH: '/layer0/health',
  LAYER0_VT_LOOKUP: '/layer0/vt-lookup',
  LAYER0_ENTROPY_CHECK: '/layer0/entropy-check',
  LAYER0_ANALYZE_FILE: '/layer0/analyze-file',
  LAYER0_VT_CACHE: '/layer0/vt-cache',

  // Layer 1
  LAYER1_HEALTH: '/layer1/health',
  LAYER1_NODES: '/layer1/nodes',
  LAYER1_EDGES: '/layer1/edges',
  LAYER1_NEIGHBORS: '/layer1/neighbors',
  LAYER1_STATS: '/layer1/stats',
  LAYER1_STREAM: '/layer1/stream',

  // Layer 3
  LAYER3_INCIDENTS: '/layer3/incidents',
  LAYER3_STATS: '/layer3/stats',

  // Layer 4
  LAYER4_QUARANTINE: '/layer4/quarantine',
  LAYER4_WHITELIST: '/layer4/whitelist',
  LAYER4_ISOLATE: '/layer4/isolate',

  // Layer 5
  LAYER5_STATS: '/layer5/stats',
  LAYER5_RETRAIN: '/layer5/retrain',
  LAYER5_MODEL_INFO: '/layer5/model-info',
  LAYER5_FEEDBACK_QUALITY: '/layer5/feedback-quality',
  LAYER5_TRAINING_PROGRESS: '/layer5/training-progress',
};

// ═══════════════════════════════════════════════════════════════
// PAGINATION & LIMITS
// ═══════════════════════════════════════════════════════════════

export const PAGINATION = {
  DEFAULT_LIMIT: 50,
  MAX_LIMIT: 1000,
  INCIDENT_FEED_LIMIT: 20,
  QUARANTINE_LIMIT: 100,
  WHITELIST_LIMIT: 100,
  EDGES_LIMIT: 100,
  NODES_LIMIT: 100,
};

// ═══════════════════════════════════════════════════════════════
// THRESHOLDS & ALERTS
// ═══════════════════════════════════════════════════════════════

export const THRESHOLDS = {
  FP_RATE_WARNING: 5,      // % above which to warn
  FP_RATE_CRITICAL: 10,    // % above which to critical
  CONFIDENCE_LOW: 0.3,
  CONFIDENCE_MEDIUM: 0.6,
  CONFIDENCE_HIGH: 0.8,
  ENTROPY_THRESHOLD: 7.9,
  SPAWN_RATE_SIGMA: 3.0,
};

// ═══════════════════════════════════════════════════════════════
// REFRESH INTERVALS (milliseconds)
// ═══════════════════════════════════════════════════════════════

export const REFRESH_INTERVALS = {
  DASHBOARD: 30000,    // 30 seconds
  INCIDENTS: 10000,    // 10 seconds
  GRAPH: 20000,        // 20 seconds
  QUARANTINE: 20000,   // 20 seconds
  WHITELIST: 30000,    // 30 seconds
  LEARNING: 60000,     // 60 seconds
};

// ═══════════════════════════════════════════════════════════════
// DATE/TIME FORMATS
// ════���══════════════════════════════════════════════════════════

export const DATE_FORMATS = {
  FULL: 'YYYY-MM-DD HH:mm:ss',
  DATE_ONLY: 'YYYY-MM-DD',
  TIME_ONLY: 'HH:mm:ss',
  SHORT: 'MM-DD HH:mm',
};

// ═══════════════════════════════════════════════════════════════
// LOCAL STORAGE KEYS
// ═══════════════════════════════════════════════════════════════

export const STORAGE_KEYS = {
  AUTH_TOKEN: 'argus_auth_token',
  USER_PREFERENCES: 'argus_user_preferences',
  LAST_VISIT: 'argus_last_visit',
  SIDEBAR_COLLAPSED: 'argus_sidebar_collapsed',
  DARK_MODE: 'argus_dark_mode',
  INCIDENT_FILTER: 'argus_incident_filter',
};