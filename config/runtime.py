# Process-wide runtime state, set once by runner.py at startup.
# Read it as runtime.DEBUG (not `from config.runtime import DEBUG`) so the value set at startup is seen.
DEBUG = False
