import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  IconButton,
  CircularProgress,
  Chip,
  Button,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Warning as WarningIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import axios from 'axios';
import { API_BASE_URL } from './config.js';

const HumanEscalationPage = ({ onBack }) => {
  const [escalations, setEscalations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchEscalations();
  }, []);

  const fetchEscalations = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/human-escalations`);
      setEscalations(response.data.escalations || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching escalations:', err);
      setError('Failed to load human escalations');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
      py: 4 
    }}>
      <Container maxWidth="xl">
        {/* Header */}
        <Box sx={{ position: 'relative', mb: 4 }}>
          <IconButton
            onClick={onBack}
            sx={{
              position: 'absolute',
              left: 0,
              top: '50%',
              transform: 'translateY(-50%)',
              bgcolor: 'rgba(255,255,255,0.2)',
              color: 'white',
              '&:hover': {
                bgcolor: 'rgba(255,255,255,0.3)',
              }
            }}
          >
            <ArrowBackIcon />
          </IconButton>

          <Typography
            variant="h3"
            align="center"
            sx={{
              fontWeight: 700,
              color: 'white',
              textShadow: '0 2px 4px rgba(0,0,0,0.2)',
            }}
          >
            ⚠️ Human Escalations
          </Typography>
        </Box>

        {/* Content */}
        <Card
          elevation={8}
          sx={{
            borderRadius: 4,
            background: 'rgba(255,255,255,0.95)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <CardContent sx={{ p: 4 }}>
            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
                <CircularProgress size={60} />
              </Box>
            ) : error ? (
              <Box sx={{ textAlign: 'center', py: 8 }}>
                <Typography variant="h6" color="error" gutterBottom>
                  {error}
                </Typography>
                <Button variant="contained" onClick={fetchEscalations} sx={{ mt: 2 }}>
                  Retry
                </Button>
              </Box>
            ) : escalations.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 8 }}>
                <WarningIcon sx={{ fontSize: 80, color: '#ff9800', mb: 2 }} />
                <Typography variant="h5" gutterBottom>
                  No Escalations
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Cases requiring human review will appear here
                </Typography>
              </Box>
            ) : (
              <>
                <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="h5" sx={{ fontWeight: 600, color: '#f5576c' }}>
                    Total Escalations: {escalations.length}
                  </Typography>
                  <Button
                    variant="outlined"
                    onClick={fetchEscalations}
                    sx={{ borderColor: '#f5576c', color: '#f5576c' }}
                  >
                    Refresh
                  </Button>
                </Box>

                <Grid container spacing={3}>
                  {escalations.map((loanId, index) => (
                    <Grid item xs={12} sm={6} md={4} key={index}>
                      <Card
                        elevation={2}
                        sx={{
                          borderRadius: 3,
                          border: '2px solid #ff9800',
                          background: 'linear-gradient(135deg, rgba(255, 152, 0, 0.05) 0%, rgba(255, 255, 255, 0.95) 100%)',
                          transition: 'all 0.3s ease',
                          '&:hover': {
                            transform: 'translateY(-4px)',
                            boxShadow: '0 12px 24px rgba(255, 152, 0, 0.2)',
                          }
                        }}
                      >
                        <CardContent sx={{ p: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                            <PersonIcon sx={{ fontSize: 40, color: '#ff9800', mr: 2 }} />
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="caption" color="text.secondary">
                                Loan ID
                              </Typography>
                              <Typography variant="h6" sx={{ fontWeight: 600, color: '#e65100' }}>
                                {loanId}
                              </Typography>
                            </Box>
                          </Box>
                          
                          <Chip
                            icon={<WarningIcon />}
                            label="NEEDS REVIEW"
                            color="warning"
                            sx={{
                              width: '100%',
                              fontWeight: 600,
                              fontSize: '0.9rem',
                            }}
                          />
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
              </>
            )}
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
};

export default HumanEscalationPage;
