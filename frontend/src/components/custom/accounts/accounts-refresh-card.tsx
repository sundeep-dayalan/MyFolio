import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { RefreshCw } from 'lucide-react';
import { useAccountsDataInfoQuery, useRefreshAccountsMutation } from '@/hooks/usePlaidApi';
import { toast } from 'sonner';

interface AccountsRefreshCardProps {
  onRefreshSuccess?: () => void;
}

const AccountsRefreshCard: React.FC<AccountsRefreshCardProps> = ({ onRefreshSuccess }) => {
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Get data information
  const {
    data: dataInfo,
    isLoading: isDataInfoLoading,
    refetch: refetchDataInfo,
  } = useAccountsDataInfoQuery();

  // Refresh mutation
  const refreshAccountsMutation = useRefreshAccountsMutation();

  const handleRefresh = async () => {
    try {
      setIsRefreshing(true);

      const result = await refreshAccountsMutation.mutateAsync();

      // Refetch data info to get updated timestamp
      await refetchDataInfo();

      toast.success('Account data refreshed successfully!', {
        description: `Updated ${result.account_count} accounts with latest balances`,
      });

      onRefreshSuccess?.();
    } catch (error) {
      toast.error('Failed to refresh account data', {
        description: error instanceof Error ? error.message : 'Please try again',
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  const formatLastUpdated = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffMins = Math.floor(diffMs / (1000 * 60));

      if (diffMins < 1) {
        return 'Just now';
      } else if (diffMins < 60) {
        return `${diffMins}m ago`;
      } else if (diffHours < 24) {
        return `${diffHours}h ago`;
      } else {
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
      }
    } catch {
      return 'Unknown';
    }
  };

  if (isDataInfoLoading) {
    return (
      <div className="flex items-center space-x-2 text-sm text-muted-foreground">
        <Spinner className="h-4 w-4" />
        <span>Loading...</span>
      </div>
    );
  }

  // Show refresh button with last updated info if data exists
  const hasData = dataInfo?.has_data;
  const lastUpdated = hasData ? formatLastUpdated(dataInfo.last_updated!) : null;

  return (
    <div className="flex items-center space-x-2">
      {hasData && lastUpdated && (
        <span className="text-xs text-muted-foreground">Updated {lastUpdated}</span>
      )}

      <Button
        onClick={handleRefresh}
        disabled={isRefreshing}
        size="sm"
        variant="outline"
        className="h-8 px-3"
      >
        {isRefreshing ? (
          <>
            <Spinner className="h-3 w-3 mr-1" />
            <span className="text-xs">Refreshing...</span>
          </>
        ) : (
          <>
            <RefreshCw className="h-3 w-3 mr-1" />
            <span className="text-xs">Refresh</span>
          </>
        )}
      </Button>
    </div>
  );
};

export default AccountsRefreshCard;
