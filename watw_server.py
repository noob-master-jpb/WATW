"""
WhatsApp File Manager - Enhanced Webhook Server
Integrates command parsing with WhatsApp webhook handling
"""

from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import os
from dotenv import load_dotenv
from command_parser import CommandParser, CommandType
import logging
from datetime import datetime

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('watw_audit.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
parser = CommandParser()

# Store processed messages (in production, use a database)
processed_messages = set()

@app.route('/webhook/whatsapp', methods=['POST'])
def handle_whatsapp():
    """Handle incoming WhatsApp messages via Twilio"""
    try:
        # Get message data from Twilio webhook
        message_sid = request.form.get('MessageSid')
        from_number = request.form.get('From')
        to_number = request.form.get('To')
        body = request.form.get('Body', '')
        profile_name = request.form.get('ProfileName', '')
        
        # Log incoming message
        logging.info(f"Incoming WhatsApp message from {from_number} ({profile_name}): {body[:100]}...")
        
        # Check if we've already processed this message
        if message_sid in processed_messages:
            logging.warning(f"Message {message_sid} already processed, skipping...")
            return '', 200
        
        # Add to processed messages
        processed_messages.add(message_sid)
        
        # Parse the command
        parsed_command = parser.parse_message(body)
        
        # Process the command and generate response
        response_text = process_command(parsed_command, from_number)
        
        # Create Twilio response
        response = MessagingResponse()
        response.message(response_text)
        
        # Log response
        logging.info(f"Responding to {from_number}: {response_text[:100]}...")
        
        return str(response), 200
        
    except Exception as e:
        logging.error(f"Error processing WhatsApp webhook: {e}")
        
        # Send error response to user
        response = MessagingResponse()
        response.message("❌ Sorry, there was an error processing your request. Please try again later.")
        return str(response), 500

def process_command(parsed_command, from_number: str) -> str:
    """Process a parsed command and return response text"""
    
    # Log the command attempt
    logging.info(f"Processing {parsed_command.command_type.value} command from {from_number}")
    
    if parsed_command.command_type == CommandType.INVALID:
        return f"❌ {parsed_command.error_message}\n\nSend 'HELP' to see available commands."
    
    elif parsed_command.command_type == CommandType.HELP:
        return parser.get_help_message()
    
    elif parsed_command.command_type == CommandType.LIST:
        return handle_list_command(parsed_command.path, from_number)
    
    elif parsed_command.command_type == CommandType.DELETE:
        return handle_delete_command(parsed_command.path, from_number)
    
    elif parsed_command.command_type == CommandType.MOVE:
        return handle_move_command(parsed_command.path, parsed_command.destination_path, from_number)
    
    elif parsed_command.command_type == CommandType.SUMMARY:
        return handle_summary_command(parsed_command.path, from_number)
    
    else:
        return "❌ Unknown command type. Send 'HELP' for available commands."

def handle_list_command(path: str, from_number: str) -> str:
    """Handle LIST command - show files in directory"""
    # TODO: Implement Google Drive integration
    logging.info(f"LIST command for path: {path} by {from_number}")
    
    # Placeholder response
    return f"""📁 **Files in {path}:**

📄 report.pdf (2.3 MB)
📊 spreadsheet.xlsx (456 KB) 
📝 notes.txt (12 KB)
📁 subfolder/

💡 Send `SUMMARY {path}` for AI content summary
⚙️ Google Drive integration: Coming soon!"""

def handle_delete_command(path: str, from_number: str) -> str:
    """Handle DELETE command - delete file with confirmation"""
    # TODO: Implement Google Drive integration with safety checks
    logging.warning(f"DELETE command for path: {path} by {from_number}")
    
    # Safety check - require confirmation
    return f"""⚠️ **CONFIRM DELETION**

You want to delete: `{path}`

🚨 This action CANNOT be undone!

To confirm, reply with:
`DELETE CONFIRM {path}`

To cancel, ignore this message.

⚙️ Google Drive integration: Coming soon!"""

def handle_move_command(source_path: str, dest_path: str, from_number: str) -> str:
    """Handle MOVE command - move file between locations"""
    # TODO: Implement Google Drive integration
    logging.info(f"MOVE command: {source_path} -> {dest_path} by {from_number}")
    
    return f"""📦 **Move Operation**

From: `{source_path}`
To: `{dest_path}`

✅ File moved successfully!

⚙️ Google Drive integration: Coming soon!"""

def handle_summary_command(path: str, from_number: str) -> str:
    """Handle SUMMARY command - AI-powered content summary"""
    # TODO: Implement AI summarization with OpenAI/Claude
    logging.info(f"SUMMARY command for path: {path} by {from_number}")
    
    return f"""🤖 **AI Summary for {path}:**

📊 **Files Analyzed:** 3 documents

**Key Points:**
• Project status report shows 85% completion
• Budget remains within allocated limits
• Next milestone due in 2 weeks
• Risk assessment identifies 2 minor issues
• Team performance metrics are positive

**File Breakdown:**
📄 report.pdf - Project progress and metrics
📊 budget.xlsx - Financial tracking spreadsheet  
📝 notes.txt - Meeting notes and action items

🔄 Powered by AI • ⚙️ Full integration: Coming soon!"""

@app.route('/webhook/status', methods=['POST'])
def handle_status():
    """Handle message status updates"""
    try:
        message_sid = request.form.get('MessageSid')
        message_status = request.form.get('MessageStatus')
        
        logging.info(f"Status update for {message_sid}: {message_status}")
        return '', 200
        
    except Exception as e:
        logging.error(f"Error processing status webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'WATW - WhatsApp File Manager',
        'processed_messages': len(processed_messages),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    return jsonify({
        'total_messages_processed': len(processed_messages),
        'service_uptime': 'Running',
        'features': {
            'command_parsing': '✅ Active',
            'google_drive': '🔄 Coming Soon',
            'ai_summarization': '🔄 Coming Soon',
            'audit_logging': '✅ Active'
        }
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    print("🚀 Starting WATW - WhatsApp File Manager")
    print(f"📱 WhatsApp webhook: http://your-domain.com/webhook/whatsapp")
    print(f"📊 Stats: http://your-domain.com/stats")
    print(f"🏥 Health: http://your-domain.com/health")
    print("-" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=True)
