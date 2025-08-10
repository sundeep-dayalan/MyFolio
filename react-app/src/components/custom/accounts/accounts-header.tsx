import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { IconPlus, IconTrash, IconAlertTriangle } from '@tabler/icons-react';
import AccountsRefreshCard from './accounts-refresh-card';

interface AccountsHeaderProps {
  onConnectBank: () => void;
  onDisconnectAll: () => void;
  isConnecting: boolean;
  hasAccounts: boolean;
  isDisconnecting: boolean;
  errorMessage?: string;
  onRefreshSuccess?: () => void;
}

export function AccountsHeader({
  onConnectBank,
  onDisconnectAll,
  isConnecting,
  hasAccounts,
  isDisconnecting,
  errorMessage,
  onRefreshSuccess,
}: AccountsHeaderProps) {
  return (
    <div className="px-4 lg:px-6 space-y-4">
      {/* Header Section */}
      <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
        <div>
          <h1 className="text-2xl font-bold">Bank Accounts</h1>
          <p className="text-muted-foreground">
            Manage your connected bank accounts and view balances
          </p>
        </div>
        <div className="flex items-center space-x-3">
          {hasAccounts && <AccountsRefreshCard onRefreshSuccess={onRefreshSuccess} />}
          <Button onClick={onConnectBank} disabled={isConnecting} size="sm">
            {isConnecting && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
            )}
            <IconPlus className="h-4 w-4 mr-2" />
            Connect Bank
          </Button>
          {hasAccounts && (
            <Button
              variant="outline"
              size="sm"
              onClick={onDisconnectAll}
              disabled={isDisconnecting}
            >
              <IconTrash className="h-4 w-4 mr-2" />
              Disconnect All
            </Button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {errorMessage && (
        <Card className="border-destructive/50 bg-destructive/10">
          <CardContent className="flex items-center space-x-2 py-4">
            <IconAlertTriangle className="h-4 w-4 text-destructive shrink-0" />
            <p className="text-sm text-destructive">{errorMessage}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
