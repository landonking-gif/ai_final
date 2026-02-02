import React, { useState, useEffect } from 'react';
import { Box, Paper, Typography, Button, TextField, Dialog, DialogTitle, DialogContent, DialogActions, List, ListItem, ListItemText, Divider } from '@mui/material';
import axios from 'axios';

// Use /api prefix for nginx proxy, or fallback to environment variable for development
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

function PRDViewer() {
  const [prds, setPrds] = useState([]);
  const [selectedPrd, setSelectedPrd] = useState(null);
  const [open, setOpen] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    loadPRDs();
  }, []);

  const loadPRDs = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/prds`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      setPrds(response.data.prds);
    } catch (error) {
      console.error('Error loading PRDs:', error);
    }
  };

  const generatePRD = async () => {
    setGenerating(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/generate-prd`, {
        requirements: "User requirements gathered from chat discussion"      }, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }      });
      await loadPRDs();
      setSelectedPrd(response.data);
      setOpen(true);
    } catch (error) {
      console.error('Error generating PRD:', error);
    } finally {
      setGenerating(false);
    }
  };

  const validatePRD = async (prdId) => {
    try {
      await axios.post(`${API_BASE_URL}/prds/${prdId}/validate`, {}, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      await loadPRDs();
    } catch (error) {
      console.error('Error validating PRD:', error);
    }
  };

  const approvePRD = async (prdId) => {
    try {
      await axios.post(`${API_BASE_URL}/prds/${prdId}/approve`, {}, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      // This would trigger the agent deployment workflow
      alert('PRD approved! Agent deployment workflow will start.');
    } catch (error) {
      console.error('Error approving PRD:', error);
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Product Requirements Documents (PRDs)
      </Typography>

      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          onClick={generatePRD}
          disabled={generating}
        >
          {generating ? 'Generating PRD...' : 'Generate New PRD'}
        </Button>
      </Box>

      <List>
        {prds.map((prd) => (
          <React.Fragment key={prd.id}>
            <ListItem
              button
              onClick={() => {
                setSelectedPrd(prd);
                setOpen(true);
              }}
            >
              <ListItemText
                primary={prd.title}
                secondary={`Status: ${prd.status} | Created: ${new Date(prd.created_at).toLocaleDateString()}`}
              />
              <Box sx={{ display: 'flex', gap: 1 }}>
                {prd.status === 'draft' && (
                  <Button size="small" onClick={(e) => { e.stopPropagation(); validatePRD(prd.id); }}>
                    Validate
                  </Button>
                )}
                {prd.status === 'validated' && (
                  <Button size="small" color="success" onClick={(e) => { e.stopPropagation(); approvePRD(prd.id); }}>
                    Approve & Deploy
                  </Button>
                )}
              </Box>
            </ListItem>
            <Divider />
          </React.Fragment>
        ))}
      </List>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{selectedPrd?.title}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={20}
            value={selectedPrd?.content || ''}
            InputProps={{ readOnly: true }}
            variant="outlined"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}

export default PRDViewer;