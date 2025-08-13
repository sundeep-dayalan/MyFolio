import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { PlaidTransaction } from '@/services/PlaidService';

interface TransactionsAccountTabsProps {
  activeBankName: string;
  accountsByBank: { [bankName: string]: any[] };
  activeAccountTabs: { [bankName: string]: string };
  transactionsByBankAndAccount: { [bankName: string]: { [accountId: string]: PlaidTransaction[] } };
  onAccountTabChange: (bankName: string, accountId: string) => void;
  getAccountName: (accountId: string) => string;
  formatCurrency: (amount: number) => string;
  formatDate: (dateString: string) => string;
  getCategoryIcon: (categories: string[]) => string;
  getTransactionTypeColor: (amount: number) => string;
}

export const TransactionsAccountTabs: React.FC<TransactionsAccountTabsProps> = ({
  activeBankName,
  accountsByBank,
  activeAccountTabs,
  transactionsByBankAndAccount,
  onAccountTabChange,
  getAccountName,
  formatCurrency,
  formatDate,
  getCategoryIcon,
  getTransactionTypeColor,
}) => {
  const bankAccounts = accountsByBank[activeBankName] || [];
  const activeAccountId = activeAccountTabs[activeBankName];

  if (bankAccounts.length === 0) return null;

  const getGridColumns = (accountCount: number) => {
    if (accountCount === 1) return 'grid-cols-1';
    if (accountCount === 2) return 'grid-cols-2';
    if (accountCount === 3) return 'grid-cols-3';
    if (accountCount === 4) return 'grid-cols-4';
    if (accountCount === 5) return 'grid-cols-5';
    if (accountCount === 6) return 'grid-cols-6';
    return 'grid-cols-6'; // Max 6 columns, then wrap
  };

  return (
    <div className="px-4 lg:px-6">
      <Tabs
        value={activeAccountId || ''}
        onValueChange={(accountId) => onAccountTabChange(activeBankName, accountId)}
      >
        <TabsList className={`grid w-full ${getGridColumns(bankAccounts.length)}`}>
          {bankAccounts.map((account) => (
            <TabsTrigger key={account.account_id} value={account.account_id} className="text-xs">
              {account.name} ({account.subtype})
            </TabsTrigger>
          ))}
        </TabsList>

        {bankAccounts.map((account) => (
          <TabsContent key={account.account_id} value={account.account_id}>
            {activeAccountId === account.account_id &&
              transactionsByBankAndAccount[activeBankName]?.[account.account_id] && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">
                      {getAccountName(account.account_id)} Transactions
                    </CardTitle>
                    <CardDescription>
                      {transactionsByBankAndAccount[activeBankName][account.account_id].length}{' '}
                      transactions
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {transactionsByBankAndAccount[activeBankName][account.account_id].map(
                      (transaction) => (
                        <div
                          key={transaction.transaction_id}
                          className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                        >
                          <div className="flex items-center space-x-4">
                            <div className="text-2xl">
                              {getCategoryIcon(transaction.category || [])}
                            </div>
                            <div>
                              <p className="font-medium">{transaction.name}</p>
                              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                                <span>{formatDate(transaction.date)}</span>
                                {transaction.category && transaction.category[0] && (
                                  <>
                                    <span>•</span>
                                    <span>{transaction.category[0]}</span>
                                  </>
                                )}
                                {transaction.pending && (
                                  <>
                                    <span>•</span>
                                    <Badge variant="outline" className="text-yellow-600">
                                      Pending
                                    </Badge>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                          <div
                            className={`text-lg font-semibold ${getTransactionTypeColor(
                              transaction.amount,
                            )}`}
                          >
                            {transaction.amount > 0 ? '-' : '+'}
                            {formatCurrency(transaction.amount)}
                          </div>
                        </div>
                      ),
                    )}
                  </CardContent>
                </Card>
              )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
};
