"""
Standalone entry point that *always* launches a native window.
Run via:  python run_launcher_desktop.py
"""

from app.main import run_desktop

# Port 5050 damit es nicht mit anderen Services kollidiert
run_desktop(host="127.0.0.1", port=5050)
