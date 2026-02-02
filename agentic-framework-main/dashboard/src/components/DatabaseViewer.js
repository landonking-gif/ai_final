import React, { useState, useEffect } from 'react';
import { Box, Paper, Typography, Tabs, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';

// Use /api prefix for nginx proxy, or fallback to environment variable for development
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

function DatabaseViewer() {
  const [tabValue, setTabValue] = useState(0);
  const [tasks, setTasks] = useState([]);
  const [agents, setAgents] = useState([]);
  const [memory, setMemory] = useState([]);
  const [artifacts, setArtifacts] = useState([]);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tabValue]);

  const loadData = async () => {
    try {
      const headers = { Authorization: `Bearer ${localStorage.getItem('token')}` };

      switch (tabValue) {
        case 0: // Tasks
          const tasksResponse = await axios.get(`${API_BASE_URL}/tasks`, { headers });
          setTasks(tasksResponse.data);
          break;
        case 1: // Agents
          const agentsResponse = await axios.get(`${API_BASE_URL}/agents`, { headers });
          setAgents(agentsResponse.data);
          break;
        case 2: // Memory
          const memoryResponse = await axios.get(`http://localhost:8002/memories`, { headers });
          setMemory(memoryResponse.data);
          break;
        case 3: // Artifacts
          const artifactsResponse = await axios.get(`${API_BASE_URL}/artifacts`, { headers });
          setArtifacts(artifactsResponse.data);
          break;
        default:
          break;
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Database Access & System Information
      </Typography>

      <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
        <Tab label="Tasks" />
        <Tab label="Agents" />
        <Tab label="Memory" />
        <Tab label="Artifacts" />
      </Tabs>

      {tabValue === 0 && (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Agent</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell>{task.id}</TableCell>
                  <TableCell>{task.status}</TableCell>
                  <TableCell>{new Date(task.created_at).toLocaleString()}</TableCell>
                  <TableCell>{task.agent_id}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {tabValue === 1 && (
        <Box>
          {agents.map((agent) => (
            <Accordion key={agent.id}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>{agent.name} - {agent.role}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography><strong>Skills:</strong> {agent.skills?.join(', ')}</Typography>
                <Typography><strong>Status:</strong> {agent.status}</Typography>
                <Typography><strong>Created:</strong> {new Date(agent.created_at).toLocaleString()}</Typography>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      )}

      {tabValue === 2 && (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Content Preview</TableCell>
                <TableCell>Created</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {memory.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.id}</TableCell>
                  <TableCell>{item.type}</TableCell>
                  <TableCell>{item.content?.substring(0, 50)}...</TableCell>
                  <TableCell>{new Date(item.created_at).toLocaleString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {tabValue === 3 && (
        <Box>
          {artifacts.map((artifact) => (
            <Accordion key={artifact.id}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>{artifact.name} - {artifact.type}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography><strong>Task ID:</strong> {artifact.task_id}</Typography>
                <Typography><strong>Size:</strong> {artifact.size} bytes</Typography>
                <Typography><strong>Created:</strong> {new Date(artifact.created_at).toLocaleString()}</Typography>
                <Typography><strong>Content:</strong></Typography>
                <Box sx={{ mt: 1, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {typeof artifact.content === 'string' ? artifact.content : JSON.stringify(artifact.content, null, 2)}
                  </Typography>
                </Box>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      )}
    </Paper>
  );
}

export default DatabaseViewer;