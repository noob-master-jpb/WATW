"""
WATW Main Server - Complete WhatsApp File Manager
Integrates all components: webhook handling, command parsing, Google Drive, AI summarization, and audit logging
"""

from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import traceback

# Import our custom modules
from command_parser import CommandParser, CommandType
from google_drive_handler import GoogleDriveHandler
from ai_summarizer import AISummarizer
from audit_logger import AuditLogger

load_dotenv()

app = Flask(__name__)

# Initialize components
parser = CommandParser()
drive_handler = GoogleDriveHandler()
ai_summarizer = AISummarizer()
audit_logger = AuditLogger()

# Store processed messages and user sessions
processed_messages = set()
user_sessions = {}

@app.route('/webhook/whatsapp', methods=['POST'])
def handle_whatsapp():
    """Handle incoming WhatsApp messages via Twilio"""
    try:
        # Get message data from Twilio webhook
        message_sid = request.form.get('MessageSid')
        from_number = request.form.get('From')
        to_number = request.form.get('To')
        body = request.form.get('Body', '').strip()
        profile_name = request.form.get('ProfileName', '')
        
        # Check for duplicate messages
        if message_sid in processed_messages:
            audit_logger.logger.warning(f"Duplicate message {message_sid} from {from_number}")
            return '', 200
        
        processed_messages.add(message_sid)
        
        # Check rate limits
        rate_limit = audit_logger.check_rate_limits(from_number, 'WHATSAPP_MESSAGE', limit_per_hour=30)
        if not rate_limit['allowed']:
            response = MessagingResponse()
            response.message(
                f"⚠️ **Rate limit exceeded**\n\n"
                f"You've sent {rate_limit['used']} messages in the last hour.\n"
                f"Limit: {rate_limit['limit']} messages per hour.\n"
                f"Please wait before sending more commands."
            )
            return str(response), 200
        
        # Parse the command
        parsed_command = parser.parse_message(body)
        
        # Process the command and generate response
        response_text = process_command(parsed_command, from_number, profile_name)
        
        # Create Twilio response
        response = MessagingResponse()
        response.message(response_text)
        
        # Log successful processing
        audit_logger.log_command(
            user_phone=from_number,
            command_type=parsed_command.command_type.value,
            file_path=parsed_command.path,
            destination_path=parsed_command.destination_path,
            result='processed',
            additional_data={
                'message_sid': message_sid,
                'profile_name': profile_name,
                'response_length': len(response_text),
                'rate_limit_remaining': rate_limit['remaining']
            }
        )
        
        return str(response), 200
        
    except Exception as e:
        error_msg = str(e)
        audit_logger.logger.error(f"Webhook error: {error_msg}\n{traceback.format_exc()}")
        
        # Log the error
        audit_logger.log_command(
            user_phone=request.form.get('From', 'unknown'),
            command_type='ERROR',
            result='system_error',
            error_message=error_msg
        )
        
        # Send user-friendly error response
        response = MessagingResponse()
        response.message("❌ Sorry, there was a system error. Please try again later or contact support.")
        return str(response), 500

def process_command(parsed_command, from_number: str, profile_name: str) -> str:
    """Process a parsed command and return response text"""
    
    if parsed_command.command_type == CommandType.INVALID:
        return f"❌ **Invalid Command**\n\n{parsed_command.error_message}\n\nSend `HELP` to see available commands."
    
    elif parsed_command.command_type == CommandType.HELP:
        return get_help_message()
    
    elif parsed_command.command_type == CommandType.LIST:
        return handle_list_command(parsed_command.path, from_number)
    
    elif parsed_command.command_type == CommandType.DELETE:
        return handle_delete_command(parsed_command.path, from_number, parsed_command.raw_message)
    
    elif parsed_command.command_type == CommandType.MOVE:
        return handle_move_command(parsed_command.path, parsed_command.destination_path, from_number)
    
    elif parsed_command.command_type == CommandType.SUMMARY:
        return handle_summary_command(parsed_command.path, from_number)
    
    else:
        return "❌ Unknown command type. Send `HELP` for available commands."

def handle_list_command(path: str, from_number: str) -> str:
    """Handle LIST command - show files in directory"""
    
    # Authenticate with Google Drive if not already done
    if not drive_handler.authenticated:
        if not drive_handler.authenticate():
            audit_logger.log_command(from_number, 'LIST', path, result='auth_failed')
            return "❌ **Authentication Failed**\n\nGoogle Drive authentication required. Please contact administrator."
    
    # List files
    result = drive_handler.list_files(path)
    
    if 'error' in result:
        audit_logger.log_command(from_number, 'LIST', path, result='failed', error_message=result['error'])
        return f"❌ **Error listing files**\n\n{result['error']}"
    
    # Format response
    response_parts = [f"📁 **Files in {result['path']}**\n"]
    
    # Show folders first
    if result['folders']:
        response_parts.append("**📁 Folders:**")
        for folder in result['folders'][:10]:  # Limit to 10 items
            response_parts.append(f"📁 {folder['name']}")
    
    # Show files
    if result['files']:
        response_parts.append("\n**📄 Files:**")
        for file in result['files'][:10]:  # Limit to 10 items
            response_parts.append(f"{file['type']} {file['name']} ({file['size']})")
    
    if not result['folders'] and not result['files']:
        response_parts.append("📭 Folder is empty")
    
    # Add footer
    if result['total_items'] > 10:
        response_parts.append(f"\n... and {result['total_items'] - 10} more items")
    
    response_parts.append(f"\n💡 **Next steps:**")
    response_parts.append(f"• `SUMMARY {path}` - Get AI summary")
    response_parts.append(f"• `LIST {path}/subfolder` - Browse subfolder")
    
    # Log success
    audit_logger.log_command(
        from_number, 'LIST', path, result='success',
        additional_data={'items_found': result['total_items']}
    )
    
    return '\n'.join(response_parts)

def handle_delete_command(path: str, from_number: str, raw_message: str) -> str:
    """Handle DELETE command with confirmation"""
    
    # Check if this is a confirmation message
    if 'DELETE_' in raw_message.upper():
        confirmation_result = audit_logger.verify_deletion_confirmation(from_number, raw_message)
        
        if confirmation_result['verified']:
            # Proceed with actual deletion
            return perform_deletion(confirmation_result['file_path'], from_number)
        else:
            return f"❌ **Confirmation Failed**\n\n{confirmation_result['error']}"
    
    # This is the initial delete request - require confirmation
    confirmation_code = audit_logger.require_deletion_confirmation(from_number, path)
    
    return f"""⚠️ **DELETION CONFIRMATION REQUIRED**

You want to delete: `{path}`

🚨 **This action CANNOT be undone!**

To confirm deletion, reply with:
`{confirmation_code}`

To cancel, ignore this message.

⏰ This confirmation expires in 5 minutes.
🔒 Only files are moved to trash (recoverable)."""

def perform_deletion(file_path: str, from_number: str) -> str:
    """Actually perform the file deletion"""
    
    if not drive_handler.authenticated:
        if not drive_handler.authenticate():
            audit_logger.log_command(from_number, 'DELETE', file_path, result='auth_failed')
            return "❌ **Authentication Failed**\n\nGoogle Drive authentication required."
    
    result = drive_handler.delete_file(file_path)
    
    if 'error' in result:
        audit_logger.log_command(from_number, 'DELETE', file_path, result='failed', error_message=result['error'])
        return f"❌ **Deletion Failed**\n\n{result['error']}"
    
    audit_logger.log_command(from_number, 'DELETE', file_path, result='success')
    
    return f"""✅ **File Deleted Successfully**

File: `{file_path}`
Status: {result['message']}

🗑️ File moved to Google Drive trash
🔄 Can be restored from trash if needed"""

def handle_move_command(source_path: str, destination_path: str, from_number: str) -> str:
    """Handle MOVE command"""
    
    if not drive_handler.authenticated:
        if not drive_handler.authenticate():
            audit_logger.log_command(from_number, 'MOVE', source_path, destination_path, result='auth_failed')
            return "❌ **Authentication Failed**\n\nGoogle Drive authentication required."
    
    result = drive_handler.move_file(source_path, destination_path)
    
    if 'error' in result:
        audit_logger.log_command(from_number, 'MOVE', source_path, destination_path, result='failed', error_message=result['error'])
        return f"❌ **Move Failed**\n\n{result['error']}"
    
    audit_logger.log_command(from_number, 'MOVE', source_path, destination_path, result='success')
    
    return f"""✅ **File Moved Successfully**

From: `{source_path}`
To: `{destination_path}`

📦 File is now in the new location"""

def handle_summary_command(path: str, from_number: str) -> str:
    """Handle SUMMARY command with AI"""
    
    if not drive_handler.authenticated:
        if not drive_handler.authenticate():
            audit_logger.log_command(from_number, 'SUMMARY', path, result='auth_failed')
            return "❌ **Authentication Failed**\n\nGoogle Drive authentication required."
    
    # Check if path is a file or folder
    file_result = drive_handler.get_file_content(path)
    
    if 'error' not in file_result:
        # It's a file - summarize single file
        summary_result = ai_summarizer.summarize_single_file(file_result['content'], path)
        
        if 'error' in summary_result:
            audit_logger.log_command(from_number, 'SUMMARY', path, result='failed', error_message=summary_result['error'])
            return f"❌ **Summarization Failed**\n\n{summary_result['error']}"
        
        audit_logger.log_command(from_number, 'SUMMARY', path, result='success', additional_data={'service': summary_result.get('service')})
        
        return f"""🤖 **AI Summary for {path}**

{summary_result['summary']}

📊 **Details:**
• Service: {summary_result.get('service', 'Unknown')}
• File type: {file_result.get('type', 'Unknown')}
• Content size: {file_result.get('size', 0)} characters"""
    
    else:
        # Assume it's a folder - get folder contents and summarize
        folder_result = drive_handler.list_files(path)
        
        if 'error' in folder_result:
            audit_logger.log_command(from_number, 'SUMMARY', path, result='failed', error_message=folder_result['error'])
            return f"❌ **Summary Failed**\n\n{folder_result['error']}"
        
        # Get content for each file (limited to first 5 files)
        files_with_content = []
        
        for file_info in folder_result['files'][:5]:
            file_path = f"{path.rstrip('/')}/{file_info['name']}"
            content_result = drive_handler.get_file_content(file_path)
            
            if 'error' not in content_result:
                files_with_content.append({
                    'file_path': file_path,
                    'content': content_result['content'],
                    'type': content_result.get('type', 'unknown')
                })
        
        if not files_with_content:
            return f"""📁 **Folder Summary for {path}**

📊 **Contents:**
• {len(folder_result['folders'])} folders
• {len(folder_result['files'])} files

⚠️ No text files found for AI analysis.
Supported formats: PDF, DOCX, TXT, Google Docs"""
        
        # Generate AI summary for folder
        folder_summary = ai_summarizer.summarize_folder(files_with_content)
        
        response_parts = [f"🤖 **AI Folder Summary for {path}**\n"]
        response_parts.append(folder_summary.get('summary', 'Unable to generate summary'))
        response_parts.append(f"\n📊 **Analysis Details:**")
        response_parts.append(f"• Files analyzed: {len(files_with_content)}")
        response_parts.append(f"• Total files in folder: {len(folder_result['files'])}")
        response_parts.append(f"• AI service: {ai_summarizer.get_available_services()[0]}")
        
        if len(folder_result['files']) > 5:
            response_parts.append(f"\n💡 Only first 5 files were analyzed. Use `LIST {path}` to see all files.")
        
        audit_logger.log_command(from_number, 'SUMMARY', path, result='success', 
                                additional_data={'files_analyzed': len(files_with_content)})
        
        return '\n'.join(response_parts)

def get_help_message() -> str:
    """Return comprehensive help message"""
    
    available_services = ai_summarizer.get_available_services()
    
    return f"""📁 **WATW - WhatsApp File Manager**

**📋 Available Commands:**

**List Files:**
• `LIST /ProjectX` - Show files in folder
• `ls /Documents` - Same as LIST

**🗑️ Delete Files:**
• `DELETE /ProjectX/report.pdf` - Delete file (with confirmation)
• `rm /old_file.txt` - Same as DELETE

**📦 Move Files:**
• `MOVE /ProjectX/report.pdf TO /Archive` - Move file
• `mv /source.pdf /destination/` - Same as MOVE

**🤖 AI Summary:**
• `SUMMARY /ProjectX` - Get AI summary of folder
• `sum /document.pdf` - Summarize single file

**ℹ️ Help:**
• `HELP` or `?` - Show this message

**🔒 Safety Features:**
• All operations are logged
• DELETE requires confirmation
• Rate limiting: 30 commands/hour
• Files moved to trash (recoverable)

**🤖 AI Services:** {', '.join(available_services)}

**💡 Tips:**
• Use quotes for paths with spaces
• Folders start with /
• Check `LIST /` to see root folder"""

@app.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check"""
    
    health = audit_logger.get_system_health()
    health.update({
        'service': 'WATW - WhatsApp File Manager',
        'components': {
            'command_parser': '✅ Active',
            'google_drive': '✅ Ready' if drive_handler.authenticated else '⚠️ Not authenticated',
            'ai_summarizer': f"✅ {len(ai_summarizer.get_available_services())} services",
            'audit_logger': '✅ Active'
        },
        'processed_messages': len(processed_messages)
    })
    
    return jsonify(health)

@app.route('/stats/<phone_number>', methods=['GET'])
def get_user_stats(phone_number):
    """Get statistics for a specific user"""
    
    # Add + if not present
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    stats = audit_logger.get_user_statistics(phone_number, days=7)
    return jsonify(stats)

@app.route('/admin/authenticate-drive', methods=['POST'])
def authenticate_drive():
    """Manual Google Drive authentication endpoint"""
    
    try:
        success = drive_handler.authenticate()
        
        if success:
            audit_logger.log_command(
                user_phone='admin',
                command_type='DRIVE_AUTH',
                result='success'
            )
            return jsonify({'success': True, 'message': 'Google Drive authenticated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Authentication failed'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    print("🚀 Starting WATW - WhatsApp File Manager")
    print(f"📱 WhatsApp webhook: http://your-domain.com/webhook/whatsapp")
    print(f"🏥 Health check: http://localhost:{port}/health")
    print(f"📊 User stats: http://localhost:{port}/stats/+1234567890")
    print(f"🔐 Drive auth: http://localhost:{port}/admin/authenticate-drive")
    print("-" * 60)
    
    # Test AI services on startup
    print(f"🤖 Available AI services: {ai_summarizer.get_available_services()}")
    
    app.run(host='0.0.0.0', port=port, debug=True)
