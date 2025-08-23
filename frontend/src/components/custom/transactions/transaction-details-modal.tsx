'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage } from '@/components/ui/avatar';
import type { Transaction } from '@/services/CosmosDBService';

interface TransactionDetailsModalProps {
  transaction: Transaction | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

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
    return 'No date available';
  }

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
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

export function TransactionDetailsModal({
  transaction,
  open,
  onOpenChange,
}: TransactionDetailsModalProps) {
  if (!transaction) return null;

  const amount = parseFloat(transaction.amount as any) || 0;
  const institutionName = transaction.institution_name || 'Unknown Bank';
  const logoUrl = transaction.logo_url;
  const categoryIconUrl = transaction.personal_finance_category_icon_url;
  const personalFinanceCategory = transaction.personal_finance_category?.primary;
  const categoryName =
    personalFinanceCategory ||
    (transaction.category && Array.isArray(transaction.category) && transaction.category.length > 0
      ? transaction.category[0]
      : 'Other');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-3">
            <Avatar className="h-10 w-10">
              {logoUrl ? (
                <AvatarImage src={logoUrl} alt={institutionName} />
              ) : (
                <div className="h-full w-full bg-slate-100 flex items-center justify-center">
                  <svg
                    className="h-5 w-5 text-slate-600"
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
            </Avatar>
            <div>
              <div className="font-semibold text-lg">
                {transaction.name || 'Unknown Transaction'}
              </div>
              <div className="text-sm text-muted-foreground">{institutionName}</div>
            </div>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Amount Section */}
          <div className="text-center py-6 bg-slate-50 rounded-lg">
            <div className={`text-4xl font-bold ${getTransactionTypeColor(amount)} mb-2`}>
              {amount > 0 ? '-' : '+'}
              {formatCurrency(amount)}
            </div>
            <Badge variant={transaction.pending ? 'secondary' : 'default'}>
              {transaction.pending ? 'Pending' : 'Posted'}
            </Badge>
          </div>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Column - Transaction Details */}
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-4 text-gray-900">Transaction Details</h3>
                <div className="space-y-4">
                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-600">Transaction ID</label>
                    <div className="text-sm font-mono bg-gray-50 p-3 rounded-md border text-gray-800 break-all">
                      {transaction.transaction_id || 'Unknown'}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-600">Date</label>
                    <p className="text-sm text-gray-800">{formatDate(transaction.date)}</p>
                  </div>

                  {transaction.authorized_date &&
                    transaction.authorized_date !== transaction.date && (
                      <div className="space-y-1">
                        <label className="text-sm font-medium text-gray-600">Authorized Date</label>
                        <p className="text-sm text-gray-800">
                          {formatDate(transaction.authorized_date)}
                        </p>
                      </div>
                    )}

                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-600">Merchant</label>
                    <p className="text-sm text-gray-800">
                      {transaction.merchant_name || 'Unknown Merchant'}
                    </p>
                  </div>

                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-600">Payment Channel</label>
                    <p className="text-sm text-gray-800 capitalize">
                      {transaction.payment_channel || 'Unknown'}
                    </p>
                  </div>

                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-600">Transaction Type</label>
                    <p className="text-sm text-gray-800 capitalize">
                      {transaction.transaction_type || 'Unknown'}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column - Account & Category */}
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-lg mb-4 text-gray-900">Account & Category</h3>
                <div className="space-y-4">
                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-600">Account</label>
                    <p className="text-sm text-gray-800">
                      {transaction.account_name || 'Unknown Account'}
                    </p>
                    <p className="text-xs text-gray-500 font-mono">
                      {transaction.account_id || 'Unknown ID'}
                    </p>
                  </div>

                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-600">Institution</label>
                    <p className="text-sm text-gray-800">{institutionName}</p>
                    <p className="text-xs text-gray-500">
                      {transaction.institution_id || 'Unknown ID'}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600">Category</label>
                    <div className="flex items-center space-x-2">
                      <Avatar className="h-6 w-6">
                        {categoryIconUrl ? (
                          <AvatarImage src={categoryIconUrl} alt={categoryName} />
                        ) : (
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
                        )}
                      </Avatar>
                      <Badge variant="outline" className="capitalize">
                        {(categoryName || 'Other').replace(/_/g, ' ').toLowerCase()}
                      </Badge>
                    </div>
                    {transaction.personal_finance_category?.detailed && (
                      <p className="text-xs text-gray-500 mt-1">
                        Detailed:{' '}
                        {transaction.personal_finance_category.detailed
                          .replace(/_/g, ' ')
                          .toLowerCase()}
                      </p>
                    )}
                    {transaction.personal_finance_category?.confidence_level && (
                      <p className="text-xs text-gray-500">
                        Confidence:{' '}
                        {transaction.personal_finance_category.confidence_level
                          .replace(/_/g, ' ')
                          .toLowerCase()}
                      </p>
                    )}
                  </div>

                  <div className="space-y-1">
                    <label className="text-sm font-medium text-gray-600">Currency</label>
                    <p className="text-sm text-gray-800">
                      {transaction.iso_currency_code ||
                        transaction.unofficial_currency_code ||
                        'USD'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Location Information */}
          {transaction.location &&
            Object.values(transaction.location).some((val) => val !== null) && (
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="font-semibold text-lg mb-3 text-gray-900">Location Information</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  {transaction.location.address && (
                    <div className="space-y-1">
                      <label className="font-medium text-gray-600">Address</label>
                      <p className="text-gray-800">{transaction.location.address}</p>
                    </div>
                  )}
                  {transaction.location.city && (
                    <div className="space-y-1">
                      <label className="font-medium text-gray-600">City</label>
                      <p className="text-gray-800">{transaction.location.city}</p>
                    </div>
                  )}
                  {transaction.location.region && (
                    <div className="space-y-1">
                      <label className="font-medium text-gray-600">Region</label>
                      <p className="text-gray-800">{transaction.location.region}</p>
                    </div>
                  )}
                  {transaction.location.postal_code && (
                    <div className="space-y-1">
                      <label className="font-medium text-gray-600">Postal Code</label>
                      <p className="text-gray-800">{transaction.location.postal_code}</p>
                    </div>
                  )}
                  {transaction.location.country && (
                    <div className="space-y-1">
                      <label className="font-medium text-gray-600">Country</label>
                      <p className="text-gray-800">{transaction.location.country}</p>
                    </div>
                  )}
                  {transaction.location.store_number && (
                    <div className="space-y-1">
                      <label className="font-medium text-gray-600">Store Number</label>
                      <p className="text-gray-800">{transaction.location.store_number}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

          {/* Payment Metadata */}
          {transaction.payment_meta &&
            Object.values(transaction.payment_meta).some((val) => val !== null) && (
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="font-semibold text-lg mb-3 text-gray-900">Payment Details</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  {transaction.payment_meta.reference_number && (
                    <div className="space-y-1">
                      <label className="font-medium text-gray-600">Reference Number</label>
                      <p className="font-mono text-gray-800 bg-white p-2 rounded border">
                        {transaction.payment_meta.reference_number}
                      </p>
                    </div>
                  )}
                  {transaction.payment_meta.ppd_id && (
                    <div className="space-y-1">
                      <label className="font-medium text-gray-600">PPD ID</label>
                      <p className="font-mono text-gray-800 bg-white p-2 rounded border">
                        {transaction.payment_meta.ppd_id}
                      </p>
                    </div>
                  )}
                  {transaction.payment_meta.payee && (
                    <div className="space-y-1">
                      <label className="font-medium text-gray-600">Payee</label>
                      <p className="text-gray-800">{transaction.payment_meta.payee}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

          {/* Additional Information */}
          {(transaction.account_owner ||
            transaction.check_number ||
            transaction.merchant_entity_id) && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold text-lg mb-3 text-gray-900">Additional Information</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                {transaction.account_owner && (
                  <div className="space-y-1">
                    <label className="font-medium text-gray-600">Account Owner</label>
                    <p className="text-gray-800">{transaction.account_owner}</p>
                  </div>
                )}
                {transaction.check_number && (
                  <div className="space-y-1">
                    <label className="font-medium text-gray-600">Check Number</label>
                    <p className="font-mono text-gray-800 bg-white p-2 rounded border">
                      {transaction.check_number}
                    </p>
                  </div>
                )}
                {transaction.merchant_entity_id && (
                  <div className="space-y-1">
                    <label className="font-medium text-gray-600">Merchant Entity ID</label>
                    <p className="font-mono text-xs text-gray-800 bg-white p-2 rounded border break-all">
                      {transaction.merchant_entity_id}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
