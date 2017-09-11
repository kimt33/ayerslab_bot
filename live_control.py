import os
import subprocess

while True:
    try:
        path = os.path.dirname(os.path.realpath(__file__))
        subprocess.call("python3 " + os.path.join(path, "live.py"), shell=True)
    except Exception:
        continue
