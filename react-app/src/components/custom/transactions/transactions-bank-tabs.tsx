import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface TransactionsBankTabsProps {
  bankNames: string[];
  activeBankTab: string | null;
  onBankTabChange: (bankName: string) => void;
}

export const TransactionsBankTabs: React.FC<TransactionsBankTabsProps> = ({
  bankNames,
  activeBankTab,
  onBankTabChange,
}) => {
  if (bankNames.length === 0) return null;

  return (
    <div className="px-4 lg:px-6">
      <Tabs value={activeBankTab || ''} onValueChange={onBankTabChange}>
        <TabsList className="grid w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {bankNames.map((bankName) => (
            <TabsTrigger key={bankName} value={bankName} className="text-sm">
              {bankName}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
    </div>
  );
};
