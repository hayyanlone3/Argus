# ARGUS Malware Simulation - Complete Usage Guide

## Overview

The aggressive malware simulation generates realistic attack patterns that trigger Layer 2 detection in ARGUS. This guide walks you through setup, execution, and troubleshooting.

## Quick Start (30 seconds)

```bash
# Terminal 1: Start ARGUS backend
cd backend
python main.py

# Terminal 2: Run malware simulation
cd backend
python -m simulations.aggressive_malware

# Terminal 3: Monitor dashboard
# Open http://localhost:3000 in your browser
```

## Detailed Setup

### Step 1: Verify Prerequisites

```bash
# Check Python version (3.8+)
python --version

# Check backend is running
curl http://localhost:8000/health

# Check Layer 2 is operational
curl http://localhost:8000/api/layer2/health
```

### Step 2: Start ARGUS Backend

```bash
cd backend
python main.py
```

Expected output:
```
[INFO] ARGUS Backend Initializing...
[INFO] Database initialized successfully
[INFO] API running on 0.0.0.0:8000
```

### Step 3: Run Malware Simulation

```bash
cd backend
python -m simulations.aggressive_malware
```

Expected output:
```
[MALWARE SIM] 🔴 SIMULATING PROCESS INJECTION ATTACK
[MALWARE SIM]   → Injected into explorer.exe
[MALWARE SIM]   → Injected into svchost.exe
...
[MALWARE SIM] ✅ MALWARE SIMULATION COMPLETE
```

### Step 4: Monitor Dashboard

Open http://localhost:3000 in your browser and navigate to:
- **Layer 2 Dashboard**: Should show CRITICAL alerts
- **Live Events**: Real-time malware behavior detection
- **Severity Distribution**: High concentration of CRITICAL events

## What Gets Detected

The simulation triggers detection across all three Layer 2 channels:

### Channel 2A: Math Certainty
- **Spawn Rate Anomaly**: 15+ child processes spawned rapidly
- **Rename Burst**: Multiple file operations with temp extensions
- **Edge Burst**: >10 edges created per minute

### Channel 2B: Statistical Impossibility
- **High Entropy**: Encrypted/obfuscated file operations
- **Unusual Patterns**: Registry modifications to persistence locations
- **P-value Analysis**: Behaviors with p < 0.001

### Channel 2C: ML Graph Anomaly
- **Graph Topology**: Unusual branching factor (>3)
- **Node Relationships**: Suspicious process hierarchies
- **River Model**: Anomaly score from trained model

## Expected Results

### Immediate (0-5 seconds)
- Events appear in `/api/layer2/live/latest`
- Fusion scores: 0.8-1.0
- Severity: CRITICAL

### Short-term (5-30 seconds)
- Dashboard updates with alerts
- Correlation engine links related events
- Response layer generates recommendations

### Verification Endpoints

```bash
# Get latest detections
curl http://localhost:8000/api/layer2/live/latest?limit=50

# Get specific event
curl http://localhost:8000/api/layer2/live/{event_id}

# Get scoring statistics
curl http://localhost:8000/api/layer2/stats

# Get Layer 1 graph
curl http://localhost:8000/api/layer1/graph/stats
```

## Customization

### Adjust Event Rate

```python
# Slower (more time for processing)
simulator = MalwareSimulator(delay_ms=200)

# Faster (stress test)
simulator = MalwareSimulator(delay_ms=10)
```

### Add Custom Attack

Edit `aggressive_malware.py` and add a method:

```python
def simulate_custom_attack(self):
    """Your custom attack simulation"""
    self.log_event("🔴 SIMULATING CUSTOM ATTACK")
    
    self.publish(
        "PROCESS_CREATE",
        parent_process="malware.exe",
        child_process="custom.exe",
        child_cmd="custom.exe /attack",
        parent_pid=self.malware_pid,
        child_pid="9999"
    )
```

Then call it in `run_full_simulation()`:

```python
self.simulate_custom_attack()
```

### Modify Attack Targets

Change process names, registry keys, or file paths:

```python
# In simulate_process_injection()
target_processes = [
    "explorer.exe",
    "svchost.exe",
    "YOUR_CUSTOM_PROCESS.exe",  # Add here
]
```

## Troubleshooting

### Problem: No events appearing in dashboard

**Solution 1: Verify backend is running**
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy", ...}
```

**Solution 2: Check event queues**
```bash
# Look for these log messages:
# [COLLECTOR] ✅ Processing X NEW events
# [LAYER2] Processing event...
```

**Solution 3: Verify Layer 2 is operational**
```bash
curl http://localhost:8000/api/layer2/health
# Should return: {"layer": 2, "status": "operational", ...}
```

### Problem: Low detection scores

**Cause**: Events may not be correlated yet

**Solution**: 
- Wait 10-15 seconds for correlation
- Check `/api/layer2/live/latest?min_final_score=0.5`
- Verify ML models are loaded in backend logs

### Problem: "Event queue full" errors

**Cause**: Backend can't process events fast enough

**Solution**:
- Increase `delay_ms` in simulator
- Reduce number of events in simulation
- Check backend CPU/memory usage

### Problem: Sysmon events not being collected

**Cause**: Sysmon not installed or not running

**Solution**:
```bash
# Check if Sysmon is running
Get-Service Sysmon

# If not installed, install it:
# Download from: https://docs.microsoft.com/en-us/sysinternals/downloads/sysmon
# Run: sysmon.exe -i -accepteula
```

## Advanced Usage

### Programmatic Integration

```python
from backend.simulations.aggressive_malware import MalwareSimulator

# Create simulator
sim = MalwareSimulator(delay_ms=100)

# Run specific attack
sim.simulate_process_injection()
sim.simulate_ransomware_encryption()

# Or run full simulation
sim.run_full_simulation()
```

### Batch Testing

```bash
# Run simulation 5 times
for i in {1..5}; do
    python -m simulations.aggressive_malware
    sleep 30
done
```

### Performance Testing

```python
import time
from backend.simulations.aggressive_malware import MalwareSimulator

start = time.time()
simulator = MalwareSimulator(delay_ms=10)  # Fast
simulator.run_full_simulation()
elapsed = time.time() - start

print(f"Simulation completed in {elapsed:.2f} seconds")
print(f"Events per second: {(60 / elapsed):.1f}")
```

## Performance Metrics

Typical performance on modern hardware:

| Metric | Value |
|--------|-------|
| Events Generated | ~60 |
| Execution Time | 3-5 seconds |
| Events/Second | 12-20 |
| Detection Latency | <1 second |
| Average Fusion Score | 0.85 |
| CRITICAL Alerts | 45-55 |

## FAQ

**Q: Will this harm my system?**
A: No. This is a simulation only - no actual malware is executed. Only telemetry events are published.

**Q: Can I run this on non-Windows systems?**
A: The simulation itself runs on any OS, but Sysmon collection only works on Windows. You can still test the scoring engine.

**Q: How often should I run this?**
A: Use for:
- Initial system validation
- After code changes to Layer 2
- Performance testing
- Demo/presentation purposes

**Q: Can I modify the simulation?**
A: Yes! Edit `aggressive_malware.py` to add custom attacks or modify existing ones.

**Q: What if I want to test with real malware?**
A: Use a sandboxed environment (VM, container) and let Sysmon collect real events naturally.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs: `backend/logs/`
3. Verify all prerequisites are installed
4. Check that ports 8000 (backend) and 3000 (frontend) are available

## Next Steps

After successful simulation:
1. Review detected alerts in dashboard
2. Check Layer 3 correlation results
3. Verify Layer 4 response recommendations
4. Analyze Layer 5 learning updates
