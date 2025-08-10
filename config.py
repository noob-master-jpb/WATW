"""
WATW Configuration Management
Centralized configuration for all components
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class Config:
    """Application configuration"""
    
    def __init__(self):
        load_dotenv()

        # Twilio Configuration
        self.TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
        self.TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

        # AI Configuration
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

        # Google Drive Configuration
        self.GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.GOOGLE_TOKEN_FILE = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')

        # Flask Configuration
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
        self.FLASK_ENV = os.getenv('FLASK_ENV', 'development')
        self.PORT = int(os.getenv('PORT', 5000))
        
        # Audit Configuration
        self.AUDIT_CSV_FILE = os.getenv('AUDIT_CSV_FILE', 'watw_audit.csv')
        self.AUDIT_JSON_FILE = os.getenv('AUDIT_JSON_FILE', 'watw_audit.json')
        self.SYSTEM_LOG_FILE = os.getenv('SYSTEM_LOG_FILE', 'watw_system.log')
        
        # Rate Limiting
        self.RATE_LIMIT_PER_HOUR = int(os.getenv('RATE_LIMIT_PER_HOUR', 30))
        self.MAX_MESSAGE_LENGTH = int(os.getenv('MAX_MESSAGE_LENGTH', 1600))
        
        # Security
        self.REQUIRE_DELETE_CONFIRMATION = os.getenv('REQUIRE_DELETE_CONFIRMATION', 'true').lower() == 'true'
        self.CONFIRMATION_EXPIRE_MINUTES = int(os.getenv('CONFIRMATION_EXPIRE_MINUTES', 5))
        
        # File Processing
        self.MAX_FILES_PER_SUMMARY = int(os.getenv('MAX_FILES_PER_SUMMARY', 5))
        self.MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 8000))
        
        # n8n Configuration
        self.N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL')
        self.N8N_USERNAME = os.getenv('N8N_USERNAME')
        self.N8N_PASSWORD = os.getenv('N8N_PASSWORD')
        
    def validate(self) -> Dict[str, Any]:
        """Validate configuration and return status"""
        
        issues = []
        warnings = []
        
        # Required configurations
        if not self.TWILIO_ACCOUNT_SID:
            issues.append("TWILIO_ACCOUNT_SID is required")
        
        if not self.TWILIO_AUTH_TOKEN:
            issues.append("TWILIO_AUTH_TOKEN is required")
        
        if not os.path.exists(self.GOOGLE_CREDENTIALS_FILE):
            issues.append(f"Google credentials file not found: {self.GOOGLE_CREDENTIALS_FILE}")
        
        # Optional but recommended
        if not self.OPENAI_API_KEY and not self.ANTHROPIC_API_KEY:
            warnings.append("No AI API keys configured - AI summarization will not be available")
        
        if self.FLASK_ENV == 'production' and self.SECRET_KEY == 'dev-key-change-in-production':
            issues.append("SECRET_KEY must be changed in production")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def get_ai_config(self) -> Dict[str, Optional[str]]:
        """Get AI service configuration"""
        return {
            'openai_key': self.OPENAI_API_KEY,
            'anthropic_key': self.ANTHROPIC_API_KEY,
            'max_content_length': self.MAX_CONTENT_LENGTH
        }
    
    def get_audit_config(self) -> Dict[str, Any]:
        """Get audit configuration"""
        return {
            'csv_file': self.AUDIT_CSV_FILE,
            'json_file': self.AUDIT_JSON_FILE,
            'system_log': self.SYSTEM_LOG_FILE,
            'rate_limit_per_hour': self.RATE_LIMIT_PER_HOUR,
            'require_delete_confirmation': self.REQUIRE_DELETE_CONFIRMATION,
            'confirmation_expire_minutes': self.CONFIRMATION_EXPIRE_MINUTES
        }
    
    def get_drive_config(self) -> Dict[str, str]:
        """Get Google Drive configuration"""
        return {
            'credentials_file': self.GOOGLE_CREDENTIALS_FILE,
            'token_file': self.GOOGLE_TOKEN_FILE
        }

# Global configuration instance
config = Config()

def validate_config() -> bool:
    """Validate configuration and print status"""
    validation = config.validate()
    
    print("🔧 WATW Configuration Status")
    print("=" * 40)
    
    if validation['valid']:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has issues:")
        for issue in validation['issues']:
            print(f"  - {issue}")
    
    if validation['warnings']:
        print("\n⚠️ Warnings:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
    
    print("\n📊 Configuration Summary:")
    print(f"  - Twilio: {'✅' if config.TWILIO_ACCOUNT_SID else '❌'}")
    print(f"  - Google Drive: {'✅' if os.path.exists(config.GOOGLE_CREDENTIALS_FILE) else '❌'}")
    print(f"  - OpenAI: {'✅' if config.OPENAI_API_KEY else '❌'}")
    print(f"  - Anthropic: {'✅' if config.ANTHROPIC_API_KEY else '❌'}")
    print(f"  - Rate Limit: {config.RATE_LIMIT_PER_HOUR}/hour")
    print(f"  - Environment: {config.FLASK_ENV}")
    
    return validation['valid']

if __name__ == "__main__":
    validate_config()
