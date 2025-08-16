#!/usr/bin/env python3
"""
Script untuk mendeteksi spesifikasi perangkat
Menampilkan informasi CPU, GPU, RAM, Storage, dan sistem lainnya
"""

import platform
import psutil
import socket
import uuid
import subprocess
import sys
import os
from datetime import datetime

def install_required_packages():
    """Install package yang diperlukan jika belum ada"""
    required_packages = ['psutil', 'GPUtil', 'py-cpuinfo']
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_').replace('GPUtil', 'GPUtil'))
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def get_size(bytes, suffix="B"):
    """Convert bytes ke format yang mudah dibaca"""
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_cpu_info():
    """Mendapatkan informasi CPU"""
    print("="*40, "CPU Info", "="*40)
    
    # Informasi dasar CPU
    print(f"Processor: {platform.processor()}")
    print(f"Architecture: {platform.machine()}")
    print(f"CPU Cores (Physical): {psutil.cpu_count(logical=False)}")
    print(f"CPU Cores (Logical): {psutil.cpu_count(logical=True)}")
    
    # Frekuensi CPU
    cpu_freq = psutil.cpu_freq()
    if cpu_freq:
        print(f"Max Frequency: {cpu_freq.max:.2f}Mhz")
        print(f"Min Frequency: {cpu_freq.min:.2f}Mhz")
        print(f"Current Frequency: {cpu_freq.current:.2f}Mhz")
    
    # CPU Usage per core
    print("CPU Usage Per Core:")
    for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
        print(f"  Core {i}: {percentage}%")
    print(f"Total CPU Usage: {psutil.cpu_percent()}%")
    
    # Informasi detail dengan py-cpuinfo (jika tersedia)
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        print(f"CPU Brand: {info.get('brand_raw', 'Unknown')}")
        print(f"CPU Family: {info.get('family', 'Unknown')}")
        print(f"CPU Model: {info.get('model', 'Unknown')}")
        print(f"CPU Vendor: {info.get('vendor_id_raw', 'Unknown')}")
    except ImportError:
        print("Untuk info CPU lebih detail, install: pip install py-cpuinfo")

def get_memory_info():
    """Mendapatkan informasi Memory/RAM"""
    print("="*40, "Memory Info", "="*40)
    
    # RAM information
    svmem = psutil.virtual_memory()
    print(f"Total RAM: {get_size(svmem.total)}")
    print(f"Available RAM: {get_size(svmem.available)}")
    print(f"Used RAM: {get_size(svmem.used)}")
    print(f"RAM Usage: {svmem.percent}%")
    
    # Swap memory
    swap = psutil.swap_memory()
    print(f"Total Swap: {get_size(swap.total)}")
    print(f"Used Swap: {get_size(swap.used)}")
    print(f"Free Swap: {get_size(swap.free)}")
    print(f"Swap Usage: {swap.percent}%")

def get_disk_info():
    """Mendapatkan informasi Storage/Disk"""
    print("="*40, "Storage Info", "="*40)
    
    print("Partitions and Usage:")
    partitions = psutil.disk_partitions()
    for partition in partitions:
        print(f"  Device: {partition.device}")
        print(f"  Mountpoint: {partition.mountpoint}")
        print(f"  File system: {partition.fstype}")
        
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            print(f"  Total Size: {get_size(partition_usage.total)}")
            print(f"  Used: {get_size(partition_usage.used)}")
            print(f"  Free: {get_size(partition_usage.free)}")
            print(f"  Usage: {(partition_usage.used/partition_usage.total)*100:.1f}%")
        except PermissionError:
            print("  Permission denied")
        print()

def get_gpu_info():
    """Mendapatkan informasi GPU"""
    print("="*40, "GPU Info", "="*40)
    
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            for i, gpu in enumerate(gpus):
                print(f"GPU {i}:")
                print(f"  Name: {gpu.name}")
                print(f"  Total Memory: {gpu.memoryTotal}MB")
                print(f"  Used Memory: {gpu.memoryUsed}MB")
                print(f"  Free Memory: {gpu.memoryFree}MB")
                print(f"  GPU Load: {gpu.load*100:.1f}%")
                print(f"  Temperature: {gpu.temperature}°C")
                print()
        else:
            print("No GPU detected or GPU information not available")
    except ImportError:
        print("Untuk info GPU, install: pip install GPUtil")
    except Exception as e:
        print(f"Error getting GPU info: {e}")
    
    # Alternatif untuk Windows - menggunakan wmic
    if platform.system() == "Windows":
        try:
            print("Additional GPU Info (Windows):")
            result = subprocess.run(
                ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip():
                        print(f"  Graphics Card: {line.strip()}")
        except Exception:
            pass

def get_network_info():
    """Mendapatkan informasi Network"""
    print("="*40, "Network Info", "="*40)
    
    # Hostname dan IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Hostname: {hostname}")
    print(f"Local IP: {local_ip}")
    
    # Network interfaces
    print("Network Interfaces:")
    if_addrs = psutil.net_if_addrs()
    for interface_name, interface_addresses in if_addrs.items():
        print(f"  Interface: {interface_name}")
        for address in interface_addresses:
            if str(address.family) == 'AddressFamily.AF_INET':
                print(f"    IP Address: {address.address}")
                print(f"    Netmask: {address.netmask}")
                print(f"    Broadcast IP: {address.broadcast}")
        print()

def get_system_info():
    """Mendapatkan informasi sistem"""
    print("="*40, "System Info", "="*40)
    
    # Basic system info
    uname = platform.uname()
    print(f"System: {uname.system}")
    print(f"Node Name: {uname.node}")
    print(f"Release: {uname.release}")
    print(f"Version: {uname.version}")
    print(f"Machine: {uname.machine}")
    print(f"Processor: {uname.processor}")
    
    # Boot time
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    print(f"Boot Time: {bt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # MAC Address
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
                   for ele in range(0,8*6,8)][::-1])
    print(f"MAC Address: {mac}")

def get_battery_info():
    """Mendapatkan informasi baterai (jika ada)"""
    print("="*40, "Battery Info", "="*40)
    
    try:
        battery = psutil.sensors_battery()
        if battery:
            print(f"Battery Percentage: {battery.percent}%")
            print(f"Power Plugged: {'Yes' if battery.power_plugged else 'No'}")
            if not battery.power_plugged:
                time_left = battery.secsleft
                if time_left != psutil.POWER_TIME_UNLIMITED:
                    hours = time_left // 3600
                    minutes = (time_left % 3600) // 60
                    print(f"Battery Time Left: {hours}h {minutes}m")
        else:
            print("No battery detected (Desktop PC)")
    except Exception as e:
        print(f"Battery info not available: {e}")

def get_sensors_info():
    """Mendapatkan informasi sensor (temperature, fan, dll)"""
    print("="*40, "Sensors Info", "="*40)
    
    # Temperature sensors
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            print("Temperature Sensors:")
            for name, entries in temps.items():
                print(f"  {name}:")
                for entry in entries:
                    print(f"    {entry.label or 'N/A'}: {entry.current}°C")
        else:
            print("No temperature sensors detected")
    except Exception:
        print("Temperature sensors not available on this platform")
    
    # Fan sensors
    try:
        fans = psutil.sensors_fans()
        if fans:
            print("Fan Sensors:")
            for name, entries in fans.items():
                print(f"  {name}:")
                for entry in entries:
                    print(f"    {entry.label or 'N/A'}: {entry.current} RPM")
        else:
            print("No fan sensors detected")
    except Exception:
        print("Fan sensors not available on this platform")

def main():
    """Fungsi utama"""
    print("🔍 DEVICE SPECIFICATION DETECTOR 🔍")
    print("="*80)
    print(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Install package yang diperlukan
    try:
        install_required_packages()
    except Exception as e:
        print(f"Warning: Could not install some packages: {e}")
        print("Some features may not work properly.")
    
    print()
    
    # Panggil semua fungsi info
    try:
        get_system_info()
        print()
        get_cpu_info()
        print()
        get_memory_info()
        print()
        get_disk_info()
        print()
        get_gpu_info()
        print()
        get_network_info()
        print()
        get_battery_info()
        print()
        get_sensors_info()
        print()
    except KeyboardInterrupt:
        print("\nScan cancelled by user")
    except Exception as e:
        print(f"Error during scan: {e}")
    
    print("="*80)
    print("✅ Device specification scan completed!")
    print("="*80)

if __name__ == "__main__":
    main()