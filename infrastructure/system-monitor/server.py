import datetime
import platform

import psutil

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None


def _build_system_stats() -> dict:
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()

    vm = psutil.virtual_memory()
    memory = {
        "total_gb": round(vm.total / (1024**3), 2),
        "available_gb": round(vm.available / (1024**3), 2),
        "percent": vm.percent,
    }

    disk = psutil.disk_usage("/")
    disk_info = {
        "total_gb": round(disk.total / (1024**3), 2),
        "free_gb": round(disk.free / (1024**3), 2),
        "percent": disk.percent,
    }

    sys_info = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "timestamp": datetime.datetime.now().isoformat(),
    }

    return {
        "cpu": {"percent": cpu_percent, "cores": cpu_count},
        "memory": memory,
        "disk": disk_info,
        "os": sys_info,
    }


if FastMCP is not None:
    mcp = FastMCP("system-monitor")

    @mcp.tool()
    def get_system_stats() -> dict:
        """Returns current system statistics (CPU, Memory, Disk, Network)."""
        return _build_system_stats()
else:
    mcp = None

    def get_system_stats() -> dict:
        """Returns current system statistics when MCP is unavailable."""
        return _build_system_stats()


if __name__ == "__main__":
    if mcp is None:
        print("mcp package is not installed; printing one-shot stats.")
        print(get_system_stats())
    else:
        mcp.run()
