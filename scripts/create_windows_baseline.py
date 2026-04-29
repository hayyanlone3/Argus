import os
import sys
import time
import pickle
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "backend"))

from river import anomaly
from backend.shared.logger import setup_logger
from backend.layers.layer2_scoring.runtime_engine import layer_c_features
from backend.layers.layer2_scoring.event_stream import TelemetryEvent

logger = setup_logger(__name__)

def create_windows_baseline(duration_minutes: int = 60):
    logger.info(f"Creating Windows baseline for {duration_minutes} minutes...")
    logger.info("Please perform normal Windows activities: browse, open apps, etc.")
    
    model = anomaly.HalfSpaceTrees(
        n_trees=25,
        height=15, 
        window_size=250,
        seed=42
    )
    
    normal_events = [
        # Normal process launches
        TelemetryEvent(
            event_id="baseline-1",
            ts=time.time(),
            source="sysmon",
            kind="PROCESS_CREATE",
            session_id="baseline",
            parent_process="C:\\Windows\\explorer.exe",
            child_process="C:\\Windows\\System32\\notepad.exe",
            child_cmd="notepad.exe",
            file_entropy=6.2 
        ),
        TelemetryEvent(
            event_id="baseline-2", 
            ts=time.time(),
            source="sysmon",
            kind="PROCESS_CREATE",
            session_id="baseline",
            parent_process="C:\\Windows\\explorer.exe",
            child_process="C:\\Program Files\\Google\\Chrome\\chrome.exe",
            child_cmd="chrome.exe",
            file_entropy=6.8
        ),
        # Normal file operations
        TelemetryEvent(
            event_id="baseline-3",
            ts=time.time(),
            source="sysmon", 
            kind="FILE_CREATE",
            session_id="baseline",
            child_process="C:\\Windows\\System32\\notepad.exe",
            target_path="C:\\Users\\user\\Documents\\document.txt",
            file_entropy=5.5
        ),
        # Normal registry operations
        TelemetryEvent(
            event_id="baseline-4",
            ts=time.time(),
            source="sysmon",
            kind="REG_SET", 
            session_id="baseline",
            child_process="C:\\Windows\\System32\\winlogon.exe",
            reg_target="HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer",
            file_entropy=None
        )
    ]
    
    logger.info("Training on normal Windows events...")
    events_processed = 0
    
    for iteration in range(100):
        for evt in normal_events:
            feats = layer_c_features(evt, a_score=0.1, b_score=0.1)
            

            model.learn_one(feats)
            events_processed += 1
            
            if events_processed % 50 == 0:
                logger.info(f"Processed {events_processed} baseline events...")
    
    # Test the baseline
    logger.info("Testing baseline with normal vs suspicious events...")
    
    # Normal event should have low anomaly score
    normal_feats = layer_c_features(normal_events[0], a_score=0.1, b_score=0.1)
    normal_score = model.score_one(normal_feats)
    
    # Suspicious event should have higher anomaly score
    suspicious_evt = TelemetryEvent(
        event_id="test-suspicious",
        ts=time.time(),
        source="sysmon",
        kind="PROCESS_CREATE", 
        session_id="test",
        parent_process="C:\\Windows\\explorer.exe",
        child_process="C:\\Windows\\System32\\cmd.exe",
        child_cmd="cmd.exe /c powershell -enc SGVsbG8gV29ybGQ=",  # Base64
        file_entropy=7.9  # High entropy
    )
    
    suspicious_feats = layer_c_features(suspicious_evt, a_score=0.85, b_score=0.7)
    suspicious_score = model.score_one(suspicious_feats)
    
    logger.info(f"Normal event anomaly score: {normal_score:.3f}")
    logger.info(f"Suspicious event anomaly score: {suspicious_score:.3f}")
    
    if suspicious_score > normal_score:
        logger.info("✅ Baseline working correctly - suspicious > normal")
    else:
        logger.warning("   Baseline may need more training data")
    
    # Save Windows-native model
    model_path = Path("backend/ml/models/river_windows_baseline.pkl")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    logger.info(f"✅ Windows baseline saved to {model_path}")
    logger.info(f"  Processed {events_processed} events")
    logger.info("  Update runtime_engine.py to use 'river_windows_baseline.pkl'")
    
    return model

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create Windows-native River baseline")
    parser.add_argument("--duration", type=int, default=60, 
                       help="Duration in minutes (default: 60)")
    args = parser.parse_args()
    
    create_windows_baseline(args.duration)