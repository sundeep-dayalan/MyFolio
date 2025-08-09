import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  IconBuildingBank,
  IconCreditCard,
  IconWallet,
  IconTrendingUp,
  IconUnlink,
} from '@tabler/icons-react';
import type { PlaidAccount } from '@/services/PlaidService';

interface AccountsDisplayProps {
  accounts: PlaidAccount[];
  onUnlinkBank: (bankName: string, itemId?: string) => void;
  getItemIdForBank: (bankName: string) => string | null;
  isRevoking: boolean;
}

export function AccountsDisplay({
  accounts,
  onUnlinkBank,
  getItemIdForBank,
  isRevoking,
}: AccountsDisplayProps) {
  const [viewMode, setViewMode] = useState<'all' | 'by-bank'>('all');

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const getAccountIcon = (type: string, subtype?: string) => {
    if (type === 'depository') {
      if (subtype === 'checking') return IconBuildingBank;
      if (subtype === 'savings') return IconWallet;
      return IconBuildingBank;
    }
    if (type === 'credit') return IconCreditCard;
    if (type === 'loan') return IconBuildingBank;
    if (type === 'investment') return IconTrendingUp;
    return IconBuildingBank;
  };

  const groupAccountsByBank = (accounts: PlaidAccount[]) => {
    const grouped: { [bankName: string]: PlaidAccount[] } = {};

    accounts.forEach((account) => {
      const bankName = account.institution_name || 'Unknown Bank';
      if (!grouped[bankName]) {
        grouped[bankName] = [];
      }
      grouped[bankName].push(account);
    });

    return grouped;
  };

  if (accounts.length === 0) {
    return (
      <div className="px-4 lg:px-6">
        <Card>
          <CardContent className="flex flex-col items-center text-center py-12">
            <div className="p-4 bg-muted rounded-full mb-4">
              <IconCreditCard className="h-8 w-8 text-muted-foreground" />
            </div>
            <CardTitle className="mb-2">No accounts connected</CardTitle>
            <CardDescription className="mb-6 max-w-md">
              Connect your first bank account to start managing your finances and tracking your
              balances.
            </CardDescription>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="px-4 lg:px-6">
      <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'all' | 'by-bank')}>
        <div className="flex items-center justify-between mb-6">
          <TabsList>
            <TabsTrigger value="all">All Accounts</TabsTrigger>
            <TabsTrigger value="by-bank">By Bank</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="all" className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {accounts.map((account) => {
              const IconComponent = getAccountIcon(account.type, account.subtype);
              return (
                <Card key={account.account_id} className="shadow-xs">
                  <CardHeader className="pb-3">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <IconComponent className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <CardTitle className="text-base truncate">{account.name}</CardTitle>
                        {account.institution_name && (
                          <CardDescription className="text-xs">
                            {account.institution_name}
                          </CardDescription>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-muted-foreground">Available</span>
                      <span className="font-medium">
                        {formatCurrency(account.balances.available || 0)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-muted-foreground">Current</span>
                      <span className="font-semibold text-green-600">
                        {formatCurrency(account.balances.current || 0)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground text-sm">Type</span>
                      <Badge variant="outline" className="text-xs">
                        {account.subtype || account.type}
                        {account.mask && ` •••• ${account.mask}`}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="by-bank" className="space-y-6">
          {Object.entries(groupAccountsByBank(accounts)).map(([bankName, bankAccounts]) => {
            const bankTotal = bankAccounts.reduce(
              (sum, acc) => sum + (acc.balances.current || 0),
              0,
            );

            return (
              <Card key={bankName} className="shadow-xs">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <IconBuildingBank className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{bankName}</CardTitle>
                        <CardDescription>
                          {bankAccounts.length} account{bankAccounts.length !== 1 ? 's' : ''}
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <p className="text-sm text-muted-foreground">Total Balance</p>
                        <p className="text-lg font-semibold text-green-600">
                          {formatCurrency(bankTotal)}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const itemId = getItemIdForBank(bankName);
                          if (itemId) {
                            onUnlinkBank(bankName, itemId);
                          }
                        }}
                        disabled={isRevoking}
                      >
                        <IconUnlink className="h-4 w-4 mr-2" />
                        Unlink
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {bankAccounts.map((account) => {
                      const IconComponent = getAccountIcon(account.type, account.subtype);
                      return (
                        <Card key={account.account_id} className="shadow-sm border-muted/40">
                          <CardHeader className="pb-3">
                            <div className="flex items-center space-x-3">
                              <div className="p-1.5 bg-primary/10 rounded">
                                <IconComponent className="h-4 w-4 text-primary" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <CardTitle className="text-sm truncate">{account.name}</CardTitle>
                                <CardDescription className="text-xs capitalize">
                                  {account.subtype || account.type}
                                  {account.mask && ` •••• ${account.mask}`}
                                </CardDescription>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-2">
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">Available</span>
                              <span className="font-medium">
                                {formatCurrency(account.balances.available || 0)}
                              </span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-muted-foreground">Current</span>
                              <span className="font-semibold text-green-600">
                                {formatCurrency(account.balances.current || 0)}
                              </span>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </TabsContent>
      </Tabs>
    </div>
  );
}
