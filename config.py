#!/usr/bin/env python3
"""
Configuration settings for OS Health Agent
"""

import os
from pathlib import Path

class Config:
    # Agent version
    VERSION = "1.0.0"
    
    # GitHub repository for updates
    GITHUB_REPO = "yourusername/os-health-agent"  # Replace with your actual repo
    
    # Dashboard URL (replace with your actual dashboard URL)
    DASHBOARD_URL = "https://your-dashboard.herokuapp.com"  # Or your server
    
    # Reporting intervals (in seconds)
    REPORT_INTERVAL = 300  # 5 minutes
    UPDATE_CHECK_INTERVAL = 3600  # 1 hour
    
    # Agent settings
    MAX_RETRIES = 3
    RETRY_DELAY = 30
    
    # Local storage settings
    AGENT_DIR = Path(__file__).parent.absolute()
    DATA_DIR = Path.home() / ".os-health-agent"
    LOGS_DIR = DATA_DIR / "logs"
    REPORTS_DIR = DATA_DIR / "reports"
    
    # Dashboard API endpoints
    API_ENDPOINTS = {
        "health_report": "/api/health-report",
        "agent_register": "/api/agent/register",
        "agent_status": "/api/agent/status",
        "messages": "/api/messages"
    }
    
    # Alert thresholds
    THRESHOLDS = {
        "cpu_warning": 75,
        "cpu_critical": 90,
        "memory_warning": 80,
        "memory_critical": 95,
        "disk_warning": 85,
        "disk_critical": 95,
        "temperature_warning": 70,
        "temperature_critical": 85
    }
    
    # Critical services by OS
    CRITICAL_SERVICES = {
        "Linux": [
            "ssh", "sshd", "systemd", "networkd", "resolved", "cron", "rsyslog"
        ],
        "Windows": [
            "Themes", "Spooler", "BITS", "Winmgmt", "EventLog", "Dhcp"
        ],
        "Darwin": [
            "com.apple.loginwindow", "com.apple.WindowServer", "com.apple.networkd"
        ]
    }
    
    # Security check settings
    SECURITY_CHECKS = {
        "check_updates": True,
        "check_firewall": True,
        "check_antivirus": True,
        "check_failed_logins": True
    }
    
    def __init__(self):
        # Create necessary directories
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.REPORTS_DIR.mkdir(exist_ok=True)
        
        # Load version from file if it exists
        version_file = self.AGENT_DIR / "version.txt"
        if version_file.exists():
            try:
                with open(version_file, 'r') as f:
                    self.VERSION = f.read().strip()
            except:
                pass
        
        # Override with environment variables if set
        self.load_from_environment()
    
    def load_from_environment(self):
        """Load configuration from environment variables"""
        env_mappings = {
            "DASHBOARD_URL": "HEALTH_AGENT_DASHBOARD_URL",
            "GITHUB_REPO": "HEALTH_AGENT_GITHUB_REPO",
            "REPORT_INTERVAL": "HEALTH_AGENT_REPORT_INTERVAL",
            "UPDATE_CHECK_INTERVAL": "HEALTH_AGENT_UPDATE_INTERVAL"
        }
        
        for attr, env_var in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                if attr in ["REPORT_INTERVAL", "UPDATE_CHECK_INTERVAL"]:
                    try:
                        setattr(self, attr, int(env_value))
                    except ValueError:
                        pass
                else:
                    setattr(self, attr, env_value)
    
    def get_dashboard_url(self, endpoint):
        """Get full URL for dashboard endpoint"""
        return f"{self.DASHBOARD_URL}{self.API_ENDPOINTS.get(endpoint, '')}"
    
    def get_critical_services(self, os_name):
        """Get critical services for specific OS"""
        return self.CRITICAL_SERVICES.get(os_name, [])
    
    def get_threshold(self, metric, level="warning"):
        """Get threshold value for a metric"""
        key = f"{metric}_{level}"
        return self.THRESHOLDS.get(key, 80)
    
    def to_dict(self):
        """Convert configuration to dictionary"""
        return {
            "version": self.VERSION,
            "dashboard_url": self.DASHBOARD_URL,
            "report_interval": self.REPORT_INTERVAL,
            "update_check_interval": self.UPDATE_CHECK_INTERVAL,
            "thresholds": self.THRESHOLDS,
            "security_checks": self.SECURITY_CHECKS
        }