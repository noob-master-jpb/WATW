#!/bin/bash
# WATW Quick Setup Script

set -e

echo "🚀 WATW - WhatsApp File Manager Setup"
echo "======================================"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root"
   exit 1
fi

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create environment file
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    cp .env.example .env
    echo "✅ Created .env file - Please edit it with your credentials"
else
    echo "⚠️  .env file already exists"
fi

# Create required directories
echo "📁 Creating required directories..."
mkdir -p logs audit nginx/ssl

# Set permissions
chmod 755 logs audit
chmod 600 .env

echo "✅ Directory structure created"

# Generate basic auth file for nginx (if doesn't exist)
if [ ! -f nginx/.htpasswd ]; then
    echo "🔐 Setting up basic authentication..."
    
    read -p "Enter admin username (default: admin): " admin_user
    admin_user=${admin_user:-admin}
    
    read -s -p "Enter admin password: " admin_pass
    echo
    
    # Create htpasswd file
    echo "$admin_pass" | htpasswd -c -i nginx/.htpasswd "$admin_user"
    
    echo "✅ Basic authentication configured"
else
    echo "⚠️  Basic auth file already exists"
fi

# Check for credentials
echo "🔍 Checking for Google Drive credentials..."
if [ ! -f credentials.json ]; then
    echo "⚠️  Google Drive credentials not found"
    echo "   Please download credentials.json from Google Cloud Console"
    echo "   and place it in the project root directory"
fi

# SSL Certificate check
echo "🔍 Checking for SSL certificates..."
if [ ! -f nginx/ssl/cert.pem ] || [ ! -f nginx/ssl/key.pem ]; then
    echo "⚠️  SSL certificates not found in nginx/ssl/"
    echo "   For production, please add:"
    echo "   - nginx/ssl/cert.pem"
    echo "   - nginx/ssl/key.pem"
    echo ""
    echo "   For testing, you can generate self-signed certificates:"
    echo "   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\"
    echo "     -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem"
fi

# Configuration validation
echo "🔧 Validating configuration..."
python3 config.py

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env file with your API keys and credentials"
echo "2. Add Google Drive credentials.json to project root"
echo "3. Configure SSL certificates in nginx/ssl/"
echo "4. Run: docker-compose up -d"
echo ""
echo "📖 For detailed instructions, see DEPLOYMENT_GUIDE.md"
echo ""
echo "🔗 Useful commands:"
echo "   docker-compose up -d          # Start services"
echo "   docker-compose logs -f        # View logs"
echo "   docker-compose down           # Stop services"
echo "   python config.py              # Validate configuration"
echo "   python message_simulator.py   # Test message handling"
