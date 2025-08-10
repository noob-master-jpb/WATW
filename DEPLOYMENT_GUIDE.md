# WATW - WhatsApp Google Drive Assistant

## Complete Deployment Guide

### 📋 Prerequisites

1. **Domain & SSL Certificate**
   - Registered domain name
   - SSL certificate (Let's Encrypt recommended)

2. **API Keys & Accounts**
   - Twilio account with WhatsApp sandbox
   - Google Cloud Project with Drive API enabled
   - OpenAI or Anthropic API key (optional)

3. **Server Requirements**
   - Linux server with Docker and Docker Compose
   - At least 2GB RAM, 2 CPU cores
   - 20GB storage space

### 🚀 Quick Deployment

#### 1. Clone and Setup
```bash
git clone <your-repo>
cd WATW

# Copy environment template
cp .env.example .env

# Edit with your configuration
nano .env
```

#### 2. Google Drive Setup
```bash
# 1. Go to Google Cloud Console
# 2. Enable Google Drive API
# 3. Create OAuth2 credentials
# 4. Download credentials.json to project root

# Set up Google OAuth
python3 google_drive_handler.py
# Follow the authentication flow
```

#### 3. Twilio WhatsApp Setup
```bash
# 1. Go to Twilio Console
# 2. Navigate to Messaging > Try it out > Send a WhatsApp message
# 3. Set webhook URL: https://your-domain.com/webhook/whatsapp
# 4. Set HTTP method: POST
```

#### 4. Deploy with Docker
```bash
# Build and start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f watw-app
```

#### 5. Import n8n Workflow
```bash
# Access n8n at https://n8n.your-domain.com
# Login with credentials
# Import workflow.json from n8n/ folder
# Configure credentials:
#   - Twilio API
#   - Google Drive OAuth2
#   - OpenAI API
#   - Google Sheets (optional)
```

### 📱 Testing

#### Test Commands via WhatsApp
```
# Send to your Twilio WhatsApp number:

HELP                          # Show available commands
LIST /                        # List root folder
LIST /ProjectX               # List specific folder
SUMMARY /ProjectX            # AI summary of folder
DELETE /ProjectX/old.pdf     # Delete file (with confirmation)
MOVE /source.pdf TO /Archive # Move file
```

### 🔧 Configuration Details

#### Environment Variables
```bash
# Required
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

# Optional (AI features)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# n8n specific
N8N_DB_PASSWORD=...
N8N_ENCRYPTION_KEY=...
N8N_WEBHOOK_URL=https://n8n.your-domain.com
```

#### SSL Certificate Setup (Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d your-domain.com -d n8n.your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
```

### 🛠️ Maintenance

#### Viewing Logs
```bash
# Application logs
docker-compose logs -f watw-app

# n8n logs
docker-compose logs -f n8n

# Database logs
docker-compose logs -f postgres
```

#### Backup
```bash
# Backup database
docker-compose exec postgres pg_dump -U n8n n8n > backup.sql

# Backup audit logs
cp logs/* backup/
cp audit/* backup/
```

#### Updates
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose up --build -d
```

### 📊 Monitoring

#### Health Checks
- Application: `https://your-domain.com/health`
- n8n: `https://n8n.your-domain.com/healthz`

#### Audit Logs
- CSV: `audit/watw_audit.csv`
- JSON: `audit/watw_audit.json`
- System: `logs/watw_system.log`

### 🔒 Security Features

#### Built-in Safety
- **Confirmation required** for DELETE operations
- **Rate limiting** (30 commands/hour per user)
- **Audit logging** of all operations
- **Files moved to trash** (not permanently deleted)
- **OAuth2 authentication** for Google Drive

#### Access Control
- **Admin endpoints** protected with basic auth
- **n8n interface** protected with basic auth
- **HTTPS only** with HSTS headers

### 🆘 Troubleshooting

#### Common Issues

**1. WhatsApp messages not received**
```bash
# Check webhook URL in Twilio console
# Verify SSL certificate is valid
# Check application logs for errors
docker-compose logs watw-app | grep ERROR
```

**2. Google Drive authentication fails**
```bash
# Ensure credentials.json is present
# Re-run authentication flow
docker-compose exec watw-app python google_drive_handler.py
```

**3. AI summarization not working**
```bash
# Check API keys are set
# Verify service availability
docker-compose exec watw-app python ai_summarizer.py
```

**4. n8n workflow fails**
```bash
# Check n8n credentials configuration
# Verify all required environment variables
# Test workflow execution manually
```

### 📈 Scaling

#### High Availability
- Use multiple app instances behind load balancer
- Set up PostgreSQL cluster
- Implement Redis Sentinel for failover

#### Performance Optimization
- Enable Redis caching
- Configure CDN for static assets  
- Use PostgreSQL connection pooling

### 🔧 Development

#### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python watw_main.py

# Test components
python command_parser.py
python google_drive_handler.py
python ai_summarizer.py
python audit_logger.py
```

#### Testing
```bash
# Run message simulator
python message_simulator.py

# Test webhook locally with ngrok
ngrok http 5000
# Set Twilio webhook to ngrok URL
```

### 📞 Support

For issues and feature requests, check:
- Application logs: `/logs/`
- Audit logs: `/audit/`
- Health endpoint: `/health`
- User statistics: `/stats/+1234567890`
