# LAYER 0: BOUNCER THRESHOLDS

ENTROPY_THRESHOLD_HIGH = 7.9
ENTROPY_THRESHOLD_MEDIUM = 7.0
P_MATRIX_ANOMALY_THRESHOLD = 0.001
VT_POSITIVE_THRESHOLD = 0.1  # >10% AV engines detect = BLOCK

# LAYER 2: SCORING THRESHOLDS

# Layer 2A (Math Certainty)
SPAWN_RATE_SIGMA = 3.0
RENAME_BURST_THRESHOLD = 0.80  # >80% files renamed
EDGE_BURST_SIGMA = 3.0

# Layer 2B (Statistical)
PMATRIX_THRESHOLD_ANOMALY = 0.001  # P < 0.001 = anomalous

# LAYER 2C (ML Graph) - FIXED THRESHOLDS
ML_THRESHOLD_HIGH = 0.90      # River fast-path threshold
ML_THRESHOLD_MEDIUM = 0.70    # River warning threshold  
ML_THRESHOLD_LOW = 0.50       # River detection threshold

# VOTING LOGIC THRESHOLDS

DECISION_CRITICAL_MATH_ML = (0.85, 0.80)  # Increased from (0.7, 0.75) - more strict
DECISION_CRITICAL_STAT_ML = (0.90, 0.85)  # Increased from (0.8, 0.70) - more strict
DECISION_WARNING_MATH = 0.80  # Increased from 0.7
DECISION_WARNING_STAT = 0.85  # Increased from 0.8
DECISION_WARNING_ML = 0.90  # Increased from 0.85
DECISION_UNKNOWN_ML_MIN = 0.70  # Increased from 0.60
DECISION_UNKNOWN_ML_MAX = 0.85

# CORRELATION THRESHOLDS (Layer 3)

CORRELATION_MAX_HOPS = 2
CORRELATION_REQUIRE_SIGNALS = 2  # 2 of 3 signals

# Signal weights
SIGNAL_PROXIMITY_WEIGHT = 0.40
SIGNAL_TREE_ROOT_WEIGHT = 0.35
SIGNAL_HASH_WEIGHT = 0.25

# GRAPH CONFIGURATION (Layer 1)
ACTIVE_WINDOW_HOURS = 24
ARCHIVE_RETENTION_DAYS = 30

# LEARNING CONFIGURATION (Layer 5)
LEARNING_RETRAINING_DAY = "Friday"
LEARNING_RETRAINING_TIME = "23:00"  # UTC
LEARNING_FP_RATE_THRESHOLD = 0.05
LEARNING_RETRAIN_BATCH_SIZE = 500

# REGISTRY PATHS TO MONITOR (Smart Filtering)
MONITORED_REGISTRY_PATHS = {
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce",
    r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run",
    r"HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce",
    r"HKLM\System\CurrentControlSet\Services",
    r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\Winlogon",
    r"HKLM\Software\Microsoft\Windows NT\CurrentVersion\Image File Execution Options",
}

# WHITELIST CONSTRAINTS
NEVER_TIER1_WHITELIST = {
    "powershell.exe",
    "cmd.exe",
    "cscript.exe",
    "wscript.exe",
    "rundll32.exe",
    "regsvr32.exe",
    "mshta.exe",
}

# KNOWN PACKERS (For Entropy Exception)

KNOWN_PACKERS = {
    "UPX",
    "ASPack",
    "Themida",
    "VMProtect",
    "PECompact",
}

# MITRE ATT&CK STAGES

MITRE_STAGES = {
    "reconnaissance": "Reconnaissance",
    "resource_development": "Resource Development",
    "initial_access": "Initial Access",
    "execution": "Execution",
    "persistence": "Persistence",
    "privilege_escalation": "Privilege Escalation",
    "defense_evasion": "Defense Evasion",
    "credential_access": "Credential Access",
    "discovery": "Discovery",
    "lateral_movement": "Lateral Movement",
    "collection": "Collection",
    "command_control": "Command and Control",
    "exfiltration": "Exfiltration",
    "impact": "Impact",
}

# Event kinds used across the system (avoid magic strings)
EVENT_KIND_PROCESS_CREATE = "PROCESS_CREATE"
EVENT_KIND_FILE_CREATE = "FILE_CREATE"
EVENT_KIND_REG_SET = "REG_SET"

# Suspicious file-write patterns for statistical scoring
SUSPICIOUS_FILE_PATH_FRAGMENTS = {
    r"\appdata\local\temp",
    r"\appdata\roaming",
    r"\programdata",
    r"\users\public",
    r"\startup",
}

SUSPICIOUS_FILE_EXTENSIONS = {
    ".exe", ".dll", ".sys", ".scr", ".com",
    ".ps1", ".psm1", ".vbs", ".js", ".jse",
    ".wsf", ".hta", ".bat", ".cmd", ".lnk",
}

# PAGINATION & RATE LIMITING
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000
RATE_LIMIT_REQUESTS = 1000
RATE_LIMIT_PERIOD_SECONDS = 60