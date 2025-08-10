"""
WhatsApp File Manager - Command Parser
Parses incoming WhatsApp messages and extracts file management commands
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

class CommandType(Enum):
    LIST = "LIST"
    DELETE = "DELETE" 
    MOVE = "MOVE"
    SUMMARY = "SUMMARY"
    HELP = "HELP"
    INVALID = "INVALID"

@dataclass
class ParsedCommand:
    command_type: CommandType
    path: Optional[str] = None
    destination_path: Optional[str] = None
    parameters: Dict[str, Any] = None
    raw_message: str = ""
    error_message: Optional[str] = None

class CommandParser:
    def __init__(self):
        # Define command patterns - allow spaces in file/folder names
        self.patterns = {
            CommandType.LIST: [
                r'^LIST\s+(.+)$',
                r'^list\s+(.+)$',
                r'^ls\s+(.+)$'
            ],
            CommandType.DELETE: [
                r'^DELETE\s+(.+)$',
                r'^delete\s+(.+)$',
                r'^rm\s+(.+)$'
            ],
            CommandType.MOVE: [
                r'^MOVE\s+(.+?)\s+TO\s+(.+)$',
                r'^move\s+(.+?)\s+to\s+(.+)$',
                r'^mv\s+(.+?)\s+(.+)$'
            ],
            CommandType.SUMMARY: [
                r'^SUMMARY\s+(.+)$',
                r'^summary\s+(.+)$',
                r'^sum\s+(.+)$'
            ],
            CommandType.HELP: [
                r'^HELP$',
                r'^help$',
                r'^\?$',
                r'^commands$'
            ]
        }
    
    def parse_message(self, message: str) -> ParsedCommand:
        """Parse a WhatsApp message and extract command"""
        message = message.strip()
        
        if not message:
            return ParsedCommand(
                command_type=CommandType.INVALID,
                raw_message=message,
                error_message="Empty message"
            )
        
        # Try to match each command type
        for command_type, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.match(pattern, message, re.IGNORECASE)
                if match:
                    return self._create_command(command_type, match, message)
        
        # No pattern matched
        return ParsedCommand(
            command_type=CommandType.INVALID,
            raw_message=message,
            error_message=f"Unknown command: {message[:50]}..."
        )
    
    def _create_command(self, command_type: CommandType, match: re.Match, raw_message: str) -> ParsedCommand:
        """Create a ParsedCommand from regex match"""
        
        if command_type == CommandType.HELP:
            return ParsedCommand(
                command_type=command_type,
                raw_message=raw_message
            )
        
        elif command_type in [CommandType.LIST, CommandType.DELETE, CommandType.SUMMARY]:
            path = match.group(1) if match.groups() else None
            return ParsedCommand(
                command_type=command_type,
                path=self._normalize_path(path),
                raw_message=raw_message
            )
        
        elif command_type == CommandType.MOVE:
            source_path = match.group(1) if match.groups() and len(match.groups()) >= 1 else None
            dest_path = match.group(2) if match.groups() and len(match.groups()) >= 2 else None
            
            return ParsedCommand(
                command_type=command_type,
                path=self._normalize_path(source_path),
                destination_path=self._normalize_path(dest_path),
                raw_message=raw_message
            )
        
        return ParsedCommand(
            command_type=CommandType.INVALID,
            raw_message=raw_message,
            error_message="Failed to parse command"
        )
    
    def _normalize_path(self, path: Optional[str]) -> Optional[str]:
        """Normalize file paths"""
        if not path:
            return None
            
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
            
        # Remove duplicate slashes
        path = re.sub(r'/+', '/', path)
        
        # Remove trailing slash (except for root)
        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]
            
        return path
    
    def get_help_message(self) -> str:
        """Return help message with available commands"""
        return """📁 **WhatsApp File Manager Commands**

**List files:**
• `LIST /ProjectX` - Show files in /ProjectX folder
• `ls /ProjectX` - Same as LIST

**Delete files:**
• `DELETE /ProjectX/report.pdf` - Delete specific file
• `rm /ProjectX/report.pdf` - Same as DELETE

**Move files:**
• `MOVE /ProjectX/report.pdf /Archive` - Move file to Archive
• `mv /ProjectX/report.pdf /Archive` - Same as MOVE

**AI Summary:**
• `SUMMARY /ProjectX` - Get AI summary of folder contents
• `sum /ProjectX` - Same as SUMMARY

**Help:**
• `HELP` or `?` - Show this message

**Safety Notes:**
⚠️ DELETE operations require confirmation
🔒 Only authenticated users can access files
📝 All operations are logged for audit"""

def test_parser():
    """Test the command parser with sample messages"""
    parser = CommandParser()
    
    test_messages = [
        "LIST /ProjectX",
        "delete /ProjectX/report.pdf", 
        "MOVE /ProjectX/report.pdf /Archive",
        "summary /ProjectX",
        "help",
        "invalid command",
        "",
        "list /My Documents/Important Files"
    ]
    
    print("🧪 Testing Command Parser")
    print("=" * 50)
    
    for msg in test_messages:
        result = parser.parse_message(msg)
        print(f"Input: '{msg}'")
        print(f"Command: {result.command_type.value}")
        print(f"Path: {result.path}")
        print(f"Destination: {result.destination_path}")
        if result.error_message:
            print(f"Error: {result.error_message}")
        print("-" * 30)

if __name__ == "__main__":
    test_parser()
