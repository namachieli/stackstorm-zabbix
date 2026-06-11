import sys
import os

# Add actions/ and tests/ to the path so imports resolve as they do in StackStorm
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'actions'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))
