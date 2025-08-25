import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Settings, AlertCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface FeatureNotAvailableProps {
  title?: string;
  description?: string;
  featureName: string;
  actionLabel?: string;
  actionPath?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function FeatureNotAvailable({
  title,
  description,
  featureName,
  actionLabel = "Go to Settings",
  actionPath = "/settings",
  icon,
  className = "",
}: FeatureNotAvailableProps) {
  const navigate = useNavigate();

  const defaultTitle = title || `${featureName} Not Available`;
  const defaultDescription = description || 
    `This feature is not activated. Please configure the required settings to access ${featureName.toLowerCase()}.`;

  return (
    <div className={`flex items-center justify-center min-h-[400px] p-4 ${className}`}>
      <Card className="max-w-md w-full p-6">
        <Alert>
          <div className="flex items-center gap-3 mb-4">
            {icon || <AlertCircle className="h-5 w-5" />}
            <AlertTitle className="text-lg font-semibold">
              {defaultTitle}
            </AlertTitle>
          </div>
          <AlertDescription className="mb-4 text-muted-foreground">
            {defaultDescription}
          </AlertDescription>
          <Button 
            onClick={() => navigate(actionPath)}
            className="w-full"
            variant="default"
          >
            <Settings className="mr-2 h-4 w-4" />
            {actionLabel}
          </Button>
        </Alert>
      </Card>
    </div>
  );
}