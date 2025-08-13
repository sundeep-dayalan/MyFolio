import { IconBuildingBank, IconCreditCard, IconWallet } from '@tabler/icons-react';

import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

interface AccountsSummaryProps {
  totalAccounts: number;
  totalBalance: number;
  connectedBanks: number;
}

export function AccountsSummary({
  totalAccounts,
  totalBalance,
  connectedBanks,
}: AccountsSummaryProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  return (
    <div className="*:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-3">
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Total Accounts</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {totalAccounts}
          </CardTitle>
          <CardAction>
            <div className="p-2 bg-primary/10 rounded-lg">
              <IconBuildingBank className="h-4 w-4 text-primary" />
            </div>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Connected accounts <IconBuildingBank className="size-4" />
          </div>
          <div className="text-muted-foreground">Active bank connections</div>
        </CardFooter>
      </Card>

      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Total Balance</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl text-green-600">
            {formatCurrency(totalBalance)}
          </CardTitle>
          <CardAction>
            <div className="p-2 bg-green-500/10 rounded-lg">
              <IconWallet className="h-4 w-4 text-green-600" />
            </div>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium text-green-600">
            Current balance <IconWallet className="size-4" />
          </div>
          <div className="text-muted-foreground">Combined across all accounts</div>
        </CardFooter>
      </Card>

      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Connected Banks</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {connectedBanks}
          </CardTitle>
          <CardAction>
            <Badge variant="outline" className="bg-primary/5">
              <IconCreditCard className="h-3 w-3 mr-1" />
              Active
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Financial institutions <IconCreditCard className="size-4" />
          </div>
          <div className="text-muted-foreground">Securely connected</div>
        </CardFooter>
      </Card>
    </div>
  );
}
