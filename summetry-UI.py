# Streamlit Entrypoint Redirect File
# Resolves the path to backend/summetry-UI.py for Streamlit Cloud deployment compatibility

import os
import sys

# Add backend directory to path so imports work correctly
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)

# Execute the main streamlit script from backend
with open(os.path.join(backend_dir, "summetry-UI.py"), "r", encoding="utf-8") as f:
    code = compile(f.read(), "summetry-UI.py", "exec")
    exec(code, globals())
