import React, { useState, useEffect } from 'react';
import { Box, Paper, Typography, Grid, Card, CardContent, Chip } from '@mui/material';
import axios from 'axios';

// Use /api prefix for nginx proxy, or fallback to environment variable for development
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

function SystemStatus() {
  const [status, setStatus] = useState({
    orchestrator: 'unknown',
    memory: 'unknown',
    subagent: 'unknown',
    mcp: 'unknown',
    minio: 'unknown',
    ollama: 'unknown'
  });

  useEffect(() => {
    const checkStatus = async () => {
      // All status checks go through the orchestrator's aggregated health endpoint
      // or use relative paths that work via nginx proxy
      const newStatus = {
        orchestrator: 'unknown',
        memory: 'unknown',
        subagent: 'unknown',
        mcp: 'unknown',
        minio: 'unknown',
        ollama: 'unknown'
      };

      try {
        // Get aggregated health from orchestrator (includes all service statuses)
        const response = await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 });
        if (response.status === 200 && response.data) {
          newStatus.orchestrator = response.data.status === 'healthy' ? 'healthy' : 'unhealthy';
          // Parse dependencies if available
          if (response.data.dependencies) {
            newStatus.memory = response.data.dependencies.memory_service === 'healthy' ? 'healthy' : 'unhealthy';
            newStatus.subagent = response.data.dependencies.subagent_manager === 'healthy' ? 'healthy' : 'unhealthy';
            newStatus.mcp = response.data.dependencies.mcp_gateway === 'healthy' ? 'healthy' : 'unhealthy';
          }
        }
      } catch (error) {
        newStatus.orchestrator = 'unhealthy';
      }

      // MinIO and Ollama status would need to be added to orchestrator health check
      // For now, mark as unknown if not available from orchestrator
      if (!newStatus.minio) newStatus.minio = 'unknown';
      if (!newStatus.ollama) newStatus.ollama = 'unknown';

      setStatus(newStatus);
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000); // Check every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'unhealthy': return 'error';
      default: return 'warning';
    }
  };

  const services = [
    { name: 'Orchestrator', key: 'orchestrator', port: 8000 },
    { name: 'Memory Service', key: 'memory', port: 8002 },
    { name: 'Subagent Manager', key: 'subagent', port: 8003 },
    { name: 'MCP Gateway', key: 'mcp', port: 8080 },
    { name: 'MinIO', key: 'minio', port: 9000 },
    { name: 'Ollama', key: 'ollama', port: 11434 }
  ];

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        System Status
      </Typography>

      <Grid container spacing={2}>
        {services.map((service) => (
          <Grid item xs={12} sm={6} md={4} key={service.key}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="div">
                  {service.name}
                </Typography>
                <Typography color="text.secondary" gutterBottom>
                  Port: {service.port}
                </Typography>
                <Chip
                  label={status[service.key]}
                  color={getStatusColor(status[service.key])}
                  size="small"
                />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          System Information
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Last updated: {new Date().toLocaleString()}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          API Base URL: {API_BASE_URL}
        </Typography>
      </Box>
    </Paper>
  );
}

export default SystemStatus;