# tools/os_tools.py
import subprocess
import os
from datetime import datetime

def get_current_time():
    return f"Son las {datetime.now().strftime('%H:%M')} del {datetime.now().strftime('%d/%m')}"

def open_application(app_name):
    try:
        if "chrome" in app_name.lower(): subprocess.Popen(["google-chrome"])
        elif "notas" in app_name.lower(): subprocess.Popen(["notepad.exe"] if os.name == 'nt' else ["gedit"])
        return f"Abriendo {app_name}"
    except Exception as e:
        return f"No pude abrir la aplicación: {e}"
