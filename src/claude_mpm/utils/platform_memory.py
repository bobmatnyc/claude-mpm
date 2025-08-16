"""Platform-specific memory monitoring utilities.

This module provides fallback methods for monitoring process memory
when psutil is not available, using platform-specific approaches.

Design Principles:
- Graceful degradation when psutil is unavailable
- Platform-specific optimizations
- Consistent interface across platforms
- Error handling and logging
"""

import os
import platform
import subprocess
import re
import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryInfo:
    """Container for memory information."""
    
    def __init__(self, rss: int, vms: int, percent: float = 0.0):
        """Initialize memory info.
        
        Args:
            rss: Resident Set Size in bytes
            vms: Virtual Memory Size in bytes  
            percent: Memory usage as percentage of total
        """
        self.rss = rss
        self.vms = vms
        self.percent = percent
    
    @property
    def rss_mb(self) -> float:
        """Get RSS in megabytes."""
        return self.rss / (1024 * 1024)
    
    @property
    def vms_mb(self) -> float:
        """Get VMS in megabytes."""
        return self.vms / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'rss_bytes': self.rss,
            'vms_bytes': self.vms,
            'rss_mb': self.rss_mb,
            'vms_mb': self.vms_mb,
            'percent': self.percent
        }


def get_memory_info_psutil(pid: int) -> Optional[MemoryInfo]:
    """Get memory info using psutil (preferred method).
    
    Args:
        pid: Process ID to monitor
        
    Returns:
        MemoryInfo object or None if psutil not available or process not found
    """
    try:
        import psutil
        process = psutil.Process(pid)
        mem_info = process.memory_info()
        mem_percent = process.memory_percent()
        return MemoryInfo(
            rss=mem_info.rss,
            vms=mem_info.vms,
            percent=mem_percent
        )
    except ImportError:
        logger.debug("psutil not available")
        return None
    except psutil.NoSuchProcess:
        logger.warning(f"Process {pid} not found")
        return None
    except Exception as e:
        logger.error(f"Error getting memory info with psutil: {e}")
        return None


def get_memory_info_macos(pid: int) -> Optional[MemoryInfo]:
    """Get memory info on macOS using ps command.
    
    Args:
        pid: Process ID to monitor
        
    Returns:
        MemoryInfo object or None if unable to get info
    """
    try:
        # Use ps to get memory info
        # RSS is in KB, VSZ is in KB
        result = subprocess.run(
            ['ps', '-o', 'rss=,vsz=', '-p', str(pid)],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            logger.debug(f"ps command failed for pid {pid}")
            return None
        
        output = result.stdout.strip()
        if not output:
            logger.debug(f"No output from ps for pid {pid}")
            return None
        
        parts = output.split()
        if len(parts) >= 2:
            rss_kb = int(parts[0])
            vsz_kb = int(parts[1])
            
            # Convert KB to bytes
            rss_bytes = rss_kb * 1024
            vms_bytes = vsz_kb * 1024
            
            # Try to get total memory for percentage
            percent = 0.0
            try:
                total_result = subprocess.run(
                    ['sysctl', '-n', 'hw.memsize'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if total_result.returncode == 0:
                    total_bytes = int(total_result.stdout.strip())
                    percent = (rss_bytes / total_bytes) * 100
            except Exception:
                pass
            
            return MemoryInfo(rss=rss_bytes, vms=vms_bytes, percent=percent)
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout getting memory info for pid {pid}")
    except ValueError as e:
        logger.error(f"Error parsing ps output: {e}")
    except Exception as e:
        logger.error(f"Error getting macOS memory info: {e}")
    
    return None


def get_memory_info_linux(pid: int) -> Optional[MemoryInfo]:
    """Get memory info on Linux using /proc filesystem.
    
    Args:
        pid: Process ID to monitor
        
    Returns:
        MemoryInfo object or None if unable to get info
    """
    try:
        status_path = Path(f'/proc/{pid}/status')
        if not status_path.exists():
            logger.debug(f"Process {pid} not found in /proc")
            return None
        
        rss_bytes = 0
        vms_bytes = 0
        
        with open(status_path, 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    # VmRSS is in KB
                    rss_kb = int(line.split()[1])
                    rss_bytes = rss_kb * 1024
                elif line.startswith('VmSize:'):
                    # VmSize is in KB
                    vms_kb = int(line.split()[1])
                    vms_bytes = vms_kb * 1024
        
        if rss_bytes == 0 and vms_bytes == 0:
            logger.debug(f"No memory info found for pid {pid}")
            return None
        
        # Try to get total memory for percentage
        percent = 0.0
        try:
            meminfo_path = Path('/proc/meminfo')
            if meminfo_path.exists():
                with open(meminfo_path, 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal:'):
                            total_kb = int(line.split()[1])
                            total_bytes = total_kb * 1024
                            percent = (rss_bytes / total_bytes) * 100
                            break
        except Exception:
            pass
        
        return MemoryInfo(rss=rss_bytes, vms=vms_bytes, percent=percent)
        
    except ValueError as e:
        logger.error(f"Error parsing /proc data: {e}")
    except Exception as e:
        logger.error(f"Error getting Linux memory info: {e}")
    
    return None


def get_memory_info_windows(pid: int) -> Optional[MemoryInfo]:
    """Get memory info on Windows using wmic or tasklist.
    
    Args:
        pid: Process ID to monitor
        
    Returns:
        MemoryInfo object or None if unable to get info
    """
    try:
        # Try wmic first (more detailed)
        result = subprocess.run(
            ['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 
             'WorkingSetSize,VirtualSize', '/format:list'],
            capture_output=True,
            text=True,
            timeout=5,
            shell=True
        )
        
        if result.returncode == 0:
            output = result.stdout
            rss_bytes = 0
            vms_bytes = 0
            
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('WorkingSetSize='):
                    try:
                        rss_bytes = int(line.split('=')[1])
                    except (IndexError, ValueError):
                        pass
                elif line.startswith('VirtualSize='):
                    try:
                        vms_bytes = int(line.split('=')[1])
                    except (IndexError, ValueError):
                        pass
            
            if rss_bytes > 0 or vms_bytes > 0:
                return MemoryInfo(rss=rss_bytes, vms=vms_bytes)
        
        # Fallback to tasklist
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
            capture_output=True,
            text=True,
            timeout=5,
            shell=True
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                # Parse CSV output
                # Format: "Image Name","PID","Session Name","Session#","Mem Usage"
                data = lines[1].split('","')
                if len(data) >= 5:
                    mem_usage = data[4].rstrip('"')
                    # Remove 'K' suffix and convert to bytes
                    mem_usage = mem_usage.replace(',', '').replace('K', '').strip()
                    if mem_usage.isdigit():
                        rss_bytes = int(mem_usage) * 1024
                        return MemoryInfo(rss=rss_bytes, vms=rss_bytes)  # tasklist only gives working set
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout getting memory info for pid {pid}")
    except Exception as e:
        logger.error(f"Error getting Windows memory info: {e}")
    
    return None


def get_memory_info_resource(pid: int) -> Optional[MemoryInfo]:
    """Get memory info using resource module (very limited).
    
    This only works for the current process and its children,
    not for arbitrary PIDs.
    
    Args:
        pid: Process ID to monitor (must be current process or child)
        
    Returns:
        MemoryInfo object or None if unable to get info
    """
    try:
        import resource
        
        # This only works if pid is the current process
        if pid != os.getpid():
            logger.debug("resource module only works for current process")
            return None
        
        usage = resource.getrusage(resource.RUSAGE_SELF)
        
        # Convert to bytes (ru_maxrss is in KB on Linux, bytes on macOS)
        if platform.system() == 'Darwin':
            rss_bytes = usage.ru_maxrss
        else:
            rss_bytes = usage.ru_maxrss * 1024
        
        # resource module doesn't provide VMS
        return MemoryInfo(rss=rss_bytes, vms=rss_bytes)
        
    except Exception as e:
        logger.error(f"Error getting memory info with resource module: {e}")
    
    return None


def get_process_memory(pid: int, method: Optional[str] = None) -> Optional[MemoryInfo]:
    """Get memory information for a process using the best available method.
    
    Args:
        pid: Process ID to monitor
        method: Specific method to use, or None for auto-detection
        
    Returns:
        MemoryInfo object or None if unable to get info
    """
    # If specific method requested, try it
    if method:
        if method == 'psutil':
            return get_memory_info_psutil(pid)
        elif method == 'macos':
            return get_memory_info_macos(pid)
        elif method == 'linux':
            return get_memory_info_linux(pid)
        elif method == 'windows':
            return get_memory_info_windows(pid)
        elif method == 'resource':
            return get_memory_info_resource(pid)
    
    # Auto-detect best method
    # Try psutil first (most reliable and cross-platform)
    info = get_memory_info_psutil(pid)
    if info:
        return info
    
    # Fall back to platform-specific methods
    system = platform.system()
    if system == 'Darwin':
        info = get_memory_info_macos(pid)
    elif system == 'Linux':
        info = get_memory_info_linux(pid)
    elif system == 'Windows':
        info = get_memory_info_windows(pid)
    
    # Last resort: resource module (only for current process)
    if not info and pid == os.getpid():
        info = get_memory_info_resource(pid)
    
    if not info:
        logger.warning(f"Unable to get memory info for pid {pid} on {system}")
    
    return info


def get_system_memory() -> Tuple[int, int]:
    """Get total and available system memory in bytes.
    
    Returns:
        Tuple of (total_bytes, available_bytes)
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        return mem.total, mem.available
    except ImportError:
        pass
    
    # Fallback methods
    system = platform.system()
    
    if system == 'Darwin':
        try:
            # Get total memory
            result = subprocess.run(
                ['sysctl', '-n', 'hw.memsize'],
                capture_output=True,
                text=True,
                timeout=5
            )
            total = int(result.stdout.strip()) if result.returncode == 0 else 0
            
            # Get free pages and page size for available memory
            vm_stat = subprocess.run(
                ['vm_stat'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if vm_stat.returncode == 0:
                free_pages = 0
                for line in vm_stat.stdout.split('\n'):
                    if 'Pages free:' in line:
                        free_pages = int(line.split(':')[1].strip().rstrip('.'))
                        break
                # Page size is typically 4096 bytes on macOS
                available = free_pages * 4096
            else:
                available = 0
            
            return total, available
        except Exception as e:
            logger.error(f"Error getting macOS system memory: {e}")
    
    elif system == 'Linux':
        try:
            total = 0
            available = 0
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        total = int(line.split()[1]) * 1024  # Convert KB to bytes
                    elif line.startswith('MemAvailable:'):
                        available = int(line.split()[1]) * 1024
            return total, available
        except Exception as e:
            logger.error(f"Error getting Linux system memory: {e}")
    
    elif system == 'Windows':
        try:
            result = subprocess.run(
                ['wmic', 'OS', 'get', 'TotalVisibleMemorySize,FreePhysicalMemory', '/format:list'],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True
            )
            if result.returncode == 0:
                total = 0
                free = 0
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('TotalVisibleMemorySize='):
                        total = int(line.split('=')[1]) * 1024  # Convert KB to bytes
                    elif line.startswith('FreePhysicalMemory='):
                        free = int(line.split('=')[1]) * 1024
                return total, free
        except Exception as e:
            logger.error(f"Error getting Windows system memory: {e}")
    
    # Unable to determine
    return 0, 0


def check_memory_pressure() -> str:
    """Check system memory pressure status.
    
    Returns:
        One of: 'normal', 'warning', 'critical', 'unknown'
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        percent_used = mem.percent
        
        if percent_used > 90:
            return 'critical'
        elif percent_used > 75:
            return 'warning'
        else:
            return 'normal'
    except ImportError:
        pass
    
    # Platform-specific checks
    system = platform.system()
    
    if system == 'Darwin':
        try:
            # Check macOS memory pressure
            result = subprocess.run(
                ['memory_pressure'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                output = result.stdout.lower()
                if 'critical' in output:
                    return 'critical'
                elif 'warning' in output:
                    return 'warning'
                else:
                    return 'normal'
        except Exception:
            pass
    
    elif system == 'Linux':
        try:
            # Check if we're close to OOM
            with open('/proc/meminfo', 'r') as f:
                total = 0
                available = 0
                for line in f:
                    if line.startswith('MemTotal:'):
                        total = int(line.split()[1])
                    elif line.startswith('MemAvailable:'):
                        available = int(line.split()[1])
                
                if total > 0:
                    percent_used = ((total - available) / total) * 100
                    if percent_used > 90:
                        return 'critical'
                    elif percent_used > 75:
                        return 'warning'
                    else:
                        return 'normal'
        except Exception:
            pass
    
    return 'unknown'