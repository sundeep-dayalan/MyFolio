# Environment Configuration

This React application uses environment-specific configuration files to manage different deployment environments.

## Environment Files

- `.env` - Default environment variables (checked into version control)
- `.env.local` - Local overrides (not checked into version control) 
- `.env.development` - Development environment configuration
- `.env.production` - Production environment configuration

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Base URL for the API server | `http://localhost:8000/api/v1` |
| `VITE_APP_ENV` | Application environment | `development` |

## Usage

All environment variables must be prefixed with `VITE_` to be accessible in the React application.

### In Code

```typescript
import config from '../config/env';

// Use the configuration
const apiUrl = config.apiBaseUrl;
const isProduction = config.isProduction;
```

## NPM Scripts

- `npm run dev` - Start development server with development environment
- `npm run dev:local` - Start development server with local environment
- `npm run build` - Build for production
- `npm run build:dev` - Build for development
- `npm run preview` - Preview production build
- `npm run preview:prod` - Preview production build with production environment

## Environment Precedence

Vite loads environment variables in the following order (higher priority overwrites lower):

1. `.env.{mode}.local`
2. `.env.local` 
3. `.env.{mode}`
4. `.env`

## Development vs Production

### Development
- Uses `http://localhost:8000/api/v1` for API calls
- Includes debug logging
- Hot module reloading enabled

### Production  
- Uses `https://myfolio-api-681015953939.us-central1.run.app/api/v1` for API calls
- Optimized build
- Debug logging disabled

## Adding New Environment Variables

1. Add the variable to the appropriate `.env` file(s) with `VITE_` prefix
2. Add the TypeScript type definition in `vite-env.d.ts`
3. Add the variable to `config/env.ts`
4. Use the variable via the config object

Example:

```typescript
// In .env.development
VITE_DEBUG_MODE=true

// In vite-env.d.ts
interface ImportMetaEnv {
  readonly VITE_DEBUG_MODE: string;
  // ... other variables
}

// In config/env.ts
export const config = {
  debugMode: import.meta.env.VITE_DEBUG_MODE === 'true',
  // ... other config
};
```
