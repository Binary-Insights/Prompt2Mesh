import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from blender_mcp.server import main as server_main

def main():
    """Entry point for the blender-mcp package"""
    server_main()

if __name__ == "__main__":
    main()
