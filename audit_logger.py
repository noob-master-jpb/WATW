"""
Audit Logger for WATW
Maintains comprehensive audit logs and safety controls
"""

import csv
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

class AuditLogger:
    def __init__(self, log_file: str = 'watw_audit.csv', json_log: str = 'watw_audit.json'):
        self.log_file = log_file
        self.json_log = json_log
        self.pending_deletions = {}  # Track pending deletion confirmations
        self.setup_logging()
        self.ensure_log_files()
    
    def setup_logging(self):
        """Setup Python logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('watw_system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('WATW')
    
    def ensure_log_files(self):
        """Ensure audit log files exist with proper headers"""
        
        # CSV audit log
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'user_phone', 'command_type', 'file_path',
                    'destination_path', 'result', 'error_message', 'file_size',
                    'ip_address', 'session_id'
                ])
        
        # JSON audit log
        if not os.path.exists(self.json_log):
            with open(self.json_log, 'w', encoding='utf-8') as f:
                json.dump([], f)
    
    def log_command(self, user_phone: str, command_type: str, file_path: Optional[str] = None,
                   destination_path: Optional[str] = None, result: str = 'success',
                   error_message: Optional[str] = None, additional_data: Dict[str, Any] = None) -> str:
        """Log a command execution"""
        
        timestamp = datetime.now().isoformat()
        log_id = f"{timestamp}_{user_phone}_{command_type}".replace(':', '-')
        
        # Prepare log entry
        log_entry = {
            'log_id': log_id,
            'timestamp': timestamp,
            'user_phone': user_phone,
            'command_type': command_type,
            'file_path': file_path,
            'destination_path': destination_path,
            'result': result,
            'error_message': error_message,
            'additional_data': additional_data or {}
        }
        
        # Log to CSV
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, user_phone, command_type, file_path or '',
                    destination_path or '', result, error_message or '',
                    additional_data.get('file_size', '') if additional_data else '',
                    additional_data.get('ip_address', '') if additional_data else '',
                    log_id
                ])
        except Exception as e:
            self.logger.error(f"Failed to write CSV log: {e}")
        
        # Log to JSON
        try:
            # Read existing logs
            logs = []
            if os.path.exists(self.json_log):
                with open(self.json_log, 'r', encoding='utf-8') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
            
            # Add new log
            logs.append(log_entry)
            
            # Keep only last 10000 entries to prevent file from growing too large
            if len(logs) > 10000:
                logs = logs[-10000:]
            
            # Write back
            with open(self.json_log, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to write JSON log: {e}")
        
        # Python logging
        log_message = f"User {user_phone} executed {command_type}"
        if file_path:
            log_message += f" on {file_path}"
        if destination_path:
            log_message += f" to {destination_path}"
        log_message += f" - Result: {result}"
        
        if result == 'success':
            self.logger.info(log_message)
        else:
            self.logger.warning(f"{log_message} - Error: {error_message}")
        
        return log_id
    
    def require_deletion_confirmation(self, user_phone: str, file_path: str) -> str:
        """Require confirmation for delete operations"""
        
        confirmation_code = f"DELETE_{datetime.now().strftime('%H%M%S')}"
        
        self.pending_deletions[user_phone] = {
            'file_path': file_path,
            'confirmation_code': confirmation_code,
            'timestamp': datetime.now().isoformat(),
            'expires_at': (datetime.now()).isoformat()  # 5 minute expiry
        }
        
        # Log the deletion request
        self.log_command(
            user_phone=user_phone,
            command_type='DELETE_REQUEST',
            file_path=file_path,
            result='pending_confirmation',
            additional_data={'confirmation_code': confirmation_code}
        )
        
        return confirmation_code
    
    def verify_deletion_confirmation(self, user_phone: str, confirmation_message: str) -> Dict[str, Any]:
        """Verify deletion confirmation"""
        
        if user_phone not in self.pending_deletions:
            return {
                'verified': False,
                'error': 'No pending deletion found for this user'
            }
        
        pending = self.pending_deletions[user_phone]
        
        # Check if confirmation message contains the code
        if pending['confirmation_code'] not in confirmation_message.upper():
            return {
                'verified': False,
                'error': 'Invalid confirmation code'
            }
        
        # Check expiry (5 minutes)
        from datetime import datetime, timedelta
        expires_at = datetime.fromisoformat(pending['timestamp']) + timedelta(minutes=5)
        
        if datetime.now() > expires_at:
            # Clean up expired confirmation
            del self.pending_deletions[user_phone]
            return {
                'verified': False,
                'error': 'Confirmation expired. Please try again.'
            }
        
        file_path = pending['file_path']
        
        # Clean up confirmation
        del self.pending_deletions[user_phone]
        
        # Log successful confirmation
        self.log_command(
            user_phone=user_phone,
            command_type='DELETE_CONFIRMED',
            file_path=file_path,
            result='confirmed'
        )
        
        return {
            'verified': True,
            'file_path': file_path
        }
    
    def check_rate_limits(self, user_phone: str, command_type: str, limit_per_hour: int = 50) -> Dict[str, Any]:
        """Check if user is within rate limits"""
        
        # Read recent logs
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        recent_commands = 0
        
        try:
            if os.path.exists(self.json_log):
                with open(self.json_log, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    
                    for log in logs:
                        if (log['user_phone'] == user_phone and 
                            log['timestamp'] > one_hour_ago and
                            log['command_type'] == command_type):
                            recent_commands += 1
        
        except Exception as e:
            self.logger.error(f"Failed to check rate limits: {e}")
            # Allow request if we can't check (fail open)
            return {'allowed': True, 'remaining': limit_per_hour}
        
        allowed = recent_commands < limit_per_hour
        remaining = max(0, limit_per_hour - recent_commands)
        
        if not allowed:
            self.log_command(
                user_phone=user_phone,
                command_type='RATE_LIMIT_EXCEEDED',
                result='blocked',
                additional_data={
                    'attempted_command': command_type,
                    'commands_in_last_hour': recent_commands,
                    'limit': limit_per_hour
                }
            )
        
        return {
            'allowed': allowed,
            'remaining': remaining,
            'used': recent_commands,
            'limit': limit_per_hour
        }
    
    def get_user_statistics(self, user_phone: str, days: int = 7) -> Dict[str, Any]:
        """Get user activity statistics"""
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        stats = {
            'user_phone': user_phone,
            'period_days': days,
            'total_commands': 0,
            'commands_by_type': {},
            'successful_commands': 0,
            'failed_commands': 0,
            'files_accessed': set(),
            'last_activity': None
        }
        
        try:
            if os.path.exists(self.json_log):
                with open(self.json_log, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    
                    user_logs = [log for log in logs 
                               if log['user_phone'] == user_phone and log['timestamp'] > cutoff_date]
                    
                    stats['total_commands'] = len(user_logs)
                    
                    for log in user_logs:
                        # Count by type
                        cmd_type = log['command_type']
                        stats['commands_by_type'][cmd_type] = stats['commands_by_type'].get(cmd_type, 0) + 1
                        
                        # Count success/failure
                        if log['result'] == 'success':
                            stats['successful_commands'] += 1
                        else:
                            stats['failed_commands'] += 1
                        
                        # Track files accessed
                        if log['file_path']:
                            stats['files_accessed'].add(log['file_path'])
                        
                        # Track last activity
                        if not stats['last_activity'] or log['timestamp'] > stats['last_activity']:
                            stats['last_activity'] = log['timestamp']
        
        except Exception as e:
            self.logger.error(f"Failed to get user statistics: {e}")
        
        # Convert set to list for JSON serialization
        stats['files_accessed'] = list(stats['files_accessed'])
        stats['unique_files_accessed'] = len(stats['files_accessed'])
        
        return stats
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        
        health = {
            'timestamp': datetime.now().isoformat(),
            'log_files_exist': {
                'csv': os.path.exists(self.log_file),
                'json': os.path.exists(self.json_log)
            },
            'pending_deletions': len(self.pending_deletions),
            'log_file_sizes': {}
        }
        
        # Get log file sizes
        for file_path in [self.log_file, self.json_log, 'watw_system.log']:
            if os.path.exists(file_path):
                size_bytes = os.path.getsize(file_path)
                health['log_file_sizes'][file_path] = f"{size_bytes / 1024 / 1024:.2f} MB"
        
        # Get recent activity (last 24 hours)
        try:
            if os.path.exists(self.json_log):
                with open(self.json_log, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    
                    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                    recent_logs = [log for log in logs if log['timestamp'] > yesterday]
                    
                    health['last_24h'] = {
                        'total_commands': len(recent_logs),
                        'unique_users': len(set(log['user_phone'] for log in recent_logs)),
                        'success_rate': (len([log for log in recent_logs if log['result'] == 'success']) / len(recent_logs) * 100) if recent_logs else 0
                    }
        
        except Exception as e:
            health['error'] = f"Failed to read logs: {e}"
        
        return health

def test_audit_logger():
    """Test audit logging functionality"""
    
    logger = AuditLogger()
    
    print("📝 Testing Audit Logger...")
    
    # Test basic logging
    log_id = logger.log_command(
        user_phone='+1234567890',
        command_type='LIST',
        file_path='/ProjectX',
        result='success',
        additional_data={'files_found': 5}
    )
    print(f"✅ Logged command: {log_id}")
    
    # Test deletion confirmation
    confirmation_code = logger.require_deletion_confirmation('+1234567890', '/ProjectX/test.pdf')
    print(f"✅ Required confirmation: {confirmation_code}")
    
    # Test rate limiting
    rate_limit = logger.check_rate_limits('+1234567890', 'LIST')
    print(f"✅ Rate limit check: {rate_limit}")
    
    # Test statistics
    stats = logger.get_user_statistics('+1234567890')
    print(f"✅ User statistics: {json.dumps(stats, indent=2)}")
    
    # Test system health
    health = logger.get_system_health()
    print(f"✅ System health: {json.dumps(health, indent=2)}")

if __name__ == "__main__":
    test_audit_logger()
