import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, AppBar, Toolbar, Typography, Container, Grid, Paper, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField } from '@mui/material';
import ChatInterface from './components/ChatInterface';
import SystemStatus from './components/SystemStatus';
import PRDViewer from './components/PRDViewer';
import DatabaseViewer from './components/DatabaseViewer';
import axios from 'axios';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

// Use /api prefix for nginx proxy, or fallback to environment variable for development
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

function App() {
  const [currentView, setCurrentView] = useState('chat');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loginDialog, setLoginDialog] = useState(true);
  const [loginData, setLoginData] = useState({ username: '', password: '' });
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      // Verify token
      axios.get(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      }).then(response => {
        setUser(response.data);
        setIsAuthenticated(true);
        setLoginDialog(false);
      }).catch(() => {
        localStorage.removeItem('token');
      });
    }
  }, []);

  const handleLogin = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, loginData);
      localStorage.setItem('token', response.data.access_token);
      setUser({ username: loginData.username });
      setIsAuthenticated(true);
      setLoginDialog(false);
    } catch (error) {
      alert('Login failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
    setLoginDialog(true);
  };

  if (!isAuthenticated) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Dialog open={loginDialog} onClose={() => {}}>
          <DialogTitle>Login to AI Dashboard</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Username"
              fullWidth
              variant="outlined"
              value={loginData.username}
              onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
            />
            <TextField
              margin="dense"
              label="Password"
              type="password"
              fullWidth
              variant="outlined"
              value={loginData.password}
              onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
              onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
            />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Default credentials: admin / admin123
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleLogin} variant="contained">Login</Button>
          </DialogActions>
        </Dialog>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              AI Agent Orchestrator Dashboard
            </Typography>
            <Typography variant="body1" sx={{ mr: 2 }}>
              Welcome, {user?.username}
            </Typography>
            <Button color="inherit" onClick={handleLogout}>Logout</Button>
          </Toolbar>
        </AppBar>
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Grid container spacing={3}>
            {/* Navigation */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2, display: 'flex', gap: 2 }}>
                <button onClick={() => setCurrentView('chat')}>Chat with AI</button>
                <button onClick={() => setCurrentView('prd')}>PRD Viewer</button>
                <button onClick={() => setCurrentView('database')}>Database Access</button>
                <button onClick={() => setCurrentView('status')}>System Status</button>
              </Paper>
            </Grid>

            {/* Main Content */}
            <Grid item xs={12}>
              {currentView === 'chat' && <ChatInterface />}
              {currentView === 'prd' && <PRDViewer />}
              {currentView === 'database' && <DatabaseViewer />}
              {currentView === 'status' && <SystemStatus />}
            </Grid>
          </Grid>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;