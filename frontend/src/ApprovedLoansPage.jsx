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
  CheckCircle as CheckCircleIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import axios from 'axios';
import { API_BASE_URL } from './config.js';

const ApprovedLoansPage = ({ onBack }) => {
  const [approvedLoans, setApprovedLoans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchApprovedLoans();
  }, []);

  const fetchApprovedLoans = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/approved-loans`);
      setApprovedLoans(response.data.approved_loans || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching approved loans:', err);
      setError('Failed to load approved loans');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
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
            ✅ Approved Loans
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
                <Button variant="contained" onClick={fetchApprovedLoans} sx={{ mt: 2 }}>
                  Retry
                </Button>
              </Box>
            ) : approvedLoans.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 8 }}>
                <CheckCircleIcon sx={{ fontSize: 80, color: '#4caf50', mb: 2 }} />
                <Typography variant="h5" gutterBottom>
                  No Approved Loans Yet
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Approved loan applications will appear here
                </Typography>
              </Box>
            ) : (
              <>
                <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="h5" sx={{ fontWeight: 600, color: '#667eea' }}>
                    Total Approved: {approvedLoans.length}
                  </Typography>
                  <Button
                    variant="outlined"
                    onClick={fetchApprovedLoans}
                    sx={{ borderColor: '#667eea', color: '#667eea' }}
                  >
                    Refresh
                  </Button>
                </Box>

                <Grid container spacing={3}>
                  {approvedLoans.map((loanId, index) => (
                    <Grid item xs={12} sm={6} md={4} key={index}>
                      <Card
                        elevation={2}
                        sx={{
                          borderRadius: 3,
                          border: '2px solid #4caf50',
                          background: 'linear-gradient(135deg, rgba(76, 175, 80, 0.05) 0%, rgba(255, 255, 255, 0.95) 100%)',
                          transition: 'all 0.3s ease',
                          '&:hover': {
                            transform: 'translateY(-4px)',
                            boxShadow: '0 12px 24px rgba(76, 175, 80, 0.2)',
                          }
                        }}
                      >
                        <CardContent sx={{ p: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                            <PersonIcon sx={{ fontSize: 40, color: '#4caf50', mr: 2 }} />
                            <Box sx={{ flex: 1 }}>
                              <Typography variant="caption" color="text.secondary">
                                Loan ID
                              </Typography>
                              <Typography variant="h6" sx={{ fontWeight: 600, color: '#2e7d32' }}>
                                {loanId}
                              </Typography>
                            </Box>
                          </Box>
                          
                          <Chip
                            icon={<CheckCircleIcon />}
                            label="APPROVED"
                            color="success"
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

export default ApprovedLoansPage;
