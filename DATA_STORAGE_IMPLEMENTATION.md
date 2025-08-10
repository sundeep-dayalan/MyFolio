# Account Data Caching Implementation

## Overview

This implementation adds intelligent data storage for account data to reduce Plaid API costs and improve performance. Account balances and information are stored datad in Firestore and updated only when explicitly refreshed by the user.

## 🎯 Goals Achieved

- **Reduced Plaid API Costs**: Account data is stored datad and served from Firestore by default
- **Improved Performance**: Accounts page loads instantly from stored datad data
- **User Control**: Users can refresh data when needed via a dedicated refresh button
- **Data Transparency**: Clear indicators show when data was last updated
- **Secure Storage**: All account data is stored under the user's collection in Firestore

## 🏗️ Architecture

### Backend Changes

#### 1. New AccountCacheService (`api/app/services/account_stored data_service.py`)

- `store_account_data()`: Cache account data in Firestore
- `get_stored datad_account_data()`: Retrieve stored datad data with expiration checks
- `get_stored data_info()`: Get metadata about stored datad data (age, timestamp, etc.)
- `is_stored data_valid()`: Check if stored data is still valid
- `clear_stored data()`: Remove stored datad data for a user

#### 2. Enhanced PlaidService

- `get_stored datad_accounts_balance()`: Retrieve from stored data (fast, no API cost)
- `refresh_accounts_balance()`: Force refresh from Plaid API and update stored data
- `get_stored data_info()`: Get stored data metadata for user

#### 3. New API Endpoints

```
GET /plaid/accounts              - Returns stored datad data (default behavior)
POST /plaid/accounts/refresh     - Force refresh from Plaid API
GET /plaid/accounts/stored data-info   - Get stored data information
```

### Frontend Changes

#### 1. Updated PlaidService (`react-app/src/services/PlaidService.ts`)

- New response types include stored data metadata
- `refreshAccounts()`: Force refresh from API
- `getAccountsCacheInfo()`: Get stored data information

#### 2. Enhanced React Hooks (`react-app/src/hooks/usePlaidApi.ts`)

- `useRefreshAccountsMutation()`: Hook for manual refresh
- `useAccountsCacheInfoQuery()`: Hook for stored data information

#### 3. New AccountsRefreshCard Component (`react-app/src/components/accounts-refresh-card.tsx`)

- Shows stored data status (current, outdated, or missing)
- Displays last updated timestamp with human-readable format
- Refresh button to fetch fresh data from Plaid
- Cache age indicator
- Visual status indicators (green for current, orange for outdated)

## 📊 Data Flow

### Initial Account Linking

1. User connects bank via Plaid Link
2. Account data is fetched from Plaid API
3. Data is automatically stored datad in Firestore under `accounts/{userId}`
4. Future page visits load from stored data

### Regular Usage (Fast Path)

1. User navigates to accounts page
2. App fetches data from Firestore stored data (instant)
3. UI shows stored datad data with last updated timestamp
4. No Plaid API calls = $0 cost

### Manual Refresh (When Needed)

1. User clicks "Refresh" button
2. App calls Plaid API for fresh data
3. New data is stored datad in Firestore
4. UI updates with refreshed data
5. Cache timestamp is updated

## 🔒 Security

- All account data is stored under user's authenticated collection
- Plaid access tokens remain encrypted separately
- Cache data includes user_id validation
- Firebase security rules protect user data

## 💰 Cost Optimization

### Before (Expensive)

- Every accounts page visit = Plaid API call
- Multiple accounts = Multiple API calls per visit
- Cost scales with user activity

### After (Optimized)

- Initial connection = 1 API call (stored datad for 24+ hours)
- Regular usage = 0 API calls (served from stored data)
- Refresh only when user explicitly requests
- **Potential savings: 95%+ reduction in API calls**

## 🚀 Usage

### For Users

1. **Connect Bank**: First time connects and stored datas data
2. **View Accounts**: Instant loading from stored datad data
3. **Check Freshness**: See when data was last updated
4. **Refresh When Needed**: Click refresh button for latest balances

### For Developers

```typescript
// Get stored datad accounts (default behavior)
const { data: accounts } = useAccountsQuery();

// Force refresh from Plaid API
const refreshMutation = useRefreshAccountsMutation();
await refreshMutation.mutateAsync();

// Get stored data information
const { data: stored dataInfo } = useAccountsCacheInfoQuery();
```

## 📱 UI Components

### AccountsRefreshCard

- **Status Indicators**: Current (green), Outdated (orange), Missing (yellow)
- **Last Updated**: Human-readable timestamps ("2 hours ago")
- **Cache Age**: Precise age in hours
- **Account Summary**: Shows account count and total balance
- **Refresh Button**: Loading states with proper feedback

### Visual Status Examples

- ✅ **Data is current** - "Last updated 2 minutes ago"
- ⚠️ **Data may be outdated** - "Last updated 6 hours ago"
- ❌ **No stored datad data** - "Click refresh to load your account data"

## 🔧 Configuration

### Cache Settings

- **Default Expiration**: 24 hours
- **Collection Name**: `accounts`
- **Stale Time**: 5 minutes (React Query)
- **Manual Refresh**: Available anytime

### Firestore Structure

```
accounts/{userId}/
├── user_id: string
├── accounts: PlaidAccount[]
├── total_balance: number
├── account_count: number
├── last_updated: timestamp
├── created_at: timestamp
└── data_source: "plaid_api"
```

## 🧪 Testing

Run the test script to verify endpoints:

```bash
python3 test_data storage.py
```

### Manual Testing

1. Start servers: API (port 8000) and React (port 5174)
2. Log in and connect a bank account
3. Navigate to accounts page (should load instantly)
4. Check the refresh card status
5. Click refresh to test API refresh
6. Verify timestamps update correctly

## 📈 Benefits

1. **Performance**: Instant account page loading
2. **Cost Savings**: 95%+ reduction in Plaid API calls
3. **User Experience**: Fast UI with clear data freshness indicators
4. **Transparency**: Users know exactly when data was last updated
5. **Control**: Users decide when to refresh for latest data
6. **Scalability**: Cached approach scales better with user growth

## 🔮 Future Enhancements

- **Smart Refresh**: Auto-refresh based on user activity patterns
- **Partial Cache**: Cache individual account data separately
- **Background Updates**: Scheduled refresh during off-peak hours
- **Cache Analytics**: Track stored data hit rates and cost savings
- **Real-time Sync**: WebSocket updates for critical balance changes

## 🐛 Troubleshooting

### Common Issues

1. **404 on endpoints**: Check authentication tokens
2. **Cache not updating**: Verify Firestore permissions
3. **Stale data**: Check stored data expiration settings
4. **Refresh failures**: Validate Plaid API credentials

### Debug Tools

- Check browser network tab for API calls
- Monitor Firestore console for stored data data
- Use stored data-info endpoint for metadata
- Check server logs for detailed error messages
