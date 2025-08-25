import React, { useState, useEffect } from 'react';
import { ShieldCheck, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Spinner } from '@/components/ui/spinner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  PlaidConfigService,
  type PlaidConfigurationCreate,
  type PlaidConfigurationResponse,
  type PlaidConfigurationStatus,
  type PlaidValidationResult,
} from '@/services/PlaidConfigService';
import { MicrosoftAuthService } from '@/services/MicrosoftAuthService';
import { logger } from '@/services/LoggerService';

type Environment = 'sandbox' | 'development' | 'production';

interface PlaidFormData {
  plaid_client_id: string;
  plaid_secret: string;
  environment: Environment;
}

export const SecretsSection: React.FC = () => {
  const [status, setStatus] = useState<PlaidConfigurationStatus | null>(null);
  const [config, setConfig] = useState<PlaidConfigurationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [validationResult, setValidationResult] = useState<PlaidValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [formData, setFormData] = useState<PlaidFormData>({
    plaid_client_id: '',
    plaid_secret: '',
    environment: 'sandbox',
  });

  // Load initial data
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Get status (public endpoint)
      const statusData = await PlaidConfigService.getConfigurationStatus();
      setStatus(statusData);

      // If configured, try to get configuration details (requires auth)
      if (statusData.is_configured) {
        try {
          // Check if user is authenticated before making auth call
          if (MicrosoftAuthService.isAuthenticated() && !MicrosoftAuthService.isTokenExpired()) {
            const configData = await PlaidConfigService.getConfiguration();
            setConfig(configData);

            // Pre-fill form with existing environment
            setFormData((prev) => ({
              ...prev,
              environment: configData.environment,
            }));
          } else {
            // User not authenticated, skip getting detailed config
            logger.info('User not authenticated, skipping detailed config load', 'PLAID_CONFIG');
          }
        } catch (error) {
          // If we can't get config details (maybe auth issue), just show status
          logger.warn('Could not load configuration details', 'PLAID_CONFIG', error);
          // Don't set error state for auth issues, just log them
          if (error instanceof Error && error.message.includes('Authentication')) {
            logger.info('Authentication error ignored in settings page', 'PLAID_CONFIG');
          } else {
            setError(
              `Could not load configuration details: ${
                error instanceof Error ? error.message : 'Unknown error'
              }`,
            );
          }
        }
      }
    } catch (error) {
      logger.error('Failed to load Plaid configuration data', 'PLAID_CONFIG', error);
      setError(error instanceof Error ? error.message : 'Failed to load configuration');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (field: keyof PlaidFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setValidationResult(null);
    setError(null);
    setSuccess(null);
  };

  const validateCredentials = async () => {
    if (!formData.plaid_client_id || !formData.plaid_secret) {
      setError('Please fill in both Client ID and Secret');
      return;
    }

    try {
      setIsValidating(true);
      setError(null);

      const result = await PlaidConfigService.validateCredentials({
        plaid_client_id: formData.plaid_client_id,
        plaid_secret: formData.plaid_secret,
        environment: formData.environment,
      });

      setValidationResult(result);
    } catch (error) {
      logger.error('Validation failed', 'PLAID_CONFIG', error);
      setError(error instanceof Error ? error.message : 'Validation failed');
    } finally {
      setIsValidating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.plaid_client_id || !formData.plaid_secret) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      setSuccess(null);

      const configData: PlaidConfigurationCreate = {
        plaid_client_id: formData.plaid_client_id,
        plaid_secret: formData.plaid_secret,
        environment: formData.environment,
      };

      await PlaidConfigService.storeConfiguration(configData);
      setSuccess('Plaid configuration saved successfully!');

      // Reload data to reflect changes
      await loadData();

      // Clear form
      setFormData({
        plaid_client_id: '',
        plaid_secret: '',
        environment: 'sandbox',
      });
      setValidationResult(null);
    } catch (error) {
      logger.error('Failed to save configuration', 'PLAID_CONFIG', error);
      setError(error instanceof Error ? error.message : 'Failed to save configuration');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      setError(null);
      setSuccess(null);

      // Debug authentication state
      const isAuth = MicrosoftAuthService.isAuthenticated();
      const isExpired = MicrosoftAuthService.isTokenExpired();
      const token = MicrosoftAuthService.getAuthToken();
      const expiry = localStorage.getItem('tokenExpiry');

      logger.info('Delete operation - Auth debug info', 'PLAID_CONFIG', {
        isAuthenticated: isAuth,
        isTokenExpired: isExpired,
        hasToken: !!token,
        tokenExpiry: expiry ? new Date(parseInt(expiry)).toISOString() : 'null',
        currentTime: new Date().toISOString(),
      });

      await PlaidConfigService.deleteConfiguration();
      setSuccess('Plaid configuration deleted successfully!');

      // Reload data to reflect changes
      await loadData();

      // Reset form
      setFormData({
        plaid_client_id: '',
        plaid_secret: '',
        environment: 'sandbox',
      });
      setValidationResult(null);
    } catch (error) {
      logger.error('Failed to delete configuration', 'PLAID_CONFIG', error);
      setError(error instanceof Error ? error.message : 'Failed to delete configuration');
    } finally {
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner className="h-6 w-6" />
        <span className="ml-2">Loading configuration...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status Section */}
      <div>
        <h3 className="text-lg font-medium mb-4">Plaid secrets</h3>

        {status && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium">Status:</span>
              <Badge variant={status.is_configured ? 'default' : 'secondary'}>
                {status.is_configured ? (
                  <span className="flex items-center gap-1">
                    Configured
                    <ShieldCheck />
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    Not Configured
                    <TriangleAlert />
                  </span>
                )}
              </Badge>
              {status.is_configured && <Badge variant="outline">{status.is_configured}</Badge>}
            </div>

            {config && (
              <div className="text-sm text-muted-foreground">
                <p>Client ID: {config.plaid_client_id.replace(/.{4}$/, '****')}</p>
                <p>Created: {new Date(config.created_at).toLocaleDateString()}</p>
                <p>Last updated: {new Date(config.updated_at).toLocaleDateString()}</p>
              </div>
            )}
          </div>
        )}

        <Separator className="my-4" />
      </div>

      {/* Configuration Form */}
      <div>
        {status?.is_configured ? (
          <Card>
            <CardHeader>
              <CardTitle>Plaid Configuration</CardTitle>
              <CardDescription>
                A Plaid configuration already exists. To update the configuration, you must first
                delete the existing one.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" disabled={isDeleting}>
                    {isDeleting && <Spinner className="mr-2 h-4 w-4" />}
                    Delete Configuration
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete Plaid Configuration?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This action cannot be undone. This will permanently delete your Plaid
                      configuration and disable Plaid features until a new configuration is added.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleDelete}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      Delete Configuration
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>New Plaid Configuration</CardTitle>
              <CardDescription>
                Add your Plaid API credentials to enable financial data integration.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!MicrosoftAuthService.isAuthenticated() && (
                <Alert>
                  <AlertDescription>
                    You need to be logged in to manage Plaid configuration.
                  </AlertDescription>
                </Alert>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="environment">Environment</Label>
                    <Select
                      value={formData.environment}
                      onValueChange={(value: Environment) =>
                        handleInputChange('environment', value)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select environment" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="sandbox">Sandbox</SelectItem>
                        <SelectItem value="production">Production</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="plaid_client_id">Plaid Client ID</Label>
                  <Input
                    id="plaid_client_id"
                    type="text"
                    placeholder="Enter your Plaid Client ID"
                    value={formData.plaid_client_id}
                    onChange={(e) => handleInputChange('plaid_client_id', e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="plaid_secret">Plaid Secret</Label>
                  <Input
                    id="plaid_secret"
                    type="password"
                    placeholder="Enter your Plaid Secret"
                    value={formData.plaid_secret}
                    onChange={(e) => handleInputChange('plaid_secret', e.target.value)}
                    required
                  />
                </div>

                {/* Validation Result */}
                {validationResult && (
                  <Alert variant={validationResult.is_valid ? 'default' : 'destructive'}>
                    <AlertDescription>{validationResult.message}</AlertDescription>
                  </Alert>
                )}

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={validateCredentials}
                    disabled={
                      isValidating ||
                      !formData.plaid_client_id ||
                      !formData.plaid_secret ||
                      !MicrosoftAuthService.isAuthenticated()
                    }
                  >
                    {isValidating && <Spinner className="mr-2 h-4 w-4" />}
                    Validate Credentials
                  </Button>

                  <Button
                    type="submit"
                    disabled={
                      isSubmitting ||
                      !validationResult?.is_valid ||
                      !MicrosoftAuthService.isAuthenticated()
                    }
                  >
                    {isSubmitting && <Spinner className="mr-2 h-4 w-4" />}
                    Save Configuration
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Success/Error Messages */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}
    </div>
  );
};
