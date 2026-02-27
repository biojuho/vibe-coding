import webbrowser
import os
import platform
import subprocess

def open_website(url):
    """
    Opens a website in the default browser.
    """
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        webbrowser.open(url)
        return True, f"Opened {url}"
    except Exception as e:
        return False, f"Failed to open website: {e}"

def launch_app(app_name):
    """
    Launches a common application.
    """
    # Common app paths or commands for Windows
    apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "cmd": "cmd.exe",
        "explorer": "explorer.exe",
        "paint": "mspaint.exe"
    }
    
    import shutil
    
    # Check OS
    if platform.system() != "Windows":
        return False, f"App launching is currently only supported on Windows (Current: {platform.system()})"
    
    app_key = app_name.lower().replace(" ", "")
    
    # Check for mapped apps
    for key, command in apps.items():
        if key in app_key:
            # Verify executable exists in PATH
            if not shutil.which(command):
                return False, f"Executable '{command}' not found in system PATH."
                
            try:
                subprocess.Popen(command)
                return True, f"Launched {key}"
            except Exception as e:
                return False, f"Failed to launch {app_name}: {e}"
                
    return False, f"Application '{app_name}' not found in supported list."

if __name__ == "__main__":
    # Test
    # open_website("google.com")
    # launch_app("calculator")
    pass
