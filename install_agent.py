#!/usr/bin/env python3
"""
Universal OS Health Agent Installer
Works on Windows, Linux, and macOS
"""

import os
import sys
import platform
import subprocess
import urllib.request
import zipfile
import shutil
import tempfile
from pathlib import Path
import json
import stat

class AgentInstaller:
    def __init__(self):
        self.os_name = platform.system()
        self.agent_dir = Path.home() / "os-health-agent"
        self.service_name = "os-health-agent"
        self.github_repo = "sumitkpand3y/os-health-agent"  # Replace with actual repo
        
    def install(self):
        """Main installation process"""
        print("🚀 OS Health Agent Universal Installer")
        print("=" * 50)
        print(f"🖥️  Detected OS: {self.os_name}")
        print(f"📁 Installation directory: {self.agent_dir}")
        
        try:
            # Check if Python is available
            self.check_python()
            
            # Download agent files
            self.download_agent()
            
            # Install dependencies
            self.install_dependencies()
            
            # Setup service/daemon
            self.setup_service()
            
            # Start the agent
            self.start_agent()
            
            print("\n✅ Installation completed successfully!")
            print(f"🎯 Agent installed in: {self.agent_dir}")
            print("📊 Check the dashboard for monitoring data")
            
        except Exception as e:
            print(f"\n❌ Installation failed: {e}")
            self.cleanup()
            sys.exit(1)
    
    def check_python(self):
        """Check if Python 3.6+ is available"""
        try:
            version = sys.version_info
            if version.major < 3 or (version.major == 3 and version.minor < 6):
                raise Exception("Python 3.6+ is required")
            print(f"✅ Python {version.major}.{version.minor} detected")
        except Exception as e:
            raise Exception(f"Python check failed: {e}")
    
    def download_agent(self):
        """Download agent files from GitHub"""
        print("\n📥 Downloading agent files...")
        
        try:
            # Create installation directory
            self.agent_dir.mkdir(parents=True, exist_ok=True)
            
            # Download latest release
            download_url = f"https://github.com/{self.github_repo}/archive/main.zip"
            
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                print(f"⬇️  Downloading from: {download_url}")
                urllib.request.urlretrieve(download_url, tmp_file.name)
                
                # Extract files
                with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                    extract_dir = tempfile.mkdtemp()
                    zip_ref.extractall(extract_dir)
                    
                    # Find source directory
                    source_dir = None
                    for root, dirs, files in os.walk(extract_dir):
                        if "agent.py" in files:
                            source_dir = Path(root)
                            break
                    
                    if not source_dir:
                        raise Exception("Could not find agent files in download")
                    
                    # Copy files to installation directory
                    files_to_copy = [
                        "agent.py", "health_report.py", "updater.py", 
                        "config.py", "requirements.txt", "version.txt"
                    ]
                    
                    for file_name in files_to_copy:
                        src = source_dir / file_name
                        dst = self.agent_dir / file_name
                        
                        if src.exists():
                            shutil.copy2(src, dst)
                            print(f"✅ Copied: {file_name}")
                        else:
                            print(f"⚠️  File not found: {file_name}")
                
                # Cleanup
                os.unlink(tmp_file.name)
                shutil.rmtree(extract_dir)
                
            print("✅ Agent files downloaded successfully")
            
        except Exception as e:
            raise Exception(f"Download failed: {e}")
    
    def install_dependencies(self):
        """Install Python dependencies"""
        print("\n📦 Installing dependencies...")
        
        try:
            # Install pip if not available
            try:
                subprocess.run([sys.executable, "-m", "pip", "--version"], 
                             check=True, capture_output=True)
            except subprocess.CalledProcessError:
                print("📦 Installing pip...")
                subprocess.run([sys.executable, "-m", "ensurepip", "--default-pip"], 
                             check=True)
            
            # Install requirements
            requirements_file = self.agent_dir / "requirements.txt"
            if requirements_file.exists():
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
                ], check=True)
                print("✅ Dependencies installed")
            else:
                print("⚠️  requirements.txt not found, installing basic dependencies")
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "psutil", "requests"
                ], check=True)
                
        except Exception as e:
            raise Exception(f"Dependency installation failed: {e}")
    
    def setup_service(self):
        """Setup service/daemon based on OS"""
        print(f"\n🔧 Setting up service for {self.os_name}...")
        
        try:
            if self.os_name == "Windows":
                self.setup_windows_service()
            elif self.os_name == "Linux":
                self.setup_linux_service()
            elif self.os_name == "Darwin":  # macOS
                self.setup_macos_service()
            else:
                print(f"⚠️  Unsupported OS: {self.os_name}")
                print("🔧 You'll need to manually set up the service")
                
        except Exception as e:
            print(f"⚠️  Service setup failed: {e}")
            print("🔧 Agent can still be run manually")
    
    def setup_windows_service(self):
        """Setup Windows service using Task Scheduler"""
        print("🔧 Setting up Windows Task Scheduler...")
        
        # Create batch file to run the agent
        batch_file = self.agent_dir / "run_agent.bat"
        with open(batch_file, 'w') as f:
            f.write(f'@echo off\n')
            f.write(f'cd /d "{self.agent_dir}"\n')
            f.write(f'"{sys.executable}" agent.py\n')
        
        # Create scheduled task
        task_xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>ServiceAccount</LogonType>
      <UserId>S-1-5-18</UserId>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions>
    <Exec>
      <Command>"{batch_file}"</Command>
      <WorkingDirectory>"{self.agent_dir}"</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
        
        try:
            # Save task XML
            task_file = self.agent_dir / "task.xml"
            with open(task_file, 'w') as f:
                f.write(task_xml)
            
            # Create scheduled task
            subprocess.run([
                "schtasks", "/create", "/tn", self.service_name, 
                "/xml", str(task_file)
            ], check=True)
            
            print("✅ Windows service setup complete")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Could not create scheduled task: {e}")
            print("🔧 Try running as administrator")
    
    def setup_linux_service(self):
        """Setup Linux systemd service"""
        print("🔧 Setting up systemd service...")
        
        service_content = f'''[Unit]
Description=OS Health Agent
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={self.agent_dir}
ExecStart={sys.executable} {self.agent_dir}/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
'''
        
        try:
            # Write service file
            service_file = Path(f"/etc/systemd/system/{self.service_name}.service")
            
            # Try to write service file (requires sudo)
            try:
                subprocess.run([
                    "sudo", "tee", str(service_file)
                ], input=service_content, text=True, check=True)
                
                # Reload systemd and enable service
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                subprocess.run(["sudo", "systemctl", "enable", self.service_name], check=True)
                
                print("✅ Linux service setup complete")
                
            except subprocess.CalledProcessError:
                # Fallback: create user service
                user_service_dir = Path.home() / ".config" / "systemd" / "user"
                user_service_dir.mkdir(parents=True, exist_ok=True)
                
                user_service_file = user_service_dir / f"{self.service_name}.service"
                with open(user_service_file, 'w') as f:
                    f.write(service_content.replace('[Install]\nWantedBy=multi-user.target', 
                                                  '[Install]\nWantedBy=default.target'))
                
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
                subprocess.run(["systemctl", "--user", "enable", self.service_name], check=True)
                
                print("✅ Linux user service setup complete")
                
        except Exception as e:
            raise Exception(f"Linux service setup failed: {e}")
    
    def setup_macos_service(self):
        """Setup macOS LaunchAgent"""
        print("🔧 Setting up macOS LaunchAgent...")
        
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.{self.service_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{self.agent_dir}/agent.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{self.agent_dir}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{self.agent_dir}/agent.log</string>
    <key>StandardErrorPath</key>
    <string>{self.agent_dir}/agent.log</string>
</dict>
</plist>'''
        
        try:
            # Create LaunchAgents directory
            launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
            launch_agents_dir.mkdir(parents=True, exist_ok=True)
            
            # Write plist file
            plist_file = launch_agents_dir / f"com.user.{self.service_name}.plist"
            with open(plist_file, 'w') as f:
                f.write(plist_content)
            
            # Load the service
            subprocess.run(["launchctl", "load", str(plist_file)], check=True)
            
            print("✅ macOS service setup complete")
            
        except Exception as e:
            raise Exception(f"macOS service setup failed: {e}")
    
    def start_agent(self):
        """Start the agent service"""
        print(f"\n🚀 Starting {self.service_name}...")
        
        try:
            if self.os_name == "Windows":
                subprocess.run([
                    "schtasks", "/run", "/tn", self.service_name
                ], check=True)
            elif self.os_name == "Linux":
                try:
                    subprocess.run(["sudo", "systemctl", "start", self.service_name], check=True)
                except subprocess.CalledProcessError:
                    subprocess.run(["systemctl", "--user", "start", self.service_name], check=True)
            elif self.os_name == "Darwin":
                # Service should already be running due to RunAtLoad
                print("✅ macOS service should be running automatically")
            
            print("✅ Agent started successfully")
            
        except Exception as e:
            print(f"⚠️  Could not start service: {e}")
            print("🔧 You can manually start the agent by running:")
            print(f"   python {self.agent_dir}/agent.py")
    
    def cleanup(self):
        """Clean up installation files on failure"""
        print("\n🧹 Cleaning up...")
        
        try:
            if self.agent_dir.exists():
                shutil.rmtree(self.agent_dir)
            print("✅ Cleanup complete")
        except Exception as e:
            print(f"⚠️  Cleanup failed: {e}")
    
    def uninstall(self):
        """Uninstall the agent"""
        print("🗑️  Uninstalling OS Health Agent...")
        
        try:
            # Stop service
            if self.os_name == "Windows":
                subprocess.run([
                    "schtasks", "/end", "/tn", self.service_name
                ], capture_output=True)
                subprocess.run([
                    "schtasks", "/delete", "/tn", self.service_name, "/f"
                ], capture_output=True)
            elif self.os_name == "Linux":
                subprocess.run([
                    "sudo", "systemctl", "stop", self.service_name
                ], capture_output=True)
                subprocess.run([
                    "sudo", "systemctl", "disable", self.service_name
                ], capture_output=True)
                subprocess.run([
                    "sudo", "rm", f"/etc/systemd/system/{self.service_name}.service"
                ], capture_output=True)
            elif self.os_name == "Darwin":
                plist_file = Path.home() / "Library" / "LaunchAgents" / f"com.user.{self.service_name}.plist"
                if plist_file.exists():
                    subprocess.run([
                        "launchctl", "unload", str(plist_file)
                    ], capture_output=True)
                    plist_file.unlink()
            
            # Remove files
            if self.agent_dir.exists():
                shutil.rmtree(self.agent_dir)
            
            print("✅ Agent uninstalled successfully")
            
        except Exception as e:
            print(f"⚠️  Uninstall failed: {e}")


def main():
    """Main entry point"""
    installer = AgentInstaller()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "uninstall":
            installer.uninstall()
        elif sys.argv[1] == "install":
            installer.install()
        else:
            print("Usage: python installer.py [install|uninstall]")
    else:
        installer.install()


if __name__ == "__main__":
    main()