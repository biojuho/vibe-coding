import psutil
import platform
import datetime

def get_system_report():
    """
    Returns a formatted string summary of the current system status.
    """
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory
        vm = psutil.virtual_memory()
        mem_total = round(vm.total / (1024**3), 2)
        mem_avail = round(vm.available / (1024**3), 2)
        mem_percent = vm.percent
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_total = round(disk.total / (1024**3), 2)
        disk_free = round(disk.free / (1024**3), 2)
        disk_percent = disk.percent
        
        # OS
        os_info = f"{platform.system()} {platform.release()}"
        
        report = f"""
[System Status Report]
- OS: {os_info}
- CPU Usage: {cpu_percent}% ({cpu_count} Cores)
- Memory: {mem_percent}% used ({mem_avail}GB available / {mem_total}GB total)
- Disk: {disk_percent}% used ({disk_free}GB free / {disk_total}GB total)
        """.strip()
        
        return report
    except Exception as e:
        return f"Failed to retrieve system status: {e}"

if __name__ == "__main__":
    print(get_system_report())
