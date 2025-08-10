import { useState, useCallback, useRef, useEffect } from 'react';
import type { LoadingState } from '@/components/ui/multi-step-loader';

export const usePlaidConnectionFlow = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const plaidConnectionSteps: LoadingState[] = [
    { text: 'Initializing secure connection...' },
    { text: 'Loading Plaid Link interface...' },
    { text: 'Selecting your bank...' },
    { text: 'Authenticating with your bank...' },
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

        // Phone verification events (Layer flow)
        case 'SUBMIT_PHONE':
        case 'VERIFY_PHONE':
        case 'SUBMIT_OTP':
          updateStep(2); // Waiting for institution selection (phone verification step)
          break;

        // Institution selection events
        case 'SELECT_INSTITUTION':
        case 'SEARCH_INSTITUTION':
        case 'MATCHED_SELECT_INSTITUTION':
          updateStep(2); // Waiting for institution selection
          break;

        // Authentication events
        case 'SUBMIT_CREDENTIALS':
        case 'OPEN_OAUTH':
        case 'CLOSE_OAUTH':
          updateStep(3); // Validating credentials
          break;

        // MFA and additional verification
        case 'SUBMIT_MFA':
        case 'SUBMIT_ACCOUNT_NUMBER':
        case 'SUBMIT_ROUTING_NUMBER':
          updateStep(3); // Still validating credentials with additional info
          break;

        // Connection completion events
        case 'HANDOFF':
          updateStep(4); // Syncing account information
          break;

        // View transitions - handle based on view name
        case 'TRANSITION_VIEW':
          if (metadata?.view_name) {
            const viewName = metadata.view_name;
            switch (viewName) {
              case 'CONSENT':
              case 'DATA_TRANSPARENCY':
              case 'DATA_TRANSPARENCY_CONSENT':
                updateStep(1); // Still in opening phase
                break;
              case 'SELECT_INSTITUTION':
                updateStep(2); // Institution selection
                break;
              case 'CREDENTIAL':
              case 'MFA':
              case 'OAUTH':
                updateStep(3); // Validating credentials
                break;
              case 'SELECT_ACCOUNT':
              case 'CONNECTED':
                updateStep(4); // Syncing account information
                break;
              case 'LOADING':
                // Keep current step during loading
                break;
              default:
                console.log('Unhandled TRANSITION_VIEW:', viewName);
                break;
            }
          }
          break;

        // Error handling
        case 'ERROR':
          console.warn('Plaid error event:', metadata);
          // Don't change step on error, let user handle it
          break;

        // Exit events
        case 'EXIT':
          console.log('Plaid exit event:', metadata);
          // Reset will be handled by onExit callback
          break;

        // Other events that don't require step changes
        case 'LAYER_READY':
        case 'LAYER_NOT_AVAILABLE':
        case 'VIEW_DATA_TYPES':
        case 'UPLOAD_DOCUMENTS':
        case 'IDENTITY_VERIFICATION_START_STEP':
        case 'IDENTITY_VERIFICATION_PASS_STEP':
        case 'IDENTITY_VERIFICATION_FAIL_STEP':
          // These events don't require step progression changes
          console.log('Informational Plaid event:', eventName, metadata);
          break;

        default:
          // Log unhandled events for debugging
          console.log('Unhandled Plaid event:', eventName, metadata);
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
