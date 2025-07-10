#!/usr/bin/env python3
"""
OS Health Agent Dashboard
Web-based dashboard for monitoring all agents
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
import json
import sqlite3
import os
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Database setup
DB_PATH = 'health_agents.db'

class HealthDashboard:
    def __init__(self):
        self.init_database()
        self.start_cleanup_thread()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT UNIQUE NOT NULL,
                hostname TEXT,
                os_info TEXT,
                local_ip TEXT,
                public_ip TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                agent_version TEXT,
                status TEXT DEFAULT 'online'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                report_data TEXT NOT NULL,
                health_score INTEGER,
                alert_count INTEGER,
                FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'info',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_cleanup_thread(self):
        """Start background thread for cleanup tasks"""
        cleanup_thread = threading.Thread(target=self.cleanup_old_data)
        cleanup_thread.daemon = True
        cleanup_thread.start()
    
    def cleanup_old_data(self):
        """Clean up old data periodically"""
        while True:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Delete health reports older than 7 days
                cutoff_date = datetime.now() - timedelta(days=7)
                cursor.execute(
                    "DELETE FROM health_reports WHERE timestamp < ?",
                    (cutoff_date,)
                )
                
                # Delete resolved alerts older than 30 days
                alert_cutoff = datetime.now() - timedelta(days=30)
                cursor.execute(
                    "DELETE FROM alerts WHERE timestamp < ? AND resolved = TRUE",
                    (alert_cutoff,)
                )
                
                # Update agent status based on last seen
                offline_cutoff = datetime.now() - timedelta(minutes=15)
                cursor.execute(
                    "UPDATE agents SET status = 'offline' WHERE last_seen < ?",
                    (offline_cutoff,)
                )
                
                conn.commit()
                conn.close()
                
                time.sleep(3600)  # Run every hour
                
            except Exception as e:
                print(f"Error in cleanup: {e}")
                time.sleep(3600)
    
    def register_agent(self, agent_data):
        """Register or update agent information"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO agents 
            (agent_id, hostname, os_info, local_ip, public_ip, last_seen, agent_version, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'online')
        ''', (
            agent_data['agent_id'],
            agent_data.get('hostname', 'unknown'),
            agent_data.get('os_info', 'unknown'),
            agent_data.get('local_ip', 'unknown'),
            agent_data.get('public_ip', 'unknown'),
            datetime.now(),
            agent_data.get('agent_version', '1.0.0')
        ))
        
        conn.commit()
        conn.close()
    
    def save_health_report(self, report_data):
        """Save health report to database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Register/update agent
        system_info = report_data.get('system', {})
        agent_info = {
            'agent_id': report_data['agent_id'],
            'hostname': system_info.get('hostname', 'unknown'),
            'os_info': system_info.get('os', 'unknown'),
            'local_ip': system_info.get('local_ip', 'unknown'),
            'public_ip': system_info.get('public_ip', 'unknown'),
            'agent_version': report_data.get('agent_version', '1.0.0')
        }
        self.register_agent(agent_info)
        
        # Save health report
        cursor.execute('''
            INSERT INTO health_reports (agent_id, report_data, health_score, alert_count)
            VALUES (?, ?, ?, ?)
        ''', (
            report_data['agent_id'],
            json.dumps(report_data),
            report_data.get('health_score', 0),
            len(report_data.get('alerts', []))
        ))
        
        # Save alerts
        for alert in report_data.get('alerts', []):
            cursor.execute('''
                INSERT INTO alerts (agent_id, level, component, message)
                VALUES (?, ?, ?, ?)
            ''', (
                report_data['agent_id'],
                alert.get('level', 'info'),
                alert.get('component', 'system'),
                alert.get('message', 'Unknown alert')
            ))
        
        conn.commit()
        conn.close()
        
        # Emit real-time update to dashboard
        socketio.emit('agent_update', {
            'agent_id': report_data['agent_id'],
            'health_score': report_data.get('health_score', 0),
            'alerts': report_data.get('alerts', []),
            'timestamp': datetime.now().isoformat()
        })
    
    def get_all_agents(self):
        """Get all agents with their latest data"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT a.*, 
                   hr.health_score, 
                   hr.alert_count,
                   hr.timestamp as last_report
            FROM agents a
            LEFT JOIN health_reports hr ON a.agent_id = hr.agent_id
            WHERE hr.timestamp = (
                SELECT MAX(timestamp) 
                FROM health_reports 
                WHERE agent_id = a.agent_id
            ) OR hr.timestamp IS NULL
            ORDER BY a.last_seen DESC
        ''')
        
        agents = []
        for row in cursor.fetchall():
            agents.append({
                'agent_id': row[1],
                'hostname': row[2],
                'os_info': row[3],
                'local_ip': row[4],
                'public_ip': row[5],
                'first_seen': row[6],
                'last_seen': row[7],
                'agent_version': row[8],
                'status': row[9],
                'health_score': row[10] or 0,
                'alert_count': row[11] or 0,
                'last_report': row[12]
            })
        
        conn.close()
        return agents
    
    def get_agent_details(self, agent_id):
        """Get detailed information for a specific agent"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get agent info
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        agent_row = cursor.fetchone()
        
        if not agent_row:
            return None
        
        # Get latest health report
        cursor.execute('''
            SELECT report_data FROM health_reports 
            WHERE agent_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (agent_id,))
        
        report_row = cursor.fetchone()
        latest_report = json.loads(report_row[0]) if report_row else {}
        
        # Get recent alerts
        cursor.execute('''
            SELECT level, component, message, timestamp 
            FROM alerts 
            WHERE agent_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', (agent_id,))
        
        alerts = []
        for alert_row in cursor.fetchall():
            alerts.append({
                'level': alert_row[0],
                'component': alert_row[1],
                'message': alert_row[2],
                'timestamp': alert_row[3]
            })
        
        conn.close()
        
        return {
            'agent_id': agent_row[1],
            'hostname': agent_row[2],
            'os_info': agent_row[3],
            'local_ip': agent_row[4],
            'public_ip': agent_row[5],
            'first_seen': agent_row[6],
            'last_seen': agent_row[7],
            'agent_version': agent_row[8],
            'status': agent_row[9],
            'latest_report': latest_report,
            'recent_alerts': alerts
        }
    
    def send_message_to_agent(self, agent_id, title, content, message_type='info'):
        """Send message to specific agent"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (agent_id, title, content, message_type)
            VALUES (?, ?, ?, ?)
        ''', (agent_id, title, content, message_type))
        
        conn.commit()
        conn.close()
    
    def get_pending_messages(self, agent_id):
        """Get pending messages for an agent"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, content, message_type 
            FROM messages 
            WHERE agent_id = ? AND sent = FALSE
            ORDER BY created_at ASC
        ''', (agent_id,))
        
        messages = []
        message_ids = []
        
        for row in cursor.fetchall():
            messages.append({
                'title': row[1],
                'content': row[2],
                'type': row[3]
            })
            message_ids.append(row[0])
        
        # Mark messages as sent
        if message_ids:
            cursor.execute(f'''
                UPDATE messages 
                SET sent = TRUE 
                WHERE id IN ({','.join(['?' for _ in message_ids])})
            ''', message_ids)
            conn.commit()
        
        conn.close()
        return messages

# Initialize dashboard
dashboard = HealthDashboard()

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    agents = dashboard.get_all_agents()
    return render_template('dashboard.html', agents=agents)

@app.route('/agent/<agent_id>')
def agent_details(agent_id):
    """Agent details page"""
    agent = dashboard.get_agent_details(agent_id)
    if not agent:
        return redirect(url_for('index'))
    return render_template('agent_details.html', agent=agent)

@app.route('/api/health-report', methods=['POST'])
def receive_health_report():
    """Receive health report from agent"""
    try:
        report_data = request.json
        dashboard.save_health_report(report_data)
        
        # Get pending messages for this agent
        messages = dashboard.get_pending_messages(report_data['agent_id'])
        
        return jsonify({
            'status': 'success',
            'messages': messages
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """Send message to agent"""
    try:
        data = request.json
        dashboard.send_message_to_agent(
            data['agent_id'],
            data['title'],
            data['content'],
            data.get('type', 'info')
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/agents')
def get_agents():
    """Get all agents data"""
    agents = dashboard.get_all_agents()
    return jsonify(agents)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)