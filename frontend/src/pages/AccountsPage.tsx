import React, { useState, useEffect, useContext } from 'react';
import { usePlaidLink } from 'react-plaid-link';
import { AuthContext } from '../context/AuthContext';
import {
  useAccountsQuery,
  useCreateLinkTokenMutation,
  useExchangePublicTokenMutation,
  useItemsQuery,
  useRevokeItemMutation,
  useRevokeAllItemsMutation,
} from '../hooks/usePlaidApi';
import { usePlaidConnectionFlow } from '../hooks/usePlaidConnectionFlow';
import { usePlaidConfigStatus } from '../hooks/usePlaidConfigStatus';
import type { AuthContextType } from '@/types/types';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { MultiStepLoader } from '@/components/ui/multi-step-loader';
import { AccountsSummary } from '@/components/custom/accounts/accounts-summary';
import { AccountsHeader } from '@/components/custom/accounts/accounts-header';
import { AccountsDisplay } from '@/components/custom/accounts/accounts-display';
import { ConfirmationDialog } from '@/components/custom/accounts/confirmation-dialog';
import { FeatureNotAvailable } from '@/components/custom/FeatureNotAvailable';

const AccountsPage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const { user } = auth || {};

  // Check Plaid configuration status
  const { data: plaidConfigStatus, isLoading: isConfigLoading } = usePlaidConfigStatus();

  // State
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'ready' | 'success' | 'error'>(
    'idle',
  );
  const [showConfirmDialog, setShowConfirmDialog] = useState<{
    type: 'single' | 'all';
    bankName?: string;
    itemId?: string;
  } | null>(null);

  // Multi-step loader hook
  const {
    currentStep,
    isLoading: isFlowLoading,
    plaidConnectionSteps,
    startFlow,
    completeFlow,
    resetFlow,
    handlePlaidEvent,
    updateStep,
  } = usePlaidConnectionFlow();

  // TanStack Query hooks
  const {
    data: accountsData,
    isLoading,
    error: accountsError,
    isError: isAccountsError,
  } = useAccountsQuery();

  const createLinkTokenMutation = useCreateLinkTokenMutation();
  const exchangePublicTokenMutation = useExchangePublicTokenMutation();

  // Derived data
  const accounts = accountsData?.accounts || [];
  const institutions = accountsData?.institutions || [];
  const { data: itemsData } = useItemsQuery((accounts.length > 0) || (institutions.length > 0));

  const revokeItemMutation = useRevokeItemMutation();
  const revokeAllItemsMutation = useRevokeAllItemsMutation();

  const isConnecting = createLinkTokenMutation.isPending || exchangePublicTokenMutation.isPending;
  const errorMessage = isAccountsError
    ? `Failed to load accounts: ${accountsError?.message}`
    : createLinkTokenMutation.error?.message
    ? `Failed to initialize bank connection: ${createLinkTokenMutation.error.message}`
    : exchangePublicTokenMutation.error?.message
    ? `Failed to connect your bank account: ${exchangePublicTokenMutation.error.message}`
    : '';

  // Helper functions
  const getItemIdForBank = (bankName: string): string | null => {
    console.log('Looking for bank:', bankName);
    console.log('ItemsData:', itemsData);
    
    // Handle the nested structure from the backend GetBanksResponse
    if (itemsData?.banks) {
      console.log('Using banks field from API response');
      const banks = itemsData.banks.map(bankInfo => ({
        institution_name: bankInfo.item.institution_name,
        item_id: bankInfo.item.item_id
      }));
      console.log('Available banks:', banks);
      const bank = banks.find(b => b.institution_name === bankName);
      console.log('Found bank:', bank);
      return bank?.item_id || null;
    }
    
    // Fallback for legacy flat structure
    if (itemsData?.items) {
      console.log('Using legacy items field');
      const item = itemsData.items.find((item) => item.institution_name === bankName);
      console.log('Found item:', item);
      return item?.item_id || null;
    }
    
    console.warn('No items data found in either banks or items field:', itemsData);
    return null;
  };

  const initializePlaidConnection = async () => {
    setConnectionStatus('idle');
    startFlow(); // Start the multi-step loader

    try {
      updateStep(0); // Initializing secure connection
      const token = await createLinkTokenMutation.mutateAsync();
      setLinkToken(token);
      setConnectionStatus('ready');
    } catch (err) {
      console.error('Error fetching Plaid link token:', err);
      setConnectionStatus('error');
      resetFlow(); // Reset the loader on error
    }
  };

  const handleUnlinkBank = async (bankName: string, itemId?: string) => {
    const finalItemId = itemId || getItemIdForBank(bankName);
    if (!finalItemId) {
      console.error('Could not find item_id for bank:', bankName);
      return;
    }

    try {
      await revokeItemMutation.mutateAsync(finalItemId);
      setShowConfirmDialog(null);
    } catch (error) {
      console.error('Failed to unlink bank:', error);
    }
  };

  const handleUnlinkAllBanks = async () => {
    console.log('handleUnlinkAllBanks called');
    try {
      console.log('Attempting to revoke all items...');
      const result = await revokeAllItemsMutation.mutateAsync();
      console.log('Successfully revoked all items:', result);
      setShowConfirmDialog(null);
    } catch (error) {
      console.error('Failed to unlink all banks:', error);
    }
  };

  const { open, ready } = usePlaidLink({
    token: linkToken || '',
    onSuccess: async (publicToken: string, _metadata: any) => {
      try {
        updateStep(4); // Syncing account information
        await exchangePublicTokenMutation.mutateAsync(publicToken);
        completeFlow(); // Complete the flow
        setConnectionStatus('success');
      } catch (err) {
        console.error('Plaid onSuccess error:', err);
        setConnectionStatus('error');
        resetFlow();
      }
    },
    onExit: (err) => {
      if (err) {
        console.error('Plaid Link exited with error:', err);
        setConnectionStatus('error');
      }
      resetFlow(); // Reset the loader when user exits
    },
    onEvent: (eventName: string, metadata: any) => {
      handlePlaidEvent(eventName, metadata);
    },
    onLoad: () => {
      updateStep(1); // Opening Plaid Link
    },
  });

  useEffect(() => {
    if (linkToken && ready && connectionStatus === 'ready') {
      setConnectionStatus('idle');
      open();
    }
  }, [linkToken, ready, connectionStatus, open]);

  // Auth check
  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle>Authentication Required</CardTitle>
            <CardDescription>Please log in to access your bank accounts.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => (window.location.href = '/login')} className="w-full">
              Go to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Loading state
  if (isLoading || isConfigLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center space-y-4 py-8">
            <Spinner />
            <p className="text-muted-foreground">
              {isConfigLoading ? 'Checking configuration...' : 'Loading your accounts...'}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Check if Plaid is configured
  if (!plaidConfigStatus?.is_configured) {
    return (
      <FeatureNotAvailable
        featureName="Bank Accounts"
        title="Bank Account Integration Not Available"
        description="Plaid integration is not configured. Please add your Plaid credentials in Settings to connect your bank accounts and view financial data."
        actionLabel="Configure Plaid Settings"
        actionPath="/settings"
      />
    );
  }

  // Main render following HomePage pattern
  return (
    <>
      {/* Multi-Step Loader */}
      <MultiStepLoader
        loadingStates={plaidConnectionSteps}
        loading={isFlowLoading}
        currentStep={currentStep}
        loop={false}
        showCloseButton={true}
        onClose={resetFlow}
      />

      <div className="flex flex-1 flex-col">
        <div className="@container/main flex flex-1 flex-col gap-2">
          <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
            <AccountsHeader
              onConnectBank={initializePlaidConnection}
              onDisconnectAll={() => setShowConfirmDialog({ type: 'all' })}
              isConnecting={isConnecting}
              hasAccounts={(institutions.length > 0) || (accounts.length > 0)}
              isDisconnecting={revokeAllItemsMutation.isPending}
              errorMessage={errorMessage}
              onRefreshSuccess={() => {
                // Optionally trigger any additional actions after refresh
                console.log('Account data refreshed successfully');
              }}
            />

            {accountsData && ((institutions.length > 0) || (accounts.length > 0)) && (
              <AccountsSummary
                totalAccounts={
                  accountsData.accounts_count || 
                  accountsData.account_count || 
                  institutions.reduce((sum, inst) => sum + inst.account_count, 0) ||
                  accounts.length
                }
                totalBalance={
                  institutions.reduce((sum, inst) => sum + inst.total_balance, 0) ||
                  accountsData.total_balance ||
                  accounts.reduce((sum, acc) => sum + (acc.balances.current || 0), 0)
                }
                connectedBanks={
                  accountsData.banks_count || 
                  institutions.length ||
                  Array.from(new Set(accounts.map((acc) => acc.institution_name).filter(Boolean))).length ||
                  Array.from(new Set(accounts.map((acc) => acc.name.split(' ')[0]))).length
                }
              />
            )}

            <AccountsDisplay
              institutions={institutions}
              accounts={accounts}
              onUnlinkBank={(bankName, itemId) =>
                setShowConfirmDialog({ type: 'single', bankName, itemId })
              }
              getItemIdForBank={getItemIdForBank}
              isRevoking={revokeItemMutation.isPending}
            />
          </div>
        </div>
      </div>

      <ConfirmationDialog
        isOpen={!!showConfirmDialog}
        type={showConfirmDialog?.type || 'single'}
        bankName={showConfirmDialog?.bankName}
        onConfirm={
          showConfirmDialog?.type === 'all'
            ? handleUnlinkAllBanks
            : () => handleUnlinkBank(showConfirmDialog?.bankName!, showConfirmDialog?.itemId)
        }
        onCancel={() => setShowConfirmDialog(null)}
        isLoading={revokeItemMutation.isPending || revokeAllItemsMutation.isPending}
      />
    </>
  );
};

export default AccountsPage;
