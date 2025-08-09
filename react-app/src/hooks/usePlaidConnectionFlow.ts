import { useState, useCallback, useRef, useEffect } from 'react';
import type { LoadingState } from '@/components/ui/multi-step-loader';

export const usePlaidConnectionFlow = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const plaidConnectionSteps: LoadingState[] = [
    { text: 'Initializing secure connection...' },
    { text: 'Opening Plaid Link...' },
    { text: 'Waiting for institution selection...' },
    { text: 'Validating credentials...' },
    { text: 'Syncing account information...' },
    { text: 'Connection complete!' },
  ];

  const updateStep = useCallback(
    (step: number) => {
      setCurrentStep(Math.min(step, plaidConnectionSteps.length - 1));
    },
    [plaidConnectionSteps.length],
  );

  const nextStep = useCallback(() => {
    setCurrentStep((prev) => Math.min(prev + 1, plaidConnectionSteps.length - 1));
  }, [plaidConnectionSteps.length]);

  const resetFlow = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setCurrentStep(0);
    setIsLoading(false);
  }, []);

  const startFlow = useCallback(() => {
    setIsLoading(true);
    setCurrentStep(0);
  }, []);

  const completeFlow = useCallback(() => {
    setCurrentStep(plaidConnectionSteps.length - 1);
    // Auto-close after showing completion message
    timeoutRef.current = setTimeout(() => {
      setIsLoading(false);
    }, 2000);
  }, [plaidConnectionSteps.length]);

  // Map Plaid events to steps
  const handlePlaidEvent = useCallback(
    (eventName: string, metadata?: any) => {
      console.log('Plaid Event:', eventName, metadata);

      switch (eventName) {
        case 'OPEN':
          updateStep(1); // Opening Plaid Link
          break;
        case 'SELECT_INSTITUTION':
        case 'SEARCH_INSTITUTION':
          updateStep(2); // Waiting for institution selection
          break;
        case 'SUBMIT_CREDENTIALS':
          updateStep(3); // Validating credentials
          break;
        case 'SUBMIT_MFA':
          updateStep(3); // Still validating credentials with MFA
          break;
        case 'HANDOFF':
        case 'TRANSITION_VIEW':
          if (metadata?.view_name === 'CONNECTED' || metadata?.view_name === 'SELECT_ACCOUNT') {
            updateStep(4); // Syncing account information
          }
          break;
        default:
          // Handle other events if needed
          break;
      }
    },
    [updateStep],
  );

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    currentStep,
    isLoading,
    plaidConnectionSteps,
    startFlow,
    completeFlow,
    resetFlow,
    handlePlaidEvent,
    updateStep,
    nextStep,
  };
};
