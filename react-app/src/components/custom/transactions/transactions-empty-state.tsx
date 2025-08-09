import { Card, CardContent, CardDescription, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { IconCreditCard, IconFileInvoice } from '@tabler/icons-react';

interface TransactionsEmptyStateProps {
  isLoading: boolean;
  hasError: boolean;
  hasTransactions: boolean;
  onGoToAccounts: () => void;
}

export const TransactionsEmptyState: React.FC<TransactionsEmptyStateProps> = ({
  isLoading,
  hasError,
  hasTransactions,
  onGoToAccounts,
}) => {
  if (isLoading) {
    return (
      <div className="px-4 lg:px-6">
        <Card>
          <CardContent className="flex flex-col items-center text-center py-12">
            <Spinner className="h-12 w-12 mb-4" />
            <p className="text-muted-foreground">Loading transactions...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="px-4 lg:px-6">
        <Card className="border-destructive/50 bg-destructive/10">
          <CardContent className="flex flex-col items-center text-center py-12">
            <div className="p-4 bg-destructive/20 rounded-full mb-4">
              <IconFileInvoice className="h-8 w-8 text-destructive" />
            </div>
            <CardTitle className="mb-2 text-destructive">Failed to load transactions</CardTitle>
            <CardDescription className="text-destructive/80">
              There was an error loading your transaction data. Please try again.
            </CardDescription>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!hasTransactions) {
    return (
      <div className="px-4 lg:px-6">
        <Card>
          <CardContent className="flex flex-col items-center text-center py-12">
            <div className="p-4 bg-muted rounded-full mb-4">
              <IconCreditCard className="h-8 w-8 text-muted-foreground" />
            </div>
            <CardTitle className="mb-2">No transactions found</CardTitle>
            <CardDescription className="mb-6 max-w-md">
              Connect your bank accounts to start viewing your transaction history and manage your
              finances.
            </CardDescription>
            <Button onClick={onGoToAccounts}>
              <IconCreditCard className="h-4 w-4 mr-2" />
              Connect Bank Accounts
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
};
