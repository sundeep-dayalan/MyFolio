
import React from 'react';

const Spinner: React.FC = () => {
  return (
    <div
      className="animate-spin rounded-full h-12 w-12 border-b-2 border-t-2 border-sky-500"
      role="status"
      aria-label="loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};

export default Spinner;
