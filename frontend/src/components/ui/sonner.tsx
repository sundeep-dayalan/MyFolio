'use client';

import { useTheme } from 'next-themes';
import { Toaster as Sonner, type ToasterProps } from 'sonner';

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = 'system' } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps['theme']}
      className="toaster group"
      style={
        {
          '--normal-bg': 'var(--popover)',
          '--normal-text': 'var(--popover-foreground)',
          '--normal-border': 'var(--border)',
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast:
            'group toast group-data-[collapsible=true]:group-data-[collapsed=false]:animate-none',
          title: '!text-black !font-bold !text-sm dark:!text-white',
          description: '!text-black !text-sm !opacity-100 dark:!text-gray-200 !text-opacity-100',
          actionButton:
            'group-data-[type=error]:!bg-red-500 group-data-[type=success]:!bg-green-500',
          cancelButton:
            'group-data-[type=error]:!bg-red-100 group-data-[type=success]:!bg-green-100',
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
