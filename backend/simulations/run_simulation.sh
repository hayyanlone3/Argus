#!/bin/bash
# Aggressive Malware Simulation Launcher for Linux/Mac
# Usage: bash run_simulation.sh

echo ""
echo "================================================================================"
echo "ARGUS MALWARE SIMULATION LAUNCHER"
echo "================================================================================"
echo ""
echo "This will simulate aggressive malware behavior."
echo "Make sure the ARGUS backend is running on http://localhost:8000"
echo ""
echo "Checking prerequisites..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python $python_version found"

# Check if backend is running
echo "Checking if backend is running..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠ WARNING: Backend does not appear to be running"
    echo "Please start the backend first:"
    echo "  cd backend"
    echo "  python main.py"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to cancel..."
fi

echo ""
echo "Starting malware simulation..."
echo ""

# Run the simulation
cd "$(dirname "$0")/.."
python3 -m simulations.aggressive_malware

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Simulation failed"
    exit 1
fi

echo ""
echo "================================================================================"
echo "SIMULATION COMPLETE"
echo "================================================================================"
echo ""
echo "Check the dashboard at http://localhost:3000 for detections"
echo ""
