'use client';

import type { ColumnDef } from '@tanstack/react-table';
import { ArrowUpDown, MoreHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { Transaction } from '@/services/CosmosDBService';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { TransactionDetailsModal } from './transaction-details-modal';
import { useState } from 'react';

// Actions Cell Component
function ActionsCell({ transaction }: { transaction: Transaction }) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-8 w-8 p-0">
            <span className="sr-only">Open menu</span>
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Actions</DropdownMenuLabel>
          <DropdownMenuItem
            onClick={() => navigator.clipboard.writeText(transaction.plaidTransactionId)}
          >
            Copy transaction ID
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setShowDetails(true)}>View details</DropdownMenuItem>
          <DropdownMenuItem>Categorize</DropdownMenuItem>
          <DropdownMenuItem>Add note</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <TransactionDetailsModal
        transaction={transaction}
        open={showDetails}
        onOpenChange={setShowDetails}
      />
    </>
  );
}

// Helper functions
const formatCurrency = (amount: number | null | undefined) => {
  if (amount == null || isNaN(Number(amount))) {
    return '$0.00';
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(Math.abs(Number(amount)));
};

const formatDate = (dateString: string | null | undefined) => {
  if (!dateString) {
    return 'No date';
  }

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch (error) {
    return 'Invalid date';
  }
};

const getTransactionTypeColor = (amount: number | null | undefined) => {
  if (amount == null || isNaN(Number(amount))) {
    return 'text-gray-500';
  }
  return Number(amount) > 0 ? 'text-red-600' : 'text-green-600';
};

export const columns: ColumnDef<Transaction>[] = [
  {
    id: 'select',
    header: ({ table }) => (
      <Checkbox
        checked={
          table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && 'indeterminate')
        }
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label="Select all"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Select row"
      />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: 'date',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Date
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => <div className="font-medium">{formatDate(row.getValue('date'))}</div>,
  },
  {
    accessorKey: 'description',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Description
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const transaction = row.original;
      const counterpartyName = transaction.counterparties?.[0]?.name;
      const counterpartyLogo = transaction.counterparties?.[0]?.logoUrl;

      return (
        <div className="flex items-center space-x-3">
          <Avatar className="h-8 w-8">
            {counterpartyLogo ? (
              <AvatarImage src={counterpartyLogo} alt={counterpartyName || 'Transaction'} />
            ) : (
              <div className="h-full w-full bg-slate-100 flex items-center justify-center">
                <svg
                  className="h-4 w-4 text-slate-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                  />
                </svg>
              </div>
            )}
            <AvatarFallback className="text-xs bg-slate-100 text-slate-600">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                />
              </svg>
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="font-medium">{transaction.description || 'Unknown Transaction'}</div>
            {counterpartyName && counterpartyName !== transaction.description && (
              <div className="text-sm text-muted-foreground">{counterpartyName}</div>
            )}
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: 'category',
    header: 'Category',
    cell: ({ row }) => {
      const transaction = row.original;
      const primaryCategory = transaction.category?.primary || 'Other';

      return (
        <div className="flex items-center space-x-2">
          <Avatar className="h-6 w-6">
            <div className="h-full w-full bg-slate-100 flex items-center justify-center">
              <svg
                className="h-3 w-3 text-slate-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                />
              </svg>
            </div>
            <AvatarFallback className="text-xs bg-slate-100 text-slate-600">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                />
              </svg>
            </AvatarFallback>
          </Avatar>
          <Badge variant="outline" className="capitalize">
            {primaryCategory.replace(/_/g, ' ').toLowerCase()}
          </Badge>
        </div>
      );
    },
  },
  {
    accessorKey: 'plaidAccountId',
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Account
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
    cell: ({ row }) => {
      const transaction = row.original;
      const accountId = transaction.plaidAccountId;

      return (
        <div>
          <div className="font-medium text-xs">{accountId.slice(-4)}</div>
          <div className="text-sm text-muted-foreground">Account</div>
        </div>
      );
    },
  },
  {
    accessorKey: 'amount',
    header: ({ column }) => {
      return (
        <div className="text-right">
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          >
            Amount
            <ArrowUpDown className="ml-2 h-4 w-4" />
          </Button>
        </div>
      );
    },
    cell: ({ row }) => {
      const rawAmount = row.getValue('amount');
      const amount = parseFloat(rawAmount as string) || 0;
      return (
        <div className={`text-right font-medium ${getTransactionTypeColor(amount)}`}>
          {amount > 0 ? '-' : '+'}
          {formatCurrency(amount)}
        </div>
      );
    },
  },
  {
    accessorKey: 'isPending',
    header: 'Status',
    cell: ({ row }) => {
      const pending = row.getValue('isPending') as boolean;
      return (
        <Badge variant={pending ? 'secondary' : 'default'}>{pending ? 'Pending' : 'Posted'}</Badge>
      );
    },
  },
  {
    id: 'actions',
    enableHiding: false,
    cell: ({ row }) => {
      const transaction = row.original;
      return <ActionsCell transaction={transaction} />;
    },
  },
];
