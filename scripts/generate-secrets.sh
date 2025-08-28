#!/bin/bash

# PolarVortex Secret Generator
# This script generates secure secrets for production deployment

echo "🔐 PolarVortex Secret Generator"
echo "================================"

# Generate a secure secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

echo "Generated SECRET_KEY: $SECRET_KEY"
echo ""

# Create production environment file
if [ ! -f .env.production ]; then
    echo "Creating .env.production file..."
    cp env.production.example .env.production
    
    # Replace the placeholder secret key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-super-secret-production-key-change-this-immediately/$SECRET_KEY/g" .env.production
    else
        # Linux
        sed -i "s/your-super-secret-production-key-change-this-immediately/$SECRET_KEY/g" .env.production
    fi
    
    echo "✅ .env.production created with secure SECRET_KEY"
else
    echo "⚠️  .env.production already exists. Please update SECRET_KEY manually:"
    echo "   SECRET_KEY=$SECRET_KEY"
fi

echo ""
echo "🔒 Security Recommendations:"
echo "1. Keep your .env.production file secure and never commit it to version control"
echo "2. Use different SECRET_KEY values for each environment"
echo "3. Regularly rotate your SECRET_KEY"
echo "4. Set appropriate file permissions: chmod 600 .env.production"
echo ""
echo "📝 Next steps:"
echo "1. Review and customize .env.production settings"
echo "2. Update CORS_ORIGINS with your domain"
echo "3. Configure ARDUINO_DEVICE path"
echo "4. Set appropriate LOG_LEVEL for production"
