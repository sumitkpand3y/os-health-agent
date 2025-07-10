#!/usr/bin/env python3
"""
OS Health Agent - Main Agent
Monitors system health and reports to central dashboard
"""

import os
import sys
import json
import time
import socket
import platform
import threading
import requests
from datetime import datetime
from health_report import HealthReporter
from updater import AgentUpdater
from config import Config

class OSHealthAgent:
    def __init__(self):
        self.config = Config()
        self.health_reporter = HealthReporter()
        self.updater = AgentUpdater()
        self.agent_id = self.get_agent_id()
        self.running = False
        
    def get_agent_id(self):
        """Generate unique agent ID based on hostname and MAC address"""
        try:
            import uuid
            mac = hex(uuid.getnode())[2:].upper()
            hostname = socket.gethostname()
            return f"{hostname}_{mac}"
        except:
            return f"{socket.gethostname()}_{int(time.time())}"
    
    def start_agent(self):
        """Start the health monitoring agent"""
        print(f"🚀 Starting OS Health Agent v{self.config.VERSION}")
        print(f"📍 Agent ID: {self.agent_id}")
        print(f"🌐 Dashboard URL: {self.config.DASHBOARD_URL}")
        
        self.running = True
        
        # Start update checker in background
        update_thread = threading.Thread(target=self.check_for_updates_loop)
        update_thread.daemon = True
        update_thread.start()
        
        # Main monitoring loop
        while self.running:
            try:
                self.collect_and_send_report()
                time.sleep(self.config.REPORT_INTERVAL)
            except KeyboardInterrupt:
                print("\n🛑 Agent stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(30)  # Wait before retry
    
    def collect_and_send_report(self):
        """Collect system health data and send to dashboard"""
        try:
            # Generate health report
            report = self.health_reporter.generate_report()
            
            # Add agent metadata
            report['agent_id'] = self.agent_id
            report['timestamp'] = datetime.now().isoformat()
            report['agent_version'] = self.config.VERSION
            
            # Send to dashboard
            self.send_to_dashboard(report)
            
            # Save local copy
            self.save_local_report(report)
            
            print(f"✅ Health report sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Error collecting/sending report: {e}")
    
    def send_to_dashboard(self, report):
        """Send health report to central dashboard"""
        try:
            response = requests.post(
                f"{self.config.DASHBOARD_URL}/api/health-report",
                json=report,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                # Check for dashboard messages/alerts
                self.check_dashboard_messages(response.json())
            else:
                print(f"⚠️ Dashboard returned status code: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("⚠️ Could not connect to dashboard - working offline")
        except Exception as e:
            print(f"❌ Error sending to dashboard: {e}")
    
    def check_dashboard_messages(self, response_data):
        """Check for messages/alerts from dashboard"""
        if 'messages' in response_data:
            for message in response_data['messages']:
                self.show_notification(message)
    
    def show_notification(self, message):
        """Show notification to user"""
        print(f"\n🔔 NOTIFICATION: {message['title']}")
        print(f"📝 {message['content']}")
        
        # For Windows/macOS, could use native notifications
        if platform.system() == "Windows":
            try:
                import win10toast
                toaster = win10toast.ToastNotifier()
                toaster.show_toast(message['title'], message['content'], duration=10)
            except ImportError:
                pass
        elif platform.system() == "Darwin":  # macOS
            try:
                os.system(f"osascript -e 'display notification \"{message['content']}\" with title \"{message['title']}\"'")
            except:
                pass
    
    def save_local_report(self, report):
        """Save report locally for offline access"""
        try:
            reports_dir = os.path.join(os.path.expanduser("~"), ".os-health-agent", "reports")
            os.makedirs(reports_dir, exist_ok=True)
            
            filename = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(reports_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            
            # Keep only last 10 reports
            self.cleanup_old_reports(reports_dir)
            
        except Exception as e:
            print(f"⚠️ Could not save local report: {e}")
    
    def cleanup_old_reports(self, reports_dir):
        """Keep only the last 10 reports"""
        try:
            files = [f for f in os.listdir(reports_dir) if f.startswith('health_report_')]
            files.sort(reverse=True)
            
            for file in files[10:]:  # Keep only last 10
                os.remove(os.path.join(reports_dir, file))
        except:
            pass
    
    def check_for_updates_loop(self):
        """Background thread to check for updates"""
        while self.running:
            try:
                if self.updater.check_for_updates():
                    print("🔄 Update available! The agent will restart with the new version.")
                    if self.updater.perform_update():
                        print("✅ Update completed! Restarting agent...")
                        self.restart_agent()
                
                time.sleep(self.config.UPDATE_CHECK_INTERVAL)
                
            except Exception as e:
                print(f"❌ Error checking for updates: {e}")
                time.sleep(300)  # Wait 5 minutes before retry
    
    def restart_agent(self):
        """Restart the agent after update"""
        try:
            self.running = False
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"❌ Error restarting agent: {e}")
    
    def stop_agent(self):
        """Stop the agent gracefully"""
        self.running = False
        print("🛑 Agent stopped")

def main():
    """Main entry point"""
    agent = OSHealthAgent()
    
    try:
        agent.start_agent()
    except KeyboardInterrupt:
        agent.stop_agent()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()