import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  Select,
  MenuItem,
  Button,
  CircularProgress,
  Alert,
  Paper,
  Tabs,
  Tab,
  Card,
  CardContent,
  Grid,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider,
  IconButton,
  LinearProgress,
  Avatar,
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import { 
  PlayArrow, 
  CheckCircle, 
  Error, 
  Warning, 
  Home as HomeIcon,
  Email as EmailIcon,
  Sms as SmsIcon,
  SupervisorAccount as EscalateIcon,
  ThumbUp as ApproveIcon,
  Description as DocumentIcon,
  AccountBalance as BankIcon,
  Receipt as ReceiptIcon,
  Work as WorkIcon,
  Person as PersonIcon,
  CreditCard as CreditCardIcon,
  AccountBalanceWallet as WalletIcon,
  Assignment as AssignmentIcon,
  ExpandMore as ExpandMoreIcon,
  Download as DownloadIcon,
  Visibility as VisibilityIcon
} from '@mui/icons-material';
import HomePage from './HomePage';
import ApprovedLoansPage from './ApprovedLoansPage';
import HumanEscalationPage from './HumanEscalationPage';
import { API_BASE_URL } from './config.js';

function App() {
  const [customers, setCustomers] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [currentView, setCurrentView] = useState('home'); // 'home', 'app', 'escalations', 'approved'


  // Fetch customers on mount
  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/customers`);
      const data = await response.json();
      setCustomers(data.customers);
    } catch (err) {
      setError('Failed to load customers');
      console.error(err);
    }
  };

  const handleRunWorkflow = async () => {
    if (!selectedCustomer) {
      setError('Please select a customer');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch(`${API_BASE_URL}/run_workflow`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ customer_id: selectedCustomer }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Workflow failed');
      }

      const data = await response.json();
      setResults(data);
      setActiveTab(0);
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Action button handlers
  const handleSendEmail = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/send_email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id: selectedCustomer }),
      });
      const data = await response.json();
      alert(`📧 ${data.message}`);
    } catch (err) {
      alert(`❌ Failed to send email: ${err.message}`);
    }
  };

  const handleSendSMS = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/send_sms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id: selectedCustomer }),
      });
      const data = await response.json();
      alert(`📱 ${data.message}`);
    } catch (err) {
      alert(`❌ Failed to send SMS: ${err.message}`);
    }
  };

  const handleEscalate = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/escalate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id: selectedCustomer }),
      });
      const data = await response.json();
      alert(`⚠️ ${data.message}`);
    } catch (err) {
      alert(`❌ Failed to escalate: ${err.message}`);
    }
  };

  const handleApproveLoan = async () => {
    const decisionAgent = results?.results?.descision_making_agent || {};
    const status = decisionAgent.suggested_status || '';
    const risk = decisionAgent.risk || '';
    
    // Check if AI recommends rejection or high risk
    if (status === 'REJECTED' || risk === 'High') {
      if (!window.confirm('⚠️ Warning: The AI decision recommends REJECTION or HIGH RISK. Are you sure you want to approve this loan?')) {
        return; // User cancelled
      }
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/approve_loan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id: selectedCustomer }),
      });
      const data = await response.json();
      alert(`✅ ${data.message}`);
    } catch (err) {
      alert(`❌ Failed to approve loan: ${err.message}`);
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'success':
        return 'success';
      case 'failed':
      case 'error':
        return 'error';
      case 'partial_success':
        return 'warning';
      default:
        return 'info';
    }
  };

  const getRiskColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  const renderProfileTab = () => {
    const profile = results?.results?.Profile || {};
    
    // Extract key information for summary cards
    const applicantName = profile.payslip?.['Employee Name'] || profile.offer?.['Employee Name'] || profile.bank?.['Account Holder Name'] || profile.form16?.['Employee Name'] || 'N/A';
    const panNumber = profile.payslip?.['PAN'] || profile.form16?.['PAN'] || 'N/A';
    const employer = profile.payslip?.['Employer'] || profile.offer?.['Employer'] || 'N/A';
    const designation = profile.offer?.['Designation'] || 'N/A';
    const netSalary = profile.payslip?.['Net Salary'] || 'N/A';
    const bankName = profile.bank?.['Bank Name'] || 'N/A';
   
    
    return (
      <Box sx={{ p: 4, background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%)' }}>
        {/* Summary Cards */}
        <Grid container spacing={2} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={4}>
            <Card variant="outlined" sx={{ borderLeft: '4px solid #757575', p: 1.5, borderRadius: 2, transition: 'all 0.3s ease', '&:hover': { boxShadow: '0 8px 24px rgba(117, 117, 117, 0.2)', transform: 'translateY(-4px)' } }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar sx={{ bgcolor: 'rgba(117, 117, 117, 0.1)', mr: 1.5, width: 40, height: 40 }}>
                  <PersonIcon sx={{ color: '#757575', fontSize: 20 }} />
                </Avatar>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>Applicant Name</Typography>
                  <Typography variant="body2" fontWeight="bold" noWrap>{applicantName}</Typography>
                </Box>
              </Box>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={4}>
            <Card variant="outlined" sx={{ borderLeft: '4px solid #757575', p: 1.5, borderRadius: 2, transition: 'all 0.3s ease', '&:hover': { boxShadow: '0 8px 24px rgba(117, 117, 117, 0.2)', transform: 'translateY(-4px)' } }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar sx={{ bgcolor: 'rgba(117, 117, 117, 0.1)', mr: 1.5, width: 40, height: 40 }}>
                  <CreditCardIcon sx={{ color: '#757575', fontSize: 20 }} />
                </Avatar>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>PAN Number</Typography>
                  <Typography variant="body2" fontWeight="bold">{panNumber}</Typography>
                </Box>
              </Box>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={4}>
            <Card variant="outlined" sx={{ borderLeft: '4px solid #757575', p: 1.5, borderRadius: 2, transition: 'all 0.3s ease', '&:hover': { boxShadow: '0 8px 24px rgba(117, 117, 117, 0.2)', transform: 'translateY(-4px)' } }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar sx={{ bgcolor: 'rgba(117, 117, 117, 0.1)', mr: 1.5, width: 40, height: 40 }}>
                  <WorkIcon sx={{ color: '#757575', fontSize: 20 }} />
                </Avatar>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>Employer</Typography>
                  <Typography variant="body2" fontWeight="bold" noWrap>{employer}</Typography>
                </Box>
              </Box>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={4}>
            <Card variant="outlined" sx={{ borderLeft: '4px solid #757575', p: 1.5, borderRadius: 2, transition: 'all 0.3s ease', '&:hover': { boxShadow: '0 8px 24px rgba(117, 117, 117, 0.2)', transform: 'translateY(-4px)' } }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar sx={{ bgcolor: 'rgba(117, 117, 117, 0.1)', mr: 1.5, width: 40, height: 40 }}>
                  <AssignmentIcon sx={{ color: '#757575', fontSize: 20 }} />
                </Avatar>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>Designation</Typography>
                  <Typography variant="body2" fontWeight="bold" noWrap>{designation}</Typography>
                </Box>
              </Box>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={4}>
            <Card variant="outlined" sx={{ borderLeft: '4px solid #757575', p: 1.5, borderRadius: 2, transition: 'all 0.3s ease', '&:hover': { boxShadow: '0 8px 24px rgba(117, 117, 117, 0.2)', transform: 'translateY(-4px)' } }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar sx={{ bgcolor: 'rgba(117, 117, 117, 0.1)', mr: 1.5, width: 40, height: 40 }}>
                  <WalletIcon sx={{ color: '#757575', fontSize: 20 }} />
                </Avatar>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>Net Salary</Typography>
                  <Typography variant="body2" fontWeight="bold">₹{netSalary}</Typography>
                </Box>
              </Box>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={4}>
            <Card variant="outlined" sx={{ borderLeft: '4px solid #757575', p: 1.5, borderRadius: 2, transition: 'all 0.3s ease', '&:hover': { boxShadow: '0 8px 24px rgba(117, 117, 117, 0.2)', transform: 'translateY(-4px)' } }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar sx={{ bgcolor: 'rgba(117, 117, 117, 0.1)', mr: 1.5, width: 40, height: 40 }}>
                  <BankIcon sx={{ color: '#757575', fontSize: 20 }} />
                </Avatar>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>Bank Name</Typography>
                  <Typography variant="body2" fontWeight="bold" noWrap>{bankName}</Typography>
                </Box>
              </Box>
            </Card>
          </Grid>
        </Grid>

        {/* Detailed Information Accordions */}
        <Grid container spacing={2}>
          {/* Payslip Info */}
          <Grid item xs={12} md={6}>
            <Accordion 
              sx={{ 
                borderLeft: '4px solid #2196F3',
                borderRadius: 2,
                '&:before': { display: 'none' },
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                height: '100%'
              }}
            >
            <AccordionSummary 
              expandIcon={<ExpandMoreIcon />}
              sx={{ 
                background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.05) 0%, rgba(33, 150, 243, 0.02) 100%)',
                '&:hover': { background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(33, 150, 243, 0.05) 100%)' }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Badge color="primary"  sx={{ mr: 2 }}>
                  <Avatar sx={{ bgcolor: 'rgba(33, 150, 243, 0.1)', width: 40, height: 40 }}>
                    <ReceiptIcon sx={{ color: '#2196F3' }} />
                  </Avatar>
                </Badge>
                <Box>
                  <Typography variant="subtitle1" fontWeight="bold">
                    Payslip Information
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Monthly salary details
                  </Typography>
                </Box>
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 3 }}>
              {Object.entries(profile.payslip || {}).map(([key, value]) => (
                <Box 
                  key={key} 
                  sx={{ 
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 1,
                    p: 1,
                    borderRadius: 2,
                    background: 'rgba(0,0,0,0.02)',
                    '&:hover': {
                      background: 'rgba(33, 150, 243, 0.08)'
                    }
                  }}
                >
                  <Typography variant="caption" sx={{ color: '#757575', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, minWidth: '120px' }}>
                    {key}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#333', textAlign: 'right' }}>
                    {value || 'N/A'}
                  </Typography>
                </Box>
              ))}
            </AccordionDetails>
          </Accordion>
          </Grid>

          {/* Offer Letter Info */}
          <Grid item xs={12} md={6}>
            <Accordion 
              sx={{ 
                borderLeft: '4px solid #2196F3',
                borderRadius: 2,
                '&:before': { display: 'none' },
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                height: '100%'
              }}
            >
            <AccordionSummary 
              expandIcon={<ExpandMoreIcon />}
              sx={{ 
                background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.05) 0%, rgba(33, 150, 243, 0.02) 100%)',
                '&:hover': { background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(33, 150, 243, 0.05) 100%)' }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Badge color="primary" sx={{ mr: 2 }}>
                  <Avatar sx={{ bgcolor: 'rgba(33, 150, 243, 0.1)', width: 40, height: 40 }}>
                    <AssignmentIcon sx={{ color: '#2196F3' }} />
                  </Avatar>
                </Badge>
                <Box>
                  <Typography variant="subtitle1" fontWeight="bold">
                    Offer Letter Information
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Employment offer details
                  </Typography>
                </Box>
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 3 }}>
              {Object.entries(profile.offer || {}).map(([key, value]) => (
                <Box 
                  key={key} 
                  sx={{ 
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 1,
                    p: 1,
                    borderRadius: 2,
                    background: 'rgba(0,0,0,0.02)',
                    '&:hover': {
                      background: 'rgba(33, 150, 243, 0.08)'
                    }
                  }}
                >
                  <Typography variant="caption" sx={{ color: '#757575', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, minWidth: '120px' }}>
                    {key}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#333', textAlign: 'right' }}>
                    {value || 'N/A'}
                  </Typography>
                </Box>
              ))}
            </AccordionDetails>
          </Accordion>
          </Grid>

          {/* Bank Statement Info */}
          <Grid item xs={12} md={6}>
            <Accordion 
              sx={{ 
                borderLeft: '4px solid #2196f3',
                borderRadius: 2,
                '&:before': { display: 'none' },
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                height: '100%'
              }}
            >
            <AccordionSummary 
              expandIcon={<ExpandMoreIcon />}
              sx={{ 
                background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.05) 0%, rgba(33, 150, 243, 0.02) 100%)',
                '&:hover': { background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(33, 150, 243, 0.05) 100%)' }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Badge color="info"  sx={{ mr: 2 }}>
                  <Avatar sx={{ bgcolor: 'rgba(33, 150, 243, 0.1)', width: 40, height: 40 }}>
                    <BankIcon sx={{ color: '#2196f3' }} />
                  </Avatar>
                </Badge>
                <Box>
                  <Typography variant="subtitle1" fontWeight="bold">
                    Bank Statement Information
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Account details
                  </Typography>
                </Box>
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 3 }}>
              {Object.entries(profile.bank || {}).map(([key, value]) => (
                <Box 
                  key={key} 
                  sx={{ 
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 1,
                    p: 1,
                    borderRadius: 2,
                    background: 'rgba(0,0,0,0.02)',
                    '&:hover': {
                      background: 'rgba(33, 150, 243, 0.08)'
                    }
                  }}
                >
                  <Typography variant="caption" sx={{ color: '#757575', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, minWidth: '120px' }}>
                    {key}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#333', textAlign: 'right' }}>
                    {value || 'N/A'}
                  </Typography>
                </Box>
              ))}
            </AccordionDetails>
          </Accordion>
          </Grid>

          {/* Form 16 Info */}
          <Grid item xs={12} md={6}>
            <Accordion 
              sx={{ 
                borderLeft: '4px solid #2196F3',
                borderRadius: 2,
                '&:before': { display: 'none' },
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                height: '100%'
              }}
            >
            <AccordionSummary 
              expandIcon={<ExpandMoreIcon />}
              sx={{ 
                background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.05) 0%, rgba(33, 150, 243, 0.02) 100%)',
                '&:hover': { background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1) 0%, rgba(33, 150, 243, 0.05) 100%)' }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Badge color="primary"  sx={{ mr: 2 }}>
                  <Avatar sx={{ bgcolor: 'rgba(33, 150, 243, 0.1)', width: 40, height: 40 }}>
                    <WorkIcon sx={{ color: '#2196F3' }} />
                  </Avatar>
                </Badge>
                <Box>
                  <Typography variant="subtitle1" fontWeight="bold">
                    Form 16 Information
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Tax deduction details
                  </Typography>
                </Box>
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 3 }}>
              {Object.entries(profile.form16 || {}).filter(([key]) => key !== 'TDS Records').map(([key, value]) => (
                <Box 
                  key={key} 
                  sx={{ 
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 1,
                    p: 1,
                    borderRadius: 2,
                    background: 'rgba(0,0,0,0.02)',
                    '&:hover': {
                      background: 'rgba(33, 150, 243, 0.08)'
                    }
                  }}
                >
                  <Typography variant="caption" sx={{ color: '#757575', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, minWidth: '120px' }}>
                    {key}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#333', textAlign: 'right' }}>
                    {value || 'N/A'}
                  </Typography>
                </Box>
              ))}
              {profile.form16?.['TDS Records'] && (
                <Box sx={{ mt: 3 }}>
                  <Typography 
                    variant="subtitle2" 
                    sx={{ 
                      color: '#757575', 
                      fontWeight: 700,
                      mb: 2,
                      textTransform: 'uppercase',
                      letterSpacing: 1
                    }}
                  >
                    TDS Records
                  </Typography>
                  <TableContainer sx={{ 
                    borderRadius: 2, 
                    border: '1px solid rgba(33, 150, 243, 0.2)',
                    background: 'rgba(255,255,255,0.5)'
                  }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow sx={{ background: 'linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(46, 125, 50, 0.1) 100%)' }}>
                          <TableCell sx={{ fontWeight: 700, color: '#4caf50' }}>Month</TableCell>
                          <TableCell sx={{ fontWeight: 700, color: '#4caf50' }}>Date</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700, color: '#4caf50' }}>Amount</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {profile.form16['TDS Records'].map((record, idx) => (
                          <TableRow 
                            key={idx}
                            sx={{
                              '&:hover': {
                                background: 'rgba(76, 175, 80, 0.05)'
                              }
                            }}
                          >
                            <TableCell sx={{ fontWeight: 500 }}>{record.Month}</TableCell>
                            <TableCell sx={{ fontWeight: 500 }}>{record.Date}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600, color: '#2e7d32' }}>₹{record.Amount}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
          </Grid>
        </Grid>
      </Box>
    );
  };

  const renderDocumentAnalyzerTab = () => {
    const docResults = results?.results?.document_analyzer_agent_results || {};
    
    // Download a locally stored GradCAM image through the backend
    const handleDownloadGradCAM = async (artifactUrl, filename) => {
      try {
        const urlParts = (artifactUrl || '').split('/');
        const imageFilename = urlParts[urlParts.length - 1] || filename;
        
        // Use backend endpoint to download with proper authentication
        const url = `${API_BASE_URL}/gradcam/${selectedCustomer}/${imageFilename}`;
        window.open(url, '_blank');
      } catch (err) {
        alert(`Failed to download GradCAM: ${err.message}`);
      }
    };
    
    // Helper to determine tampering level based on score
    const getTamperingLevelFromScore = (score) => {
      if (score > 0.6) return 'High';
      if (score >= 0.55) return 'Medium';
      return 'Low';
    };
    
    // Helper to get overall document status
    const getDocumentStatus = (pages) => {
      if (!pages || pages.length === 0) return { status: 'Unknown', color: 'default', badge: '?' };
      
      const hasHigh = pages.some(p => {
        const level = p.tampering_level || p.level;
        const score = p.ensemble_score || p.probability;
        return level === 'High' || (score && score > 0.6);
      });
      const hasMedium = pages.some(p => {
        const level = p.tampering_level || p.level;
        const score = p.ensemble_score || p.probability;
        return level === 'Medium' || (score && score >= 0.55 && score <= 0.6);
      });
      
      if (hasHigh) return { status: 'High Risk', color: 'error', badge: '✗', borderColor: '#F44336', bgColor: 'rgba(244, 67, 54, 0.1)' };
      if (hasMedium) return { status: 'Medium Risk', color: 'warning', badge: '!', borderColor: '#FB8C00', bgColor: 'rgba(251, 140, 0, 0.1)' };
      return { status: 'Low Risk', color: 'success', badge: '✓', borderColor: '#4CAF50', bgColor: 'rgba(76, 175, 80, 0.1)' };
    };
    
    return (
      <Box sx={{ p: 4, background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%)' }}>
        <Box sx={{ mb: 4 }}>
          <Typography 
            variant="h4" 
            sx={{ 
              fontWeight: 700,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mb: 1
            }}
          >
               Document Manipulation Analysis
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary' }}>
            AI-powered analysis to detect potential document manipulation
          </Typography>
        </Box>
        
        <Grid container spacing={3}>
          {Object.entries(docResults).map(([docName, pages]) => {
            const docStatus = getDocumentStatus(pages);
            const avgProbability = pages.length > 0 
              ? (pages.reduce((sum, p) => sum + p.probability, 0) / pages.length * 100).toFixed(1)
              : 0;
            
            return (
              <Grid item xs={12} md={6} key={docName}>
                <Card 
                  variant="outlined" 
                  sx={{ 
                    borderLeft: `4px solid ${docStatus.borderColor}`, 
                    p: 2,
                    borderRadius: 3,
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      boxShadow: `0 8px 24px ${docStatus.borderColor}40`,
                      transform: 'translateY(-4px)'
                    }
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Avatar sx={{ bgcolor: docStatus.bgColor, mr: 2 }}>
                      <DocumentIcon color={docStatus.color} />
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {docName}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {pages.length} page{pages.length !== 1 ? 's' : ''} analyzed
                      </Typography>
                    </Box>
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Status: <strong style={{ color: docStatus.borderColor }}>{docStatus.status}</strong>
                  </Typography>
                  
                  {pages.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="caption" color="text.secondary" gutterBottom sx={{ display: 'block', mb: 1, fontWeight: 600 }}>
                        Page Analysis:
                      </Typography>
                      {pages.map((page, idx) => {
                        const ensembleScore = page.ensemble_score || page.probability;
                        // Determine tampering level from score with new thresholds
                        let tamperingLevel = page.tampering_level || page.level;
                        if (ensembleScore) {
                          tamperingLevel = getTamperingLevelFromScore(ensembleScore);
                        }
                        
                        const hasGradCAM = page.gradcam_url || page.gradcam_path;
                        const showDownload = (tamperingLevel === 'High' || tamperingLevel === 'Medium') && hasGradCAM;
                        
                        return (
                          <Box 
                            key={idx} 
                            sx={{ 
                              display: 'flex', 
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              mt: 1,
                              p: 1.5,
                              borderRadius: 2,
                              background: 'rgba(0,0,0,0.02)',
                              border: '1px solid rgba(0,0,0,0.05)',
                              '&:hover': {
                                background: 'rgba(0,0,0,0.05)',
                                boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                              },
                              transition: 'all 0.2s ease'
                            }}
                          >
                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flex: 1 }}>
                              <Typography variant="body2" fontWeight="600">
                                Page {page.page}
                              </Typography>
                              <Chip 
                                label={tamperingLevel} 
                                color={getRiskColor(tamperingLevel)}
                                size="small"
                                sx={{ fontWeight: 600, fontSize: '0.7rem', height: 22 }}
                              />
                            </Box>
                            {showDownload && (
                              <IconButton 
                                size="small"
                                color="primary"
                                onClick={() => handleDownloadGradCAM(page.gradcam_url, `page${page.page}_gradcam.png`)}
                                sx={{ 
                                  ml: 1,
                                  bgcolor: 'rgba(25, 118, 210, 0.08)',
                                  '&:hover': {
                                    bgcolor: 'rgba(25, 118, 210, 0.15)'
                                  }
                                }}
                                title="Download GradCAM Heatmap"
                              >
                                <DownloadIcon fontSize="small" />
                              </IconButton>
                            )}
                          </Box>
                        );
                      })}
                    </Box>
                  )}
                  
                  
                </Card>
              </Grid>
            );
          })}
        </Grid>
      </Box>
    );
  };

  const renderCrossValidationTab = () => {
    const crossResults = results?.results?.cross_validation_agent_results || {};
    
    const getValidationStatus = (data) => {
      const values = Object.values(data).filter(v => typeof v === 'boolean');
      const matches = values.filter(v => v === true).length;
      const total = values.length;
      
      if (total === 0) return { status: 'Unknown', color: 'default', badge: '?', borderColor: '#9e9e9e', bgColor: 'rgba(158, 158, 158, 0.1)' };
      if (matches === total) return { status: 'All Match', color: 'success', badge: '✓', borderColor: '#4CAF50', bgColor: 'rgba(76, 175, 80, 0.1)' };
      if (matches === 0) return { status: 'All Mismatch', color: 'error', badge: '✗', borderColor: '#F44336', bgColor: 'rgba(244, 67, 54, 0.1)' };
      return { status: 'Partial Match', color: 'warning', badge: '!', borderColor: '#FB8C00', bgColor: 'rgba(251, 140, 0, 0.1)' };
    };
    
    const validations = [
      { key: 'payslip_vs_offer', title: 'Payslip vs Offer Letter', icon: <ReceiptIcon />, data: crossResults.payslip_vs_offer },
      { key: 'bank_vs_payslip', title: 'Bank Statement vs Payslip', icon: <BankIcon />, data: crossResults.bank_vs_payslip },
      { key: 'payslip_vs_form16', title: 'Payslip vs Form 16', icon: <WorkIcon />, data: crossResults.payslip_vs_form16 }
    ];
    
    return (
      <Box sx={{ p: 4, background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%)' }}>
        <Box sx={{ mb: 4 }}>
          <Typography 
            variant="h4" 
            sx={{ 
              fontWeight: 700,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mb: 1
            }}
          >
             Cross Validation Results
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary' }}>
            Verification of data consistency across different documents
          </Typography>
        </Box>
        
        <Grid container spacing={3}>
          {validations.map(({ key, title, icon, data }) => {
            if (!data) return null;
            
            const valStatus = getValidationStatus(data);
            const discrepancies = data.Discrepancies || [];
            
            return (
              <Grid item xs={12} md={6} key={key}>
                <Card 
                  variant="outlined" 
                  sx={{ 
                    borderLeft: `4px solid ${valStatus.borderColor}`, 
                    p: 2,
                    borderRadius: 3,
                    height: '100%',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      boxShadow: `0 8px 24px ${valStatus.borderColor}40`,
                      transform: 'translateY(-4px)'
                    }
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Badge 
                      color={valStatus.color} 
                      badgeContent={valStatus.badge} 
                      sx={{ mr: 2 }}
                    >
                      <Avatar sx={{ bgcolor: valStatus.bgColor }}>
                        {React.cloneElement(icon, { color: valStatus.color })}
                      </Avatar>
                    </Badge>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Cross-document validation
                      </Typography>
                    </Box>
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Status: <strong style={{ color: valStatus.borderColor }}>{valStatus.status}</strong>
                  </Typography>
                  
                  <Box sx={{ mt: 2 }}>
                    {Object.entries(data).filter(([k]) => k !== 'Discrepancies').map(([key, value]) => (
                      <Box 
                        key={key}
                        sx={{ 
                          display: 'flex', 
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          mt: 1,
                          p: 1,
                          borderRadius: 1,
                          background: 'rgba(0,0,0,0.02)',
                          '&:hover': {
                            background: 'rgba(0,0,0,0.05)'
                          }
                        }}
                      >
                        <Typography variant="caption" sx={{ fontWeight: 500 }}>
                          {key}
                        </Typography>
                        <Chip 
                          label={value === true ? '✓ Match' : value === false ? '✗ Mismatch' : value}
                          color={value === true ? 'success' : value === false ? 'error' : 'default'}
                          size="small"
                          sx={{ fontWeight: 600, fontSize: '0.7rem' }}
                        />
                      </Box>
                    ))}
                  </Box>
                  
                  {discrepancies.length > 0 && (
                    <Alert severity="warning" sx={{ mt: 2 }}>
                      <strong>Discrepancies Found:</strong>
                      {discrepancies.map((disc, idx) => (
                        <Typography key={idx} variant="caption" display="block" sx={{ mt: 0.5 }}>
                          • {disc}
                        </Typography>
                      ))}
                    </Alert>
                  )}
                </Card>
              </Grid>
            );
          })}
        </Grid>
      </Box>
    );
  };

  const renderAAVerificationTab = () => {
    const aaResults = results?.results?.account_aggrigator_agent_results || {};
    const aaChecks = aaResults.aa_checks || {};
    
    const getAAStatus = () => {
      const values = Object.entries(aaChecks).filter(([k, v]) => k !== 'AA Verification Status' && typeof v === 'boolean');
      const matches = values.filter(([_, v]) => v === true).length;
      const total = values.length;
      
      if (total === 0) return { status: 'No Data', color: 'default', badge: '?', borderColor: '#9e9e9e', bgColor: 'rgba(158, 158, 158, 0.1)' };
      if (matches === total) return { status: 'Verified', color: 'success', badge: '✓', borderColor: '#4CAF50', bgColor: 'rgba(76, 175, 80, 0.1)' };
      if (matches === 0) return { status: 'Failed', color: 'error', badge: '✗', borderColor: '#F44336', bgColor: 'rgba(244, 67, 54, 0.1)' };
      return { status: 'Partial', color: 'warning', badge: '!', borderColor: '#FB8C00', bgColor: 'rgba(251, 140, 0, 0.1)' };
    };
    
    const aaStatus = getAAStatus();
    const verificationStatus = aaChecks['AA Verification Status'] || '';
    
    return (
      <Box sx={{ p: 4, background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%)' }}>
        <Box sx={{ mb: 4 }}>
          <Typography 
            variant="h4" 
            sx={{ 
              fontWeight: 700,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mb: 1
            }}
          >
               Account Aggregator Verification
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary' }}>
            Verification against Account Aggregator data
          </Typography>
        </Box>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card 
              variant="outlined" 
              sx={{ 
                borderLeft: `4px solid ${aaStatus.borderColor}`, 
                p: 2,
                borderRadius: 3,
                height: '100%',
                transition: 'all 0.3s ease',
                '&:hover': {
                  boxShadow: `0 8px 24px ${aaStatus.borderColor}40`,
                  transform: 'translateY(-4px)'
                }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Badge 
                  color={aaStatus.color} 
                  badgeContent={aaStatus.badge} 
                  sx={{ mr: 2 }}
                >
                  <Avatar sx={{ bgcolor: aaStatus.bgColor }}>
                    <BankIcon color={aaStatus.color} />
                  </Avatar>
                </Badge>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">
                    Account Aggregator Checks
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Bank account verification
                  </Typography>
                </Box>
              </Box>
              
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Status: <strong style={{ color: aaStatus.borderColor }}>{aaStatus.status}</strong>
              </Typography>
              
              <Box sx={{ mt: 2 }}>
                {Object.entries(aaChecks).filter(([k]) => k !== 'AA Verification Status').map(([key, value]) => (
                  <Box 
                    key={key}
                    sx={{ 
                      display: 'flex', 
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      mt: 1,
                      p: 1,
                      borderRadius: 1,
                      background: 'rgba(0,0,0,0.02)',
                      '&:hover': {
                        background: 'rgba(0,0,0,0.05)'
                      }
                    }}
                  >
                    <Typography variant="caption" sx={{ fontWeight: 500 }}>
                      {key}
                    </Typography>
                    <Chip 
                      label={value === true ? '✓ Match' : value === false ? '✗ Mismatch' : value}
                      color={value === true ? 'success' : value === false ? 'error' : 'default'}
                      size="small"
                      sx={{ fontWeight: 600, fontSize: '0.7rem' }}
                    />
                  </Box>
                ))}
              </Box>
              
              {verificationStatus && (
                <Alert 
                  severity={verificationStatus.includes('✅') ? 'success' : 'warning'} 
                  sx={{ mt: 2 }}
                >
                  {verificationStatus}
                </Alert>
              )}
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card 
              sx={{ 
                p: 3, 
                borderRadius: 3,
                background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)',
                border: '2px solid rgba(102, 126, 234, 0.2)',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center'
              }}
            >
              <Avatar 
                sx={{ 
                  width: 80, 
                  height: 80, 
                  bgcolor: aaStatus.bgColor,
                  mb: 2
                }}
              >
                <BankIcon sx={{ fontSize: 40 }} color={aaStatus.color} />
              </Avatar>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                {aaStatus.status}
              </Typography>
              <Typography variant="body2" color="text.secondary" textAlign="center">
                Account Aggregator verification {aaStatus.status.toLowerCase()}
              </Typography>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  };

  const renderDecisionTab = () => {
    const decision = results?.results?.descision_making_agent || {};
    
    // Use structured JSON fields if available, otherwise fallback to old format
    const decisionStatus = decision.suggested_status || 'UNKNOWN';
    const riskLevel = decision.risk || 'Unknown';
    const decisionText = decision.response || decision.decision_response || 'No decision available';
    
    // Function to parse and render decision text with table detection
    const renderDecisionContent = (text) => {
      if (!text) return 'No decision available';
      
      // Replace escaped newlines with actual newlines
      const normalizedText = text.replace(/\\n/g, '\n');
      
      // Split text into sections - only split on section numbers at start of line (1. 2. 3. etc.)
      // Don't split on decimal numbers like 0.29 or 0.57
      const sections = normalizedText.split(/(?=^[1-9]\d*\.\s)/m); // Split on "1. ", "2. ", etc. at line start
      
      return sections.map((section, index) => {
        // Check if section contains a table (has box drawing characters)
        const hasTable = /[╒╤╕╞╪╡╘╧╛═│├┼┤└┴┘─]/.test(section);
        
        if (hasTable) {
          // Extract table and surrounding text
          const tableMatch = section.match(/(.*?)(╒[^]*?╛)(.*)/s);
          
          if (tableMatch) {
            const beforeTable = tableMatch[1];
            const tableText = tableMatch[2];
            const afterTable = tableMatch[3];
            
            return (
              <Box key={index} sx={{ mb: 3 }}>
                {beforeTable && (
                  <Typography variant="body1" sx={{ mb: 2, whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
                    {beforeTable.trim()}
                  </Typography>
                )}
                
                {/* Render table in a styled box */}
                <Box 
                  sx={{ 
                    fontFamily: 'Courier New, monospace',
                    fontSize: '0.85rem',
                    whiteSpace: 'pre',
                    overflowX: 'auto',
                    p: 2,
                    borderRadius: 2,
                    background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%)',
                    border: '2px solid rgba(102, 126, 234, 0.2)',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                    mb: 2
                  }}
                >
                  {tableText}
                </Box>
                
                {afterTable && (
                  <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
                    {afterTable.trim()}
                  </Typography>
                )}
              </Box>
            );
          }
        }
        
        // Regular text section (no table)
        return (
          <Typography 
            key={index} 
            variant="body1" 
            sx={{ 
              mb: 2, 
              whiteSpace: 'pre-wrap', 
              lineHeight: 1.8,
              color: '#333'
            }}
          >
            {section.trim()}
          </Typography>
        );
      });
    };
    
    return (
      <Box sx={{ p: 4, background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%)' }}>
        <Box sx={{ mb: 4 }}>
          <Typography 
            variant="h4" 
            sx={{ 
              fontWeight: 700,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mb: 1
            }}
          >
               Final Decision
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary' }}>
            AI-powered decision based on all verification results
          </Typography>
        </Box>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card 
              elevation={0}
              sx={{
                borderRadius: 3,
                border: '3px solid',
                borderColor: decisionStatus === 'APPROVED' ? '#4caf50' : 
                            decisionStatus === 'REJECTED' ? '#f44336' : '#ff9800',
                background: decisionStatus === 'APPROVED' 
                  ? 'linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(255, 255, 255, 0.95) 100%)'
                  : decisionStatus === 'REJECTED'
                  ? 'linear-gradient(135deg, rgba(244, 67, 54, 0.1) 0%, rgba(255, 255, 255, 0.95) 100%)'
                  : 'linear-gradient(135deg, rgba(255, 152, 0, 0.1) 0%, rgba(255, 255, 255, 0.95) 100%)',
                transition: 'all 0.3s ease',
                '&:hover': {
                  boxShadow: decisionStatus === 'APPROVED' 
                    ? '0 12px 32px rgba(76, 175, 80, 0.25)'
                    : decisionStatus === 'REJECTED'
                    ? '0 12px 32px rgba(244, 67, 54, 0.25)'
                    : '0 12px 32px rgba(255, 152, 0, 0.25)',
                  transform: 'translateY(-4px)'
                }
              }}
            >
              <CardContent sx={{ p: 4, textAlign: 'center' }}>
                <Typography 
                  variant="h6" 
                  gutterBottom
                  sx={{ 
                    fontWeight: 700,
                    color: decisionStatus === 'APPROVED' ? '#2e7d32' : 
                           decisionStatus === 'REJECTED' ? '#c62828' : '#e65100',
                    mb: 3
                  }}
                >
                  Status Suggested
                </Typography>
                <Chip 
                  label={decisionStatus}
                  color={decisionStatus === 'APPROVED' ? 'success' : 
                         decisionStatus === 'REJECTED' ? 'error' : 'warning'}
                  sx={{ 
                    fontSize: '1.5rem', 
                    p: 3,
                    fontWeight: 700,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                  }}
                />
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card 
              elevation={0}
              sx={{
                borderRadius: 3,
                border: '3px solid',
                borderColor: riskLevel === 'Low' ? '#4caf50' : 
                            riskLevel === 'High' ? '#f44336' : '#ff9800',
                background: riskLevel === 'Low' 
                  ? 'linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(255, 255, 255, 0.95) 100%)'
                  : riskLevel === 'High'
                  ? 'linear-gradient(135deg, rgba(244, 67, 54, 0.1) 0%, rgba(255, 255, 255, 0.95) 100%)'
                  : 'linear-gradient(135deg, rgba(255, 152, 0, 0.1) 0%, rgba(255, 255, 255, 0.95) 100%)',
                transition: 'all 0.3s ease',
                '&:hover': {
                  boxShadow: riskLevel === 'Low' 
                    ? '0 12px 32px rgba(76, 175, 80, 0.25)'
                    : riskLevel === 'High'
                    ? '0 12px 32px rgba(244, 67, 54, 0.25)'
                    : '0 12px 32px rgba(255, 152, 0, 0.25)',
                  transform: 'translateY(-4px)'
                }
              }}
            >
              <CardContent sx={{ p: 4, textAlign: 'center' }}>
                <Typography 
                  variant="h6" 
                  gutterBottom
                  sx={{ 
                    fontWeight: 700,
                    color: riskLevel === 'Low' ? '#2e7d32' : 
                           riskLevel === 'High' ? '#c62828' : '#e65100',
                    mb: 3
                  }}
                >
                  Risk Level
                </Typography>
                <Chip 
                  label={riskLevel}
                  color={getRiskColor(riskLevel)}
                  sx={{ 
                    fontSize: '1.5rem', 
                    p: 3,
                    fontWeight: 700,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                  }}
                />
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12}>
            <Card 
              elevation={0}
              sx={{
                borderRadius: 3,
                border: '2px solid',
                borderColor: 'rgba(102, 126, 234, 0.2)',
                background: 'rgba(255,255,255,0.95)',
                transition: 'all 0.3s ease',
                '&:hover': {
                  borderColor: '#667eea',
                  boxShadow: '0 8px 24px rgba(102, 126, 234, 0.15)',
                }
              }}
            >
              <CardContent sx={{ p: 4 }}>
                <Typography 
                  variant="h6" 
                  gutterBottom
                  sx={{
                    fontWeight: 700,
                    color: '#667eea',
                    mb: 2
                  }}
                >
                   Detailed Analysis
                </Typography>
                <Divider sx={{ mb: 3, borderColor: 'rgba(102, 126, 234, 0.2)' }} />
                <Box 
                  sx={{ 
                    p: 3,
                    borderRadius: 2,
                    background: 'rgba(102, 126, 234, 0.03)',
                    border: '1px solid rgba(102, 126, 234, 0.1)'
                  }}
                >
                  {renderDecisionContent(decisionText)}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  };

  // Show different pages based on currentView
  if (currentView === 'home') {
    return (
      <HomePage 
        onNavigateToApp={() => setCurrentView('app')} 
        onNavigateToEscalations={() => setCurrentView('escalations')}
        onNavigateToApprovedLoans={() => setCurrentView('approved')}
      />
    );
  }

  if (currentView === 'escalations') {
    return <HumanEscalationPage onBack={() => setCurrentView('home')} />;
  }

  if (currentView === 'approved') {
    return <ApprovedLoansPage onBack={() => setCurrentView('home')} />;
  }

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
            onClick={() => setCurrentView('home')}
            sx={{
              position: 'absolute',
              top: 0,
              right: 0,
              color: 'white',
              bgcolor: 'rgba(255,255,255,0.2)',
              backdropFilter: 'blur(10px)',
              '&:hover': {
                bgcolor: 'rgba(255,255,255,0.3)',
                transform: 'scale(1.1)',
              },
              transition: 'all 0.3s ease'
            }}
          >
            <HomeIcon />
          </IconButton>
          <Typography 
            variant="h3" 
            sx={{ 
              color: 'white', 
              fontWeight: 'bold', 
              mb: 1,
              textShadow: '2px 2px 4px rgba(0,0,0,0.2)'
            }}
          >
            🏦 LendIQ
          </Typography>
          <Typography 
            variant="h6" 
            sx={{ 
              color: 'rgba(255,255,255,0.95)',
              fontWeight: 300
            }}
          >
            AI-Powered Document Verification & Risk Assessment
          </Typography>
        </Box>

        {/* Customer Selection */}
        <Paper 
          elevation={8} 
          sx={{ 
            p: 4, 
            mb: 4,
            borderRadius: 4,
            background: 'rgba(255,255,255,0.95)',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
          }}
        >
          <Typography 
            variant="h5" 
            gutterBottom 
            sx={{ 
              fontWeight: 600,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mb: 3
            }}
          >
            📋 Customer Verification
          </Typography>
          
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="body2" gutterBottom sx={{ color: 'text.secondary', mb: 1 }}>
                Select Customer ID
              </Typography>
              <Select
                fullWidth
                value={selectedCustomer}
                onChange={(e) => setSelectedCustomer(e.target.value)}
                displayEmpty
                disabled={loading}
                sx={{
                  borderRadius: 2,
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: '#667eea',
                  },
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: '#764ba2',
                  },
                  '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                    borderColor: '#667eea',
                    borderWidth: 2,
                  }
                }}
              >
                <MenuItem value="" disabled>
                  Choose a customer...
                </MenuItem>
                {customers.map((customer) => (
                  <MenuItem key={customer} value={customer}>
                    {customer}
                  </MenuItem>
                ))}
              </Select>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box sx={{ mt: { xs: 0, md: 3 } }}>
                <Button
                  variant="contained"
                  size="large"
                  fullWidth
                  onClick={handleRunWorkflow}
                  disabled={!selectedCustomer || loading}
                  startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                  sx={{
                    py: 1.5,
                    borderRadius: 2,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%)',
                      boxShadow: '0 6px 20px rgba(102, 126, 234, 0.6)',
                      transform: 'translateY(-2px)',
                    },
                    '&:disabled': {
                      background: '#ccc',
                    },
                    transition: 'all 0.3s ease',
                    fontSize: '1.1rem',
                    fontWeight: 600
                  }}
                >
                  {loading ? 'Processing...' : 'Run Verification'}
                </Button>
              </Box>
            </Grid>
          </Grid>
          
          {loading && (
            <Box sx={{ mt: 3 }}>
              <LinearProgress 
                sx={{
                  height: 6,
                  borderRadius: 3,
                  backgroundColor: 'rgba(102, 126, 234, 0.1)',
                  '& .MuiLinearProgress-bar': {
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    borderRadius: 3,
                  }
                }}
              />
              <Typography 
                variant="body2" 
                sx={{ 
                  mt: 1, 
                  textAlign: 'center',
                  color: '#667eea',
                  fontWeight: 500
                }}
              >
                Analyzing documents and running AI verification...
              </Typography>
            </Box>
          )}
        </Paper>

        {/* Error Display */}
        {error && (
          <Alert 
            severity="error" 
            sx={{ 
              mb: 4,
              borderRadius: 3,
              boxShadow: '0 4px 12px rgba(211, 47, 47, 0.2)'
            }} 
            onClose={() => setError(null)}
          >
            {error}
          </Alert>
        )}

        {/* Results Section */}
        {results && (
          <Paper 
            elevation={8} 
            sx={{ 
              mb: 4,
              borderRadius: 4,
              overflow: 'hidden',
              background: 'rgba(255,255,255,0.95)',
              backdropFilter: 'blur(10px)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
            }}
          >
            {/* Status Banner */}
            <Box sx={{ 
              p: 3, 
              background: getStatusColor(results.status) === 'success' 
                ? 'linear-gradient(135deg, #4caf50 0%, #45a049 100%)' 
                : getStatusColor(results.status) === 'error' 
                ? 'linear-gradient(135deg, #f44336 0%, #e53935 100%)' 
                : 'linear-gradient(135deg, #ff9800 0%, #fb8c00 100%)',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
            }}>
              <Typography 
                variant="h5" 
                sx={{ 
                  color: 'white', 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 1,
                  fontWeight: 600,
                  textShadow: '1px 1px 2px rgba(0,0,0,0.2)'
                }}
              >
                {getStatusColor(results.status) === 'success' ? <CheckCircle fontSize="large" /> : 
                 getStatusColor(results.status) === 'error' ? <Error fontSize="large" /> : <Warning fontSize="large" />}
                Verification {results.status.toUpperCase()}
              </Typography>
            </Box>

            {/* Tabs */}
            <Tabs 
              value={activeTab} 
              onChange={(e, newValue) => setActiveTab(newValue)}
              variant="scrollable"
              scrollButtons="auto"
              sx={{ 
                borderBottom: 2, 
                borderColor: '#667eea',
                px: 2,
                '& .MuiTab-root': {
                  fontSize: '1rem',
                  fontWeight: 600,
                  textTransform: 'none',
                  minHeight: 64,
                  '&.Mui-selected': {
                    color: '#667eea',
                  }
                },
                '& .MuiTabs-indicator': {
                  height: 3,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  borderRadius: '3px 3px 0 0'
                }
              }}
            >
              <Tab label="Customer Profile" />
              <Tab label="Document Analysis Agent" />
              <Tab label="Cross Validation Agent" />
              <Tab label="AA Verification Agent" />
              <Tab label="Final Decision Agent" />
            </Tabs>

            {/* Tab Content */}
            {activeTab === 0 && renderProfileTab()}
            {activeTab === 1 && renderDocumentAnalyzerTab()}
            {activeTab === 2 && renderCrossValidationTab()}
            {activeTab === 3 && renderAAVerificationTab()}
            {activeTab === 4 && renderDecisionTab()}

            {/* Action Buttons */}
            <Box sx={{ 
              p: 4, 
              borderTop: 2, 
              borderColor: '#667eea',
              background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%)'
            }}>
              <Typography 
                variant="h5" 
                gutterBottom 
                sx={{ 
                  mb: 3, 
                  fontWeight: 600,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                📋 Quick Actions
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    variant="contained"
                    fullWidth
                    size="large"
                    startIcon={<EmailIcon />}
                    onClick={handleSendEmail}
                    sx={{
                      py: 1.5,
                      borderRadius: 2,
                      background: 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)',
                      boxShadow: '0 4px 12px rgba(25, 118, 210, 0.3)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #1565c0 0%, #0d47a1 100%)',
                        boxShadow: '0 6px 16px rgba(25, 118, 210, 0.4)',
                        transform: 'translateY(-2px)',
                      },
                      transition: 'all 0.3s ease',
                      fontWeight: 600
                    }}
                  >
                    Send Email
                  </Button>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    variant="contained"
                    fullWidth
                    size="large"
                    startIcon={<SmsIcon />}
                    onClick={handleSendSMS}
                    sx={{
                      py: 1.5,
                      borderRadius: 2,
                      background: 'linear-gradient(135deg, #0288d1 0%, #0277bd 100%)',
                      boxShadow: '0 4px 12px rgba(2, 136, 209, 0.3)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #0277bd 0%, #01579b 100%)',
                        boxShadow: '0 6px 16px rgba(2, 136, 209, 0.4)',
                        transform: 'translateY(-2px)',
                      },
                      transition: 'all 0.3s ease',
                      fontWeight: 600
                    }}
                  >
                    Send SMS
                  </Button>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    variant="contained"
                    fullWidth
                    size="large"
                    startIcon={<EscalateIcon />}
                    onClick={handleEscalate}
                    sx={{
                      py: 1.5,
                      borderRadius: 2,
                      background: 'linear-gradient(135deg, #ed6c02 0%, #e65100 100%)',
                      boxShadow: '0 4px 12px rgba(237, 108, 2, 0.3)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #e65100 0%, #bf360c 100%)',
                        boxShadow: '0 6px 16px rgba(237, 108, 2, 0.4)',
                        transform: 'translateY(-2px)',
                      },
                      transition: 'all 0.3s ease',
                      fontWeight: 600
                    }}
                  >
                    Human Review
                  </Button>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    variant="contained"
                    fullWidth
                    size="large"
                    startIcon={<ApproveIcon />}
                    onClick={handleApproveLoan}
                    sx={{
                      py: 1.5,
                      borderRadius: 2,
                      background: 'linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%)',
                      boxShadow: '0 4px 12px rgba(46, 125, 50, 0.3)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #1b5e20 0%, #0d3d0f 100%)',
                        boxShadow: '0 6px 16px rgba(46, 125, 50, 0.4)',
                        transform: 'translateY(-2px)',
                      },
                      transition: 'all 0.3s ease',
                      fontWeight: 600
                    }}
                  >
                    Approve Loan
                  </Button>
                </Grid>
              </Grid>
            </Box>
          </Paper>
        )}

        {/* Footer */}
        <Box sx={{ textAlign: 'center', mt: 6, pb: 2 }}>
          <Typography 
            variant="body2" 
            sx={{ 
              color: 'rgba(255,255,255,0.8)',
              fontWeight: 300
            }}
          >
            © 2024 LendIQ - AI-Powered Loan Verification System
          </Typography>
          <Typography 
            variant="caption" 
            sx={{ 
              color: 'rgba(255,255,255,0.6)',
              display: 'block',
              mt: 0.5
            }}
          >
            Powered locally with Google Gemini
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}

export default App;
