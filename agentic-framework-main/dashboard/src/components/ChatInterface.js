import React, { useState, useEffect, useRef } from 'react';
import { Box, Paper, TextField, Button, Typography, List, ListItem, ListItemText, Divider } from '@mui/material';
import axios from 'axios';
import io from 'socket.io-client';

// Use /api prefix for nginx proxy, or fallback to environment variable for development
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

// For Socket.IO, we need the full URL. In production, use the same host on port 8000
const getSocketURL = () => {
  if (process.env.REACT_APP_WS_URL) {
    return process.env.REACT_APP_WS_URL;
  }
  // In production, connect to the orchestrator on port 8000
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
    return `http://${window.location.hostname}:8000`;
  }
  return 'http://localhost:8000';
};

function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Connect to WebSocket for real-time updates
    const socketURL = getSocketURL();
    socketRef.current = io(socketURL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

    socketRef.current.on('connect', () => {
      setIsConnected(true);
    });

    socketRef.current.on('disconnect', () => {
      setIsConnected(false);
    });

    socketRef.current.on('message', (message) => {
      setMessages(prev => [...prev, { text: message, sender: 'ai', timestamp: new Date() }]);
    });

    return () => {
      socketRef.current.disconnect();
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { text: input, sender: 'user', timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: input,
        context: messages.slice(-10) // Send last 10 messages for context
      }, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });

      const aiMessage = { text: response.data.response, sender: 'ai', timestamp: new Date() };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = { text: 'Error: Could not send message. Please check authentication.', sender: 'system', timestamp: new Date() };
      setMessages(prev => [...prev, errorMessage]);
    }

    setInput('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Paper sx={{ p: 2, height: '70vh', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" gutterBottom>
        Chat with AI Orchestrator
        {isConnected ? ' (Connected)' : ' (Disconnected)'}
      </Typography>

      <Box sx={{ flexGrow: 1, overflow: 'auto', mb: 2 }}>
        <List>
          {messages.map((message, index) => (
            <ListItem key={index} sx={{ alignItems: 'flex-start' }}>
              <ListItemText
                primary={
                  <Typography variant="subtitle2" color={message.sender === 'user' ? 'primary' : 'secondary'}>
                    {message.sender === 'user' ? 'You' : message.sender === 'ai' ? 'AI Orchestrator' : 'System'}
                  </Typography>
                }
                secondary={
                  <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                    {message.text}
                  </Typography>
                }
              />
            </ListItem>
          ))}
          <div ref={messagesEndRef} />
        </List>
      </Box>

      <Divider sx={{ mb: 2 }} />

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          multiline
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Discuss project requirements with the AI..."
          variant="outlined"
        />
        <Button variant="contained" onClick={sendMessage} disabled={!input.trim()}>
          Send
        </Button>
      </Box>
    </Paper>
  );
}

export default ChatInterface;