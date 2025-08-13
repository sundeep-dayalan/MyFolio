import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { RefreshCw, Clock, AlertTriangle, CheckCircle } from 'lucide-react';
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
        return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
      } else if (diffHours < 24) {
        return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
      } else {
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
      }
    } catch {
      return 'Unknown';
    }
  };

  const getDataStatus = () => {
    if (!dataInfo?.has_data) {
      return {
        icon: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
        text: 'No stored data',
        description: 'Click refresh to load your account data',
        color: 'text-yellow-600',
      };
    }

    if (dataInfo.is_expired) {
      return {
        icon: <AlertTriangle className="h-4 w-4 text-orange-500" />,
        text: 'Data may be outdated',
        description: `Last updated ${formatLastUpdated(dataInfo.last_updated!)}`,
        color: 'text-orange-600',
      };
    }

    return {
      icon: <CheckCircle className="h-4 w-4 text-green-500" />,
      text: 'Data is current',
      description: `Last updated ${formatLastUpdated(dataInfo.last_updated!)}`,
      color: 'text-green-600',
    };
  };

  if (isDataInfoLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-6">
          <Spinner className="h-6 w-6" />
        </CardContent>
      </Card>
    );
  }

  const status = getDataStatus();

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {status.icon}
            <div>
              <CardTitle className={`text-sm font-medium ${status.color}`}>{status.text}</CardTitle>
              <CardDescription className="text-xs">{status.description}</CardDescription>
            </div>
          </div>

          <Button
            onClick={handleRefresh}
            disabled={isRefreshing}
            size="sm"
            variant="outline"
            className="flex items-center space-x-2"
          >
            {isRefreshing ? (
              <>
                <Spinner className="h-4 w-4" />
                <span>Refreshing...</span>
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                <span>Refresh</span>
              </>
            )}
          </Button>
        </div>
      </CardHeader>

      {dataInfo?.has_data && (
        <CardContent className="pt-0">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <div className="flex items-center space-x-1">
              <Clock className="h-3 w-3" />
              <span>
                Data age: {dataInfo.age_hours ? `${dataInfo.age_hours.toFixed(1)}h` : 'Unknown'}
              </span>
            </div>

            {(dataInfo.account_count ?? 0) > 0 && (
              <span>
                {dataInfo.account_count} accounts • $
                {dataInfo.total_balance?.toLocaleString('en-US', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </span>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
};

export { AccountsRefreshCard };
export default AccountsRefreshCard;
