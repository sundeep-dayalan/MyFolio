import { useQuery } from '@tanstack/react-query';
import { PlaidConfigService } from '@/services/PlaidConfigService';

export const usePlaidConfigStatus = () => {
  return useQuery({
    queryKey: ['plaidConfigStatus'],
    queryFn: () => PlaidConfigService.getConfigurationStatus(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });
};