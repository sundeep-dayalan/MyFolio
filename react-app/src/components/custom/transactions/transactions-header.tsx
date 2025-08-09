import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { IconRefresh, IconAlertTriangle } from '@tabler/icons-react';

interface TransactionsHeaderProps {
  activeBankName: string | null;
  onRefreshBank: (bankName: string) => Promise<void>;
  isRefreshing: boolean;
  errorMessage?: string;
}

export const TransactionsHeader: React.FC<TransactionsHeaderProps> = ({
  activeBankName,
  onRefreshBank,
  isRefreshing,
  errorMessage,
}) => {
  return (
    <div className="px-4 lg:px-6 space-y-4">
      <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
        <div>
          <h1 className="text-2xl font-bold">Transactions</h1>
          <p className="text-muted-foreground">
            View and manage your transaction history across all connected accounts
          </p>
        </div>
        {activeBankName && (
          <div className="flex items-center space-x-2">
            <Button
              onClick={() => onRefreshBank(activeBankName)}
              disabled={isRefreshing}
              size="sm"
              variant="outline"
            >
              {isRefreshing ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
              ) : (
                <IconRefresh className="h-4 w-4 mr-2" />
              )}
              Refresh {activeBankName}
            </Button>
          </div>
        )}
      </div>

      {errorMessage && (
        <Card className="border-destructive/50 bg-destructive/10">
          <CardContent className="flex items-center space-x-2 py-4">
            <IconAlertTriangle className="h-4 w-4 text-destructive" />
            <p className="text-sm text-destructive">{errorMessage}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
