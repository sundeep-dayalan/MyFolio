import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SecretsSection } from '@/components/custom/settings/SecretsSection';

const SettingsPage: React.FC = () => {
  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-2">Manage your account settings and preferences.</p>
      </div>

      <div className="flex gap-8">
        {/* Sidebar Navigation */}
        <div className="w-64 flex-shrink-0">
          <nav className="space-y-1">
            <div className="px-3 py-2">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Access
              </h3>
            </div>
            <a
              href="#secrets"
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md hover:bg-muted transition-colors"
            >
              Secrets
            </a>
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1">
          <Tabs defaultValue="secrets" className="w-full">
            <TabsList className="grid w-full grid-cols-1 max-w-[200px]">
              <TabsTrigger value="secrets">Secrets</TabsTrigger>
            </TabsList>

            <TabsContent value="secrets" className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Secrets</CardTitle>
                  <CardDescription>
                    Secrets allow you to manage reusable configuration data. Secrets are encrypted
                    and are used for sensitive data.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <SecretsSection />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
