
import React from 'react';
import { Link } from 'react-router-dom';
import WarningIcon from '../components/icons/WarningIcon';

const NoPermissionPage: React.FC = () => {
  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-900 p-4">
      <div className="w-full max-w-md mx-auto bg-slate-800 rounded-2xl shadow-2xl p-8 border border-slate-700 text-center">
        <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-500/20 mb-6">
          <WarningIcon className="h-10 w-10 text-red-400" />
        </div>
        <h1 className="text-3xl font-bold text-white">Access Denied</h1>
        <p className="text-slate-400 mt-2 mb-8">
          Authentication failed or you do not have permission to access this page. Please try signing in again.
        </p>
        <Link
          to="/login"
          className="inline-block bg-sky-600 hover:bg-sky-700 text-white font-bold py-3 px-6 rounded-lg transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-opacity-50"
        >
          Return to Login
        </Link>
      </div>
    </div>
  );
};

export default NoPermissionPage;
