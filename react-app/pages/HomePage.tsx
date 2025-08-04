
import React, { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { AuthContextType } from '../types';

const HomePage: React.FC = () => {
  const auth = useContext(AuthContext) as AuthContextType;
  const { user, logout } = auth;

  console.log('HomePage: Rendering with user:', user ? 'present' : 'missing');

  if (!user) {
    console.log('HomePage: No user data, showing loading state');
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto"></div>
          <p className="mt-4 text-slate-400">Loading your profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-slate-900">
        <div className="w-full max-w-md mx-auto bg-slate-800 rounded-2xl shadow-2xl p-8 border border-slate-700 text-center">
            <img 
                src={user.picture} 
                alt="Profile" 
                className="w-24 h-24 rounded-full mx-auto mb-4 border-4 border-slate-600 shadow-lg" 
            />
            <h1 className="text-2xl font-bold text-white">Welcome, {user.name}!</h1>
            <p className="text-slate-400 mt-2">{user.email}</p>

            <div className="mt-8 text-left bg-slate-900/50 p-4 rounded-lg border border-slate-700">
                <h3 className="text-lg font-semibold text-sky-400 mb-3">Profile Details</h3>
                <ul className="text-sm space-y-2 text-slate-300">
                    <li><strong>First Name:</strong> {user.given_name || 'Not provided'}</li>
                    <li><strong>Last Name:</strong> {user.family_name || 'Not provided'}</li>
                    <li><strong>User ID:</strong> <span className="break-all">{user.id}</span></li>
                    <li><strong>Account Status:</strong> {user.is_active ? 'Active' : 'Inactive'}</li>
                    <li><strong>Member Since:</strong> {new Date(user.created_at).toLocaleDateString()}</li>
                </ul>
            </div>

            <button
                onClick={logout}
                className="mt-8 w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-4 rounded-lg transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50"
            >
                Logout
            </button>
        </div>
        <footer className="text-center text-slate-500 text-xs mt-8">
             <p>&copy; {new Date().getFullYear()} SSO App. All rights reserved.</p>
        </footer>
    </div>
  );
};

export default HomePage;
