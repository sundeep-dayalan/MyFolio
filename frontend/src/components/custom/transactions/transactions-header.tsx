import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
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
import { Check, ChevronDown } from 'lucide-react';
import { IconRefresh, IconAlertTriangle } from '@tabler/icons-react';
import { cn } from '@/lib/utils';

interface TransactionsHeaderProps {
  activeBankName: string | null;
  availableBanks: string[];
  onBankChange: (bankName: string | null) => void;
  onRefreshBank: (bankName: string) => Promise<void>;
  isRefreshing: boolean;
  onForceRefreshBank?: (bankName: string) => Promise<void>;
  isForceRefreshing?: boolean;
  errorMessage?: string;
  transactionType: 'posted' | 'pending' | 'removed' | 'all';
  onTransactionTypeChange: (type: 'posted' | 'pending' | 'removed' | 'all') => void;
}

export const TransactionsHeader: React.FC<TransactionsHeaderProps> = ({
  activeBankName,
  availableBanks,
  onBankChange,
  onRefreshBank,
  isRefreshing,
  onForceRefreshBank,
  isForceRefreshing,
  errorMessage,
  transactionType,
  onTransactionTypeChange,
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

        <div className="flex items-center space-x-2">
          {/* Transaction Type Selector */}
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="justify-between min-w-[120px]">
                {transactionType.charAt(0).toUpperCase() + transactionType.slice(1)}
                <ChevronDown className="ml-2 h-4 w-4" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[160px] p-0" align="end">
              <div className="p-1">
                {(['posted', 'pending', 'removed', 'all'] as const).map((type) => (
                  <button
                    key={type}
                    className={cn(
                      'w-full flex items-center px-2 py-2 text-sm rounded-sm hover:bg-accent hover:text-accent-foreground',
                      transactionType === type && 'bg-accent',
                    )}
                    onClick={() => onTransactionTypeChange(type)}
                  >
                    <Check
                      className={cn(
                        'mr-2 h-4 w-4',
                        transactionType === type ? 'opacity-100' : 'opacity-0',
                      )}
                    />
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </button>
                ))}
              </div>
            </PopoverContent>
          </Popover>

          {/* Bank Selector */}
          {availableBanks.length > 0 && (
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" size="sm" className="justify-between min-w-[160px]">
                  {activeBankName || 'Select Bank'}
                  <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[200px] p-0" align="end">
                <div className="p-1">
                  {/* Option for All Banks */}
                  <button
                    className={cn(
                      'w-full flex items-center px-2 py-2 text-sm rounded-sm hover:bg-accent hover:text-accent-foreground',
                      !activeBankName && 'bg-accent',
                    )}
                    onClick={() => onBankChange(null)}
                  >
                    <Check
                      className={cn('mr-2 h-4 w-4', !activeBankName ? 'opacity-100' : 'opacity-0')}
                    />
                    All Banks
                  </button>

                  {/* Individual Banks */}
                  {availableBanks.map((bank) => (
                    <button
                      key={bank}
                      className={cn(
                        'w-full flex items-center px-2 py-2 text-sm rounded-sm hover:bg-accent hover:text-accent-foreground',
                        activeBankName === bank && 'bg-accent',
                      )}
                      onClick={() => onBankChange(bank)}
                    >
                      <Check
                        className={cn(
                          'mr-2 h-4 w-4',
                          activeBankName === bank ? 'opacity-100' : 'opacity-0',
                        )}
                      />
                      {bank}
                    </button>
                  ))}
                </div>
              </PopoverContent>
            </Popover>
          )}

          {/* Refresh Button */}
          {activeBankName && (
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
          )}

          {/* Force Refresh Button with Confirmation */}
          {activeBankName && onForceRefreshBank && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  disabled={isRefreshing || isForceRefreshing}
                  size="sm"
                  variant="destructive"
                >
                  {isForceRefreshing ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
                  ) : (
                    <IconRefresh className="h-4 w-4 mr-2" />
                  )}
                  Force Refresh
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Force Refresh Transactions</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will delete all existing transaction data for {activeBankName} and perform
                    a complete resync from your bank. This action cannot be undone. Are you sure you
                    want to continue?
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => onForceRefreshBank(activeBankName)}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    Force Refresh
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
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
