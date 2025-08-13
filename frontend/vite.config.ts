import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import path from 'path';
import tailwindcss from '@tailwindcss/vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      {
        find: '@/lib/utils',
        replacement: path.resolve(__dirname, './src/lib/utils.ts'),
      },
      {
        find: '@/lib/format',
        replacement: path.resolve(__dirname, './src/lib/format.ts'),
      },
      {
        find: '@',
        replacement: path.resolve(__dirname, './src'),
      },
    ],
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
  },
});
