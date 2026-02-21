import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from backend.app.main import app

def test_import():
    assert app is not None
    print("Backend app imported successfully")

if __name__ == "__main__":
    test_import()
