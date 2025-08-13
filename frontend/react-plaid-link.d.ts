declare module 'react-plaid-link' {
  import React from 'react';

  export interface UsePlaidLinkOptions {
    token: string;
    onSuccess: (publicToken: string, metadata: any) => void;
    onExit?: (error: Error | null, metadata: any) => void;
    onEvent?: (eventName: string, metadata: any) => void;
    onLoad?: () => void;
  }

  export function usePlaidLink(options: UsePlaidLinkOptions): {
    open: () => void;
    ready: boolean;
  };
}
