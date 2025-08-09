import { DataTable } from '@/components/chart-area-interactive';
import { ChartAreaInteractive } from '@/components/data-table';
import { SectionCards } from '@/components/section-cards';
import React, { useEffect, useState, useContext } from 'react';
import data from './data.json';
import type { AuthContextType } from '@/types/types';
import { AuthContext } from '@/context/AuthContext';

const LoginPage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const { user: authUser, logout } = auth || {};

  return (
    <>
      <div className="flex flex-1 flex-col">
        <div className="@container/main flex flex-1 flex-col gap-2">
          <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
            <SectionCards />
            <div className="px-4 lg:px-6">
              <ChartAreaInteractive />
            </div>
            <DataTable data={data} />
          </div>
        </div>
      </div>
    </>
  );
};

export default LoginPage;
