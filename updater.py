#!/usr/bin/env python3
"""
Agent Updater - Handles automatic updates from GitHub
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import requests
from pathlib import Path
from config import Config

class AgentUpdater:
    def __init__(self):
        self.config = Config()
        self.current_version = self.config.VERSION
        self.agent_dir = Path(__file__).parent.absolute()
        self.version_file = self.agent_dir / "version.txt"
        
    def check_for_updates(self):
        """Check if updates are available"""
        try:
            # Get latest version from GitHub API
            response = requests.get(
                f"https://api.github.com/repos/{self.config.GITHUB_REPO}/releases/latest",
                timeout=10
            )
            
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release["tag_name"].lstrip("v")
                
                print(f"🔍 Current version: {self.current_version}")
                print(f"🔍 Latest version: {latest_version}")
                
                if self.is_newer_version(latest_version, self.current_version):
                    print(f"🆕 Update available: {latest_version}")
                    self.latest_release_data = latest_release
                    return True
                else:
                    print("✅ Agent is up to date")
                    return False
            else:
                print(f"⚠️ Could not check for updates: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking for updates: {e}")
            return False
    
    def is_newer_version(self, latest, current):
        """Compare version strings"""
        try:
            def version_tuple(v):
                return tuple(map(int, v.split('.')))
            
            return version_tuple(latest) > version_tuple(current)
        except:
            return False
    
    def perform_update(self):
        """Download and install the update"""
        try:
            print("🔄 Starting update process...")
            
            # Create backup of current version
            backup_dir = self.create_backup()
            
            try:
                # Download latest release
                download_url = self.get_download_url()
                if not download_url:
                    print("❌ Could not find download URL")
                    return False
                
                # Download and extract
                temp_dir = self.download_and_extract(download_url)
                
                # Install new version
                self.install_new_version(temp_dir)
                
                # Update version file
                self.update_version_file()
                
                print("✅ Update completed successfully!")
                return True
                
            except Exception as e:
                print(f"❌ Update failed: {e}")
                print("🔄 Restoring backup...")
                self.restore_backup(backup_dir)
                return False
                
        except Exception as e:
            print(f"❌ Update process failed: {e}")
            return False
    
    def create_backup(self):
        """Create backup of current agent"""
        try:
            backup_dir = self.agent_dir.parent / f"os-health-agent-backup-{self.current_version}"
            
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            
            shutil.copytree(self.agent_dir, backup_dir)
            print(f"📦 Backup created: {backup_dir}")
            
            return backup_dir
        except Exception as e:
            print(f"⚠️ Could not create backup: {e}")
            return None
    
    def get_download_url(self):
        """Get download URL for the latest release"""
        try:
            for asset in self.latest_release_data["assets"]:
                if asset["name"].endswith(".zip"):
                    return asset["browser_download_url"]
            
            # If no zip asset, try to construct URL
            tag_name = self.latest_release_data["tag_name"]
            return f"https://github.com/{self.config.GITHUB_REPO}/archive/{tag_name}.zip"
            
        except Exception as e:
            print(f"❌ Error getting download URL: {e}")
            return None
    
    def download_and_extract(self, download_url):
        """Download and extract the update"""
        try:
            print(f"⬇️ Downloading update from: {download_url}")
            
            # Download to temporary file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r⬇️ Progress: {progress:.1f}%", end='', flush=True)
                
                print("\n✅ Download completed")
                
                # Extract to temporary directory
                extract_dir = tempfile.mkdtemp()
                
                with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                print(f"📦 Extracted to: {extract_dir}")
                
                # Clean up download file
                os.unlink(tmp_file.name)
                
                return extract_dir
                
        except Exception as e:
            print(f"❌ Error downloading/extracting: {e}")
            return None
    
    def install_new_version(self, temp_dir):
        """Install the new version"""
        try:
            print("🔧 Installing new version...")
            
            # Find the actual source directory (might be nested)
            source_dir = self.find_source_directory(temp_dir)
            if not source_dir:
                raise Exception("Could not find source directory in download")
            
            # List of files to update
            files_to_update = [
                "agent.py",
                "health_report.py",
                "updater.py",
                "config.py",
                "requirements.txt"
            ]
            
            # Copy new files
            for file_name in files_to_update:
                source_file = source_dir / file_name
                dest_file = self.agent_dir / file_name
                
                if source_file.exists():
                    shutil.copy2(source_file, dest_file)
                    print(f"✅ Updated: {file_name}")
                else:
                    print(f"⚠️ File not found in update: {file_name}")
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            print(f"❌ Error installing new version: {e}")
            raise
    
    def find_source_directory(self, temp_dir):
        """Find the actual source directory in the extracted files"""
        try:
            temp_path = Path(temp_dir)
            
            # Look for agent.py in the extracted files
            for root, dirs, files in os.walk(temp_path):
                if "agent.py" in files:
                    return Path(root)
            
            return None
        except:
            return None
    
    def update_version_file(self):
        """Update the local version file"""
        try:
            new_version = self.latest_release_data["tag_name"].lstrip("v")
            
            with open(self.version_file, 'w') as f:
                f.write(new_version)
            
            print(f"📝 Updated version to: {new_version}")
            
        except Exception as e:
            print(f"⚠️ Could not update version file: {e}")
    
    def restore_backup(self, backup_dir):
        """Restore from backup if update fails"""
        try:
            if backup_dir and backup_dir.exists():
                # Remove current directory
                for item in self.agent_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                
                # Restore from backup
                for item in backup_dir.iterdir():
                    if item.is_file():
                        shutil.copy2(item, self.agent_dir)
                    elif item.is_dir():
                        shutil.copytree(item, self.agent_dir / item.name)
                
                print("✅ Backup restored successfully")
                
        except Exception as e:
            print(f"❌ Error restoring backup: {e}")
    
    def rollback_to_previous_version(self):
        """Rollback to previous version if available"""
        try:
            backup_dirs = [d for d in self.agent_dir.parent.iterdir() 
                          if d.is_dir() and d.name.startswith("os-health-agent-backup-")]
            
            if backup_dirs:
                # Use the most recent backup
                latest_backup = max(backup_dirs, key=lambda x: x.stat().st_mtime)
                self.restore_backup(latest_backup)
                return True
            else:
                print("⚠️ No backup available for rollback")
                return False
                
        except Exception as e:
            print(f"❌ Error during rollback: {e}")
            return False
    
    def get_update_info(self):
        """Get information about available updates"""
        try:
            if hasattr(self, 'latest_release_data'):
                return {
                    "version": self.latest_release_data["tag_name"].lstrip("v"),
                    "release_notes": self.latest_release_data.get("body", ""),
                    "published_at": self.latest_release_data.get("published_at", ""),
                    "download_url": self.get_download_url()
                }
            return None
        except:
            return None