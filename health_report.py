#!/usr/bin/env python3
"""
Health Reporter - Collects system health information
"""

import os
import json
import psutil
import platform
import subprocess
import socket
from datetime import datetime

class HealthReporter:
    def __init__(self):
        self.os_name = platform.system()
        self.hostname = socket.gethostname()
        
    def generate_report(self):
        """Generate complete health report"""
        report = {
            "system": self.get_system_info(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "network": self.get_network_info(),
            "security": self.get_security_status(),
            "services": self.get_critical_services(),
            "health_score": 0,
            "alerts": []
        }
        
        # Calculate health score and generate alerts
        report["health_score"] = self.calculate_health_score(report)
        report["alerts"] = self.generate_alerts(report)
        
        return report
    
    def get_system_info(self):
        """Get basic system information"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            return {
                "hostname": self.hostname,
                "os": f"{platform.system()} {platform.release()}",
                "version": platform.version(),
                "architecture": platform.machine(),
                "boot_time": boot_time.isoformat(),
                "uptime_seconds": int(uptime.total_seconds()),
                "uptime_human": str(uptime).split('.')[0],
                "local_ip": self.get_local_ip(),
                "public_ip": self.get_public_ip()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_cpu_info(self):
        """Get CPU information and usage"""
        try:
            return {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "current_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                "max_frequency": psutil.cpu_freq().max if psutil.cpu_freq() else None,
                "usage_percent": psutil.cpu_percent(interval=1),
                "usage_per_core": psutil.cpu_percent(interval=1, percpu=True),
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
                "temperature": self.get_cpu_temperature()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_memory_info(self):
        """Get memory information"""
        try:
            virtual_mem = psutil.virtual_memory()
            swap_mem = psutil.swap_memory()
            
            return {
                "total_gb": round(virtual_mem.total / (1024**3), 2),
                "available_gb": round(virtual_mem.available / (1024**3), 2),
                "used_gb": round(virtual_mem.used / (1024**3), 2),
                "usage_percent": virtual_mem.percent,
                "swap_total_gb": round(swap_mem.total / (1024**3), 2),
                "swap_used_gb": round(swap_mem.used / (1024**3), 2),
                "swap_percent": swap_mem.percent
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_disk_info(self):
        """Get disk information"""
        try:
            disk_info = []
            
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "usage_percent": round((usage.used / usage.total) * 100, 2)
                    })
                except PermissionError:
                    continue
            
            return disk_info
        except Exception as e:
            return {"error": str(e)}
    
    def get_network_info(self):
        """Get network information"""
        try:
            network_stats = psutil.net_io_counters()
            connections = len(psutil.net_connections())
            
            return {
                "bytes_sent": network_stats.bytes_sent,
                "bytes_received": network_stats.bytes_recv,
                "packets_sent": network_stats.packets_sent,
                "packets_received": network_stats.packets_recv,
                "active_connections": connections,
                "network_interfaces": self.get_network_interfaces()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_network_interfaces(self):
        """Get network interface information"""
        try:
            interfaces = []
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        interfaces.append({
                            "interface": interface,
                            "ip": addr.address,
                            "netmask": addr.netmask
                        })
            return interfaces
        except:
            return []
    
    def get_security_status(self):
        """Get security and update status"""
        try:
            if self.os_name == "Linux":
                return self.get_linux_security_status()
            elif self.os_name == "Windows":
                return self.get_windows_security_status()
            elif self.os_name == "Darwin":  # macOS
                return self.get_macos_security_status()
            else:
                return {"status": "unknown", "details": "OS not supported"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_linux_security_status(self):
        """Get Linux security status"""
        try:
            status = {
                "updates_available": 0,
                "security_updates": 0,
                "last_update_check": None,
                "package_manager": "unknown"
            }
            
            # Check for apt (Debian/Ubuntu)
            if os.path.exists("/usr/bin/apt"):
                status["package_manager"] = "apt"
                try:
                    # Update package list
                    subprocess.run(["sudo", "apt", "update"], capture_output=True, check=True)
                    
                    # Check for upgradable packages
                    result = subprocess.run(["apt", "list", "--upgradable"], 
                                          capture_output=True, text=True)
                    if result.stdout:
                        lines = result.stdout.strip().split('\n')[1:]  # Skip header
                        status["updates_available"] = len(lines)
                    
                    # Check for security updates
                    result = subprocess.run(["apt", "list", "--upgradable"], 
                                          capture_output=True, text=True)
                    security_count = result.stdout.count('security')
                    status["security_updates"] = security_count
                    
                except subprocess.CalledProcessError:
                    pass
            
            # Check for yum/dnf (RedHat/CentOS/Fedora)
            elif os.path.exists("/usr/bin/yum") or os.path.exists("/usr/bin/dnf"):
                status["package_manager"] = "yum/dnf"
                try:
                    cmd = "dnf" if os.path.exists("/usr/bin/dnf") else "yum"
                    result = subprocess.run([cmd, "check-update"], 
                                          capture_output=True, text=True)
                    if result.stdout:
                        lines = result.stdout.strip().split('\n')
                        status["updates_available"] = len([l for l in lines if l and not l.startswith('#')])
                except subprocess.CalledProcessError:
                    pass
            
            return status
        except Exception as e:
            return {"error": str(e)}
    
    def get_windows_security_status(self):
        """Get Windows security status"""
        try:
            status = {
                "windows_updates": "unknown",
                "antivirus": "unknown",
                "firewall": "unknown",
                "last_update_check": None
            }
            
            # Check Windows Update status using PowerShell
            try:
                ps_command = """
                Get-WUList | Measure-Object | Select-Object -ExpandProperty Count
                """
                result = subprocess.run(["powershell", "-Command", ps_command], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    status["windows_updates"] = int(result.stdout.strip())
            except:
                pass
            
            return status
        except Exception as e:
            return {"error": str(e)}
    
    def get_macos_security_status(self):
        """Get macOS security status"""
        try:
            status = {
                "software_updates": "unknown",
                "system_integrity": "unknown",
                "last_update_check": None
            }
            
            # Check for software updates
            try:
                result = subprocess.run(["softwareupdate", "-l"], 
                                      capture_output=True, text=True)
                if "No new software available" in result.stdout:
                    status["software_updates"] = 0
                else:
                    # Count available updates
                    lines = result.stdout.split('\n')
                    updates = [l for l in lines if l.strip().startswith('*')]
                    status["software_updates"] = len(updates)
            except:
                pass
            
            return status
        except Exception as e:
            return {"error": str(e)}
    
    def get_critical_services(self):
        """Get status of critical services"""
        try:
            services = []
            
            # Common critical services by OS
            if self.os_name == "Linux":
                critical_services = ["ssh", "systemd", "network", "cron"]
            elif self.os_name == "Windows":
                critical_services = ["Themes", "Spooler", "BITS", "Winmgmt"]
            elif self.os_name == "Darwin":
                critical_services = ["com.apple.loginwindow", "com.apple.WindowServer"]
            else:
                critical_services = []
            
            for service in critical_services:
                status = self.check_service_status(service)
                services.append({
                    "name": service,
                    "status": status,
                    "critical": True
                })
            
            return services
        except Exception as e:
            return {"error": str(e)}
    
    def check_service_status(self, service_name):
        """Check if a service is running"""
        try:
            if self.os_name == "Linux":
                result = subprocess.run(["systemctl", "is-active", service_name], 
                                      capture_output=True, text=True)
                return "active" if result.returncode == 0 else "inactive"
            elif self.os_name == "Windows":
                result = subprocess.run(["sc", "query", service_name], 
                                      capture_output=True, text=True)
                return "running" if "RUNNING" in result.stdout else "stopped"
            else:
                return "unknown"
        except:
            return "unknown"
    
    def get_cpu_temperature(self):
        """Get CPU temperature if available"""
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if 'cpu' in name.lower() or 'core' in name.lower():
                            return entries[0].current if entries else None
            return None
        except:
            return None
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
    
    def get_public_ip(self):
        """Get public IP address"""
        try:
            import requests
            response = requests.get("https://api.ipify.org", timeout=5)
            return response.text.strip()
        except:
            return "unknown"
    
    def calculate_health_score(self, report):
        """Calculate overall health score (0-100)"""
        try:
            score = 100
            
            # CPU usage penalty
            if report.get("cpu", {}).get("usage_percent", 0) > 80:
                score -= 20
            elif report.get("cpu", {}).get("usage_percent", 0) > 60:
                score -= 10
            
            # Memory usage penalty
            if report.get("memory", {}).get("usage_percent", 0) > 90:
                score -= 25
            elif report.get("memory", {}).get("usage_percent", 0) > 75:
                score -= 15
            
            # Disk usage penalty
            for disk in report.get("disk", []):
                if disk.get("usage_percent", 0) > 95:
                    score -= 20
                elif disk.get("usage_percent", 0) > 85:
                    score -= 10
            
            # Security updates penalty
            security_updates = report.get("security", {}).get("security_updates", 0)
            if security_updates > 0:
                score -= min(security_updates * 5, 25)
            
            # Service status penalty
            for service in report.get("services", []):
                if service.get("critical") and service.get("status") not in ["active", "running"]:
                    score -= 15
            
            return max(0, min(100, score))
        except:
            return 50  # Default score if calculation fails
    
    def generate_alerts(self, report):
        """Generate alerts based on health data"""
        alerts = []
        
        try:
            # CPU alerts
            cpu_usage = report.get("cpu", {}).get("usage_percent", 0)
            if cpu_usage > 90:
                alerts.append({
                    "level": "critical",
                    "component": "cpu",
                    "message": f"High CPU usage: {cpu_usage:.1f}%"
                })
            elif cpu_usage > 80:
                alerts.append({
                    "level": "warning",
                    "component": "cpu",
                    "message": f"Elevated CPU usage: {cpu_usage:.1f}%"
                })
            
            # Memory alerts
            memory_usage = report.get("memory", {}).get("usage_percent", 0)
            if memory_usage > 95:
                alerts.append({
                    "level": "critical",
                    "component": "memory",
                    "message": f"Critical memory usage: {memory_usage:.1f}%"
                })
            elif memory_usage > 85:
                alerts.append({
                    "level": "warning",
                    "component": "memory",
                    "message": f"High memory usage: {memory_usage:.1f}%"
                })
            
            # Disk alerts
            for disk in report.get("disk", []):
                usage = disk.get("usage_percent", 0)
                if usage > 95:
                    alerts.append({
                        "level": "critical",
                        "component": "disk",
                        "message": f"Critical disk usage on {disk.get('mountpoint', 'unknown')}: {usage:.1f}%"
                    })
                elif usage > 90:
                    alerts.append({
                        "level": "warning",
                        "component": "disk",
                        "message": f"High disk usage on {disk.get('mountpoint', 'unknown')}: {usage:.1f}%"
                    })
            
            # Security alerts
            security_updates = report.get("security", {}).get("security_updates", 0)
            if security_updates > 0:
                alerts.append({
                    "level": "warning",
                    "component": "security",
                    "message": f"{security_updates} security updates available"
                })
            
            # Service alerts
            for service in report.get("services", []):
                if service.get("critical") and service.get("status") not in ["active", "running"]:
                    alerts.append({
                        "level": "critical",
                        "component": "service",
                        "message": f"Critical service '{service.get('name')}' is not running"
                    })
            
        except Exception as e:
            alerts.append({
                "level": "error",
                "component": "system",
                "message": f"Error generating alerts: {str(e)}"
            })
        
        return alerts