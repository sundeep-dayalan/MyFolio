import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CheckCircle, AlertCircle, ExternalLink, CreditCard } from 'lucide-react';
import { api } from '@/services/api';

interface SetupStatus {
  plaid_configured: boolean;
  oauth_configured: boolean;
  app_ready: boolean;
}

interface PlaidConfig {
  client_id: string;
  secret: string;
  env: 'sandbox' | 'production';
}

export const PlaidSetup: React.FC = () => {
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);
  const [plaidConfig, setPlaidConfig] = useState<PlaidConfig>({
    client_id: '',
    secret: '',
    env: 'sandbox'
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchSetupStatus();
  }, []);

  const fetchSetupStatus = async () => {
    try {
      const response = await api.get('/setup/status');
      setSetupStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch setup status:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      await api.post('/setup/plaid', plaidConfig);
      setSuccess('Plaid configuration saved successfully! You can now connect your bank accounts.');
      fetchSetupStatus();
      
      // Clear form
      setPlaidConfig({
        client_id: '',
        secret: '',
        env: 'sandbox'
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to configure Plaid');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkip = () => {
    setSuccess('You can set up Plaid integration later from the settings page.');
  };

  if (!setupStatus) {
    return (
      <Card className="w-full max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-6 w-6" />
            Loading Setup Status...
          </CardTitle>
        </CardHeader>
      </Card>
    );
  }

  if (setupStatus.plaid_configured) {
    return (
      <Card className="w-full max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-green-600">
            <CheckCircle className="h-6 w-6" />
            Plaid Integration Configured
          </CardTitle>
          <CardDescription>
            Your Plaid integration is set up and ready to use. You can now connect your bank accounts.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CreditCard className="h-6 w-6" />
          Set Up Plaid Integration
        </CardTitle>
        <CardDescription>
          Connect your bank accounts securely with Plaid. This step is optional - you can skip it and set it up later.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Instructions */}
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <strong>Need Plaid credentials?</strong>
            <br />
            1. Go to{' '}
            <a 
              href="https://dashboard.plaid.com/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline inline-flex items-center gap-1"
            >
              Plaid Dashboard <ExternalLink className="h-3 w-3" />
            </a>
            <br />
            2. Sign up or log in to your account
            <br />
            3. Create a new application
            <br />
            4. Copy your Client ID and Secret Key
          </AlertDescription>
        </Alert>

        {/* Success Message */}
        {success && (
          <Alert className="border-green-200 bg-green-50">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              {success}
            </AlertDescription>
          </Alert>
        )}

        {/* Error Message */}
        {error && (
          <Alert className="border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              {error}
            </AlertDescription>
          </Alert>
        )}

        {/* Configuration Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="client_id">Plaid Client ID</Label>
            <Input
              id="client_id"
              type="text"
              placeholder="Enter your Plaid Client ID"
              value={plaidConfig.client_id}
              onChange={(e) => setPlaidConfig(prev => ({ ...prev, client_id: e.target.value }))}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="secret">Plaid Secret Key</Label>
            <Input
              id="secret"
              type="password"
              placeholder="Enter your Plaid Secret Key"
              value={plaidConfig.secret}
              onChange={(e) => setPlaidConfig(prev => ({ ...prev, secret: e.target.value }))}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="environment">Environment</Label>
            <Select
              value={plaidConfig.env}
              onValueChange={(value: 'sandbox' | 'production') => 
                setPlaidConfig(prev => ({ ...prev, env: value }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sandbox">Sandbox (for testing)</SelectItem>
                <SelectItem value="production">Production (live data)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={isLoading} className="flex-1">
              {isLoading ? 'Configuring...' : 'Configure Plaid'}
            </Button>
            <Button type="button" variant="outline" onClick={handleSkip} className="flex-1">
              Skip for Now
            </Button>
          </div>
        </form>

        {/* Test Credentials Info */}
        <Alert className="border-blue-200 bg-blue-50">
          <AlertCircle className="h-4 w-4 text-blue-600" />
          <AlertDescription className="text-blue-800">
            <strong>For testing (Sandbox mode):</strong>
            <br />
            Use "First Platypus Bank" with username "user_good" and password "pass_good"
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
};