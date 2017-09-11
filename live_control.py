import os
import subprocess

while True:
    try:
        path = os.path.dirname(os.path.realpath(__file__))
        subprocess.call(["python", os.path.join(path, "live.py")], shell=True)
    except Exception:
        continue
