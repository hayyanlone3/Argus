# Malware Simulations - Quick Start

This folder contains executable malware samples that trigger Layer 2 detection in ARGUS.

## 🚀 Quick Start (1-Click Execution)

### Option 1: Run Individual Malware Samples

**Windows (Double-click any of these):**
- `RUN_MALWARE_1.bat` - Process Injection Attack
- `RUN_MALWARE_2.bat` - Registry Persistence & Encryption
- `RUN_MALWARE_3.bat` - PowerShell & Lateral Movement

**Linux/Mac:**
```bash
python malware_sample_1.py
python malware_sample_2.py
python malware_sample_3.py
```

### Option 2: Run All Malware Samples

**Windows (Double-click):**
- `RUN_ALL_MALWARE.bat` - Runs all 3 samples sequentially

**Linux/Mac:**
```bash
python malware_sample_1.py && python malware_sample_2.py && python malware_sample_3.py
```

## 📋 Available Malware Samples

### Malware Sample 1: Process Injection
- **File**: `malware_sample_1.py` or `RUN_MALWARE_1.bat`
- **Attack**: Spawns 5 cmd.exe processes with suspicious commands
- **Triggers**: Spawn rate anomaly, unusual process hierarchy
- **Expected Alerts**: 5-10 CRITICAL alerts

### Malware Sample 2: Registry Persistence & Encryption
- **File**: `malware_sample_2.py` or `RUN_MALWARE_2.bat`
- **Attack**: Modifies registry keys + encrypts files
- **Triggers**: Registry modification patterns, file rename burst
- **Expected Alerts**: 10-15 CRITICAL alerts

### Malware Sample 3: PowerShell & Lateral Movement
- **File**: `malware_sample_3.py` or `RUN_MALWARE_3.bat`
- **Attack**: PowerShell commands + network reconnaissance
- **Triggers**: Suspicious command line, network connections
- **Expected Alerts**: 8-12 CRITICAL alerts

## ✅ Expected Results

When you run any malware sample:

1. **Console Output**: Shows malware execution progress
2. **Dashboard Alerts**: Layer 2 detects CRITICAL severity alerts
3. **Fusion Scores**: 0.8-1.0 confidence
4. **Detection Latency**: <1 second

## 🔧 How to Use

### Step 1: Start ARGUS Backend
```bash
cd backend
python main.py
```
Wait for: `API running on 0.0.0.0:8000`

### Step 2: Run Malware Sample
**Windows**: Double-click `RUN_MALWARE_1.bat` (or any sample)
**Linux/Mac**: `python malware_sample_1.py`

### Step 3: Monitor Dashboard
Open http://localhost:3000 and check Layer 2 for alerts

## 📊 Performance

| Sample | Events | Execution Time | Expected Alerts |
|--------|--------|-----------------|-----------------|
| Sample 1 | ~15 | 2-3 seconds | 5-10 |
| Sample 2 | ~20 | 3-4 seconds | 10-15 |
| Sample 3 | ~18 | 3-4 seconds | 8-12 |
| All 3 | ~53 | 8-11 seconds | 23-37 |

## 🐛 Troubleshooting

**No detections?**
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check Layer 2
curl http://localhost:8000/api/layer2/health

# Check latest events
curl http://localhost:8000/api/layer2/live/latest
```

**Low scores?**
- Wait 10-15 seconds for correlation
- Check ML models in backend logs
- Run multiple samples for more detections

## 📝 Notes

- These are **simulations only** - no actual malware is executed
- Sysmon must be running to collect events
- Backend must be running before executing samples
- Safe to run multiple times
- Use for testing and demonstration only

## 🎯 Next Steps

1. Double-click `RUN_ALL_MALWARE.bat` to run all samples
2. Open dashboard at http://localhost:3000
3. Review Layer 2 alerts and scores
4. Check correlation in Layer 3
5. Verify response recommendations in Layer 4
