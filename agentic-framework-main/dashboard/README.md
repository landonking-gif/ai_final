# AI Agent Orchestrator Dashboard

A React-based web dashboard for interacting with the Agentic Framework's AI orchestrator, enabling requirement gathering, PRD generation, system monitoring, and database access.

## Features

- **Chat Interface**: Discuss project requirements with the AI orchestrator in real-time
- **PRD Generation**: Automatically create and validate Product Requirements Documents
- **System Monitoring**: View the health status of all framework services
- **Database Access**: Browse tasks, agents, memory, and artifacts
- **Agent Deployment**: Trigger multi-agent workflows after PRD approval

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API endpoints
```

3. Start the development server:
```bash
npm start
```

The dashboard will be available at `http://localhost:3000`

## Environment Variables

- `REACT_APP_API_BASE_URL`: Base URL for the orchestrator API (default: http://localhost:8000)

## Usage

1. **Requirement Gathering**: Use the chat interface to discuss project requirements with the AI
2. **PRD Generation**: The AI will create a comprehensive PRD based on the discussion
3. **Validation**: Review and validate the PRD with the AI's assistance
4. **Approval**: Once satisfied, approve the PRD to trigger agent deployment
5. **Monitoring**: Use the system status and database viewer to track progress

## Architecture

- **Frontend**: React with Material-UI for the user interface
- **Real-time Communication**: Socket.io for live chat updates
- **API Integration**: Axios for REST API calls to the framework services
- **State Management**: React hooks for local state management

## Development

### Available Scripts

- `npm start`: Start development server
- `npm build`: Build for production
- `npm test`: Run tests
- `npm eject`: Eject from Create React App

### Project Structure

```
src/
├── components/
│   ├── ChatInterface.js      # Main chat component
│   ├── SystemStatus.js       # Service health monitoring
│   ├── PRDViewer.js          # PRD management
│   └── DatabaseViewer.js     # Database access
├── App.js                    # Main application component
└── index.js                  # Application entry point
```

## Troubleshooting

- **Connection Issues**: Ensure the Agentic Framework is running and accessible
- **WebSocket Errors**: Check firewall settings for WebSocket connections
- **API Errors**: Verify API_BASE_URL environment variable is correct

## Deployment

### Local Development
```bash
npm start
```
The dashboard will be available at `http://localhost:3000`

### Production Build
```bash
./build-dashboard.sh
```

### Deploying to AWS (alongside the framework)

1. **Build the dashboard**:
   ```bash
   cd dashboard
   ./build-dashboard.sh
   ```

2. **Copy to your AWS instance** (after deploying the framework):
   ```bash
   # From your local machine
   scp -i your-key.pem -r dashboard/build ubuntu@your-aws-ip:/opt/agentic-framework/dashboard
   ```

3. **Serve the dashboard on AWS**:
   ```bash
   # SSH to your AWS instance
   ssh -i your-key.pem ubuntu@your-aws-ip

   # Install a simple HTTP server
   sudo apt update
   sudo apt install -y nginx

   # Configure nginx to serve the dashboard
   sudo tee /etc/nginx/sites-available/dashboard << EOF
   server {
       listen 80;
       server_name your-domain-or-ip;
       root /opt/agentic-framework/dashboard;
       index index.html;

       location / {
           try_files \$uri \$uri/ /index.html;
       }

       # Proxy API requests to the orchestrator
       location /api/ {
           proxy_pass http://localhost:8000/;
           proxy_set_header Host \$host;
           proxy_set_header X-Real-IP \$remote_addr;
       }
   }
   EOF

   sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. **Access the dashboard**:
   - Dashboard: `http://your-aws-ip`
   - API: `http://your-aws-ip:8000`

### Environment Configuration

Create a `.env` file in the dashboard root:
```bash
REACT_APP_API_BASE_URL=http://your-aws-ip:8000
```

For production, update this to match your deployment URL.

## Contributing

1. Follow React best practices
2. Use Material-UI components for consistency
3. Add proper error handling
4. Test with the deployed framework services