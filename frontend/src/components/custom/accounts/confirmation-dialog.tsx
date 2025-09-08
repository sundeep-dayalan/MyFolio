import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { IconAlertTriangle } from '@tabler/icons-react';

interface ConfirmationDialogProps {
  isOpen: boolean;
  type: 'single' | 'all';
  bankName?: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
}

export function ConfirmationDialog({
  isOpen,
  type,
  bankName,
  onConfirm,
  onCancel,
  isLoading,
}: ConfirmationDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm">
      <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 p-4">
        <Card className="shadow-xl">
          <CardHeader>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-destructive/10 rounded-full">
                <IconAlertTriangle className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <CardTitle>
                  {type === 'all'
                    ? 'Disconnect All Banks?'
                    : `Disconnect ${bankName}?`}
                </CardTitle>
                <CardDescription className="mt-1">
                  {type === 'all'
                    ? 'This will permanently disconnect all your bank connections. You will need to reconnect them to access your account data again.'
                    : `This will permanently disconnect ${bankName} from your account. You will need to reconnect it to access this bank's data again.`}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex justify-end space-x-2 pt-4">
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                console.log('Confirmation button clicked');
                onConfirm();
              }}
              disabled={isLoading}
            >
              {isLoading ? 'Disconnecting...' : 'Yes, Disconnect'}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
