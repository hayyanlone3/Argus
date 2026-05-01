# 🦠 ARGUS Malware Simulations

## One-Click Malware Tests

All malware can be run by **double-clicking** the `.bat` files!

---

## 🎮 Interactive Menu (Recommended)

**Double-click: `RUN_ALL_MALWARE.bat`**

Choose from a menu:
```
1. SIMPLE MALWARE       - Single cmd.exe (easiest test)
2. TEST DETECTION       - 5 cmd.exe spawns
3. VERBOSE MALWARE      - Step-by-step with output

4. AGGRESSIVE 1         - 10 cmd.exe spawns
5. AGGRESSIVE 2         - PowerShell attacks
6. AGGRESSIVE 3         - File drops + cmd spawns
7. AGGRESSIVE 4         - LOLBin abuse
8. AGGRESSIVE 5         - ULTIMATE ATTACK (everything)
```

---

## 📋 Individual Tests

### ⭐ Beginner Tests (Start Here)

| File | What It Does | Difficulty |
|------|--------------|------------|
| **`RUN_SIMPLE_MALWARE.bat`** | Spawns 1 cmd.exe | ⭐ Easiest |
| **`RUN_TEST_DETECTION.bat`** | Spawns 5 cmd.exe rapidly | ⭐⭐ Easy |
| **`RUN_VERBOSE_MALWARE.bat`** | 3 cmd.exe with step-by-step output | ⭐⭐ Easy |

### 🔥 Advanced Tests

| File | What It Does | Difficulty |
|------|--------------|------------|
| **`RUN_AGGRESSIVE_1.bat`** | 10 cmd.exe in 2 seconds | ⭐⭐⭐ Medium |
| **`RUN_AGGRESSIVE_2.bat`** | 5 PowerShell with suspicious flags | ⭐⭐⭐ Medium |
| **`RUN_AGGRESSIVE_3.bat`** | 5 .exe drops + 7 cmd.exe | ⭐⭐⭐⭐ Hard |
| **`RUN_AGGRESSIVE_4.bat`** | wscript, cscript, rundll32 | ⭐⭐⭐⭐ Hard |
| **`RUN_AGGRESSIVE_5.bat`** | ULTIMATE: 29 malicious actions | ⭐⭐⭐⭐⭐ Extreme |

---

## 🚀 How to Use

### Step 1: Start Backend
From root directory, run:
```
START_BACKEND_SAFE.bat
```

Wait for:
```
🎯 READY - Waiting for new malware activity...
```

### Step 2: Run Malware
Go to `backend/simulations/` folder and **double-click** any `.bat` file!

### Step 3: Check Detection
Look at backend console for:
```
[SYSMON] ⚠️  SUSPICIOUS PROCESS: cmd.exe
[AUTO-SCORE] 🚨 CRITICAL DETECTED!
[CORRELATOR] 🚨 CRITICAL INCIDENT CREATED!
```

---

## 📊 Test Details

### SIMPLE_MALWARE
- **Actions**: 1 cmd.exe spawn
- **Expected Score**: 0.50 (CRITICAL)
- **Detection Time**: < 1 second
- **Use Case**: Verify basic detection works

### TEST_DETECTION
- **Actions**: 5 cmd.exe spawns (0.2s apart)
- **Expected Score**: 0.50 each (CRITICAL)
- **Detection Time**: < 2 seconds
- **Use Case**: Test rapid process spawning

### VERBOSE_MALWARE
- **Actions**: 3 cmd.exe spawns (1s apart)
- **Expected Score**: 0.50 each (CRITICAL)
- **Detection Time**: < 3 seconds
- **Use Case**: See step-by-step what's happening

### AGGRESSIVE_MALWARE_1
- **Actions**: 10 cmd.exe spawns in 2 seconds
- **Expected Score**: 0.50 each (CRITICAL)
- **Detection Time**: < 3 seconds
- **Use Case**: Stress test rapid spawning

### AGGRESSIVE_MALWARE_2
- **Actions**: 5 PowerShell commands with:
  - `-NoProfile`
  - `-EncodedCommand`
  - `-WindowStyle Hidden`
  - `-ExecutionPolicy Bypass`
- **Expected Score**: 0.60-0.80 (CRITICAL)
- **Detection Time**: < 3 seconds
- **Use Case**: Test PowerShell detection

### AGGRESSIVE_MALWARE_3
- **Actions**: 
  - 5 .exe files dropped in temp
  - 7 cmd.exe spawns
- **Expected Score**: 0.40-0.75 (CRITICAL)
- **Detection Time**: < 4 seconds
- **Use Case**: Test file creation + process spawning

### AGGRESSIVE_MALWARE_4
- **Actions**: LOLBin abuse:
  - wscript.exe
  - cscript.exe
  - rundll32.exe
- **Expected Score**: 0.55+ (CRITICAL)
- **Detection Time**: < 2 seconds
- **Use Case**: Test Living-off-the-Land binaries

### AGGRESSIVE_MALWARE_5 (ULTIMATE)
- **Actions**: Everything at once:
  - 15 cmd.exe spawns
  - 3 PowerShell attacks
  - 8 .exe file drops
  - 3 LOLBin attacks
- **Total**: 29 malicious actions
- **Expected Score**: 0.40-0.80 (CRITICAL)
- **Detection Time**: < 6 seconds
- **Use Case**: Ultimate stress test

---

## ✅ Expected Results

For **all tests**, you should see in backend console:

```
[SYSMON] ⚠️  SUSPICIOUS PROCESS: cmd.exe (PID: 1234)
[SYSMON]   Parent: python.exe
[SYSMON]   Command: cmd.exe /c echo ...
[COLLECTOR] ✅ Suspicious event published

[INGESTION] ✅ Batch processed: X suspicious events
[INGESTION]   - cmd.exe (PID: 1234)
[INGESTION]   - cmd.exe (PID: 5678)

[AUTO-SCORE] 🚨 CRITICAL DETECTED!
[AUTO-SCORE]   Edge ID: 42
[AUTO-SCORE]   Type: SPAWNED
[AUTO-SCORE]   Score: 0.50
[AUTO-SCORE]   Target: cmd.exe

[CORRELATOR] 🚨 CRITICAL INCIDENT CREATED!
[CORRELATOR]   ID: 1
[CORRELATOR]   Session: {guid}
[CORRELATOR]   Edges: 5
[CORRELATOR]   MITRE: Execution
```

---

## 🔧 Troubleshooting

### No Detection?
1. Check Sysmon is running: `CHECK_SYSMON.bat` (in root)
2. Check backend logs for errors
3. Verify backend shows "READY - Waiting for new malware activity..."

### Slow Detection?
1. Edit `backend/.env`: Set `ARGUS_SYSMON_POLL_SEC=0.05`
2. Restart backend

### False Negatives?
1. Lower thresholds in `backend/layers/layer2_scoring/auto_scoring.py`
2. Change `if score >= 0.35:` to `if score >= 0.25:`

---

## 🎯 Recommended Testing Order

1. **`RUN_SIMPLE_MALWARE.bat`** - Verify basic detection
2. **`RUN_VERBOSE_MALWARE.bat`** - Understand the flow
3. **`RUN_TEST_DETECTION.bat`** - Test rapid detection
4. **`RUN_AGGRESSIVE_5.bat`** - Ultimate stress test

---

## 💡 Tips

- Always start backend before running malware
- Watch backend console in real-time
- Use VERBOSE_MALWARE to see step-by-step execution
- Start with SIMPLE_MALWARE for first test
- Use AGGRESSIVE_5 to verify system handles complex attacks

---

## ⚠️ Safety Note

These are **simulated malware** for testing purposes only. They:
- Spawn legitimate Windows processes (cmd.exe, powershell.exe)
- Create temporary files that are immediately deleted
- Do NOT contain actual malicious code
- Are safe to run on your system

However, they **will trigger** antivirus software and ARGUS detection!

---

**Happy Testing! 🎯**
