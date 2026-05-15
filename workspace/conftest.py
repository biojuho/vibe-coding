import os
import sys

# Add root execution/ for pytest runs launched with cwd=workspace/.
workspace_dir = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(workspace_dir, ".."))
execution_dir = os.path.join(root_dir, "execution")

if execution_dir not in sys.path:
    sys.path.insert(0, execution_dir)
