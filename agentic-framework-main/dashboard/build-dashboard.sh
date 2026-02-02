#!/bin/bash

# Dashboard Deployment Script
# Builds and serves the React dashboard

set -e

echo "🚀 Building AI Dashboard..."

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build the application
echo "🔨 Building production version..."
npm run build

#!/bin/bash

# Dashboard Deployment Script
# Builds and serves the React dashboard

set -e

echo "🚀 Building AI Dashboard..."

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build the application
echo "🔨 Building production version..."
npm run build

echo "✅ Dashboard built successfully!"
echo ""
echo "🌐 To serve the dashboard locally:"
echo "  npx serve -s build -l 3000"
echo ""
echo "📤 To deploy to production:"
echo "  - Copy the 'build' folder to your web server"
echo "  - Configure your web server to serve the static files"
echo "  - Set the REACT_APP_API_BASE_URL environment variable to your orchestrator URL"
echo ""
echo "🔧 Make sure your orchestrator service is running and accessible!"
echo ""
echo "☁️  AWS Deployment Example:"
echo "  scp -i your-key.pem -r build ubuntu@your-aws-ip:/opt/agentic-framework/dashboard"
echo "  # Then configure nginx on your AWS instance to serve the files"