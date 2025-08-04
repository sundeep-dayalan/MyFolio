# Firestore Index Management Guide

## 🔍 Understanding the Index Issue

The error you encountered indicates that Firestore requires a composite index for complex queries that combine:
- **Filtering** (e.g., `where("is_active", "==", True)`)
- **Ordering** (e.g., `order_by("created_at")`)

## 🛠️ Solutions Implemented

### 1. **Optimized Query Strategy**
The `UserService.get_users()` method now uses a fallback approach:

```python
# Primary: Filter by is_active first, then sort in memory
query = db.collection("users").where("is_active", "==", True).limit(limit + skip)

# Fallback: Order by created_at, filter in memory
query = db.collection("users").order_by("created_at").limit(limit + skip + 20)
```

### 2. **Index Requirements for Different Queries**

| Query Type | Index Required | Example |
|------------|----------------|---------|
| Single field filter | Single field index | `where("is_active", "==", True)` |
| Single field order | Single field index | `order_by("created_at")` |
| Filter + Order | Composite index | `where("is_active", "==", True).order_by("created_at")` |
| Multiple filters | Composite index | `where("is_active", "==", True).where("role", "==", "user")` |

## 📋 Firestore Index Management

### Automatic Indexes
Firestore automatically creates single-field indexes for:
- Each field in ascending order
- Each field in descending order

### Manual Composite Indexes
For complex queries, you need to create composite indexes:

#### Option 1: Via Firebase Console
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project: `fit-guide-465001-p3`
3. Navigate to Firestore Database
4. Go to "Indexes" tab
5. Click "Create Index"

#### Option 2: Via CLI (Recommended for Production)
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Initialize Firebase in your project
firebase init firestore

# Deploy indexes
firebase deploy --only firestore:indexes
```

#### Option 3: Programmatically Handle in Code
```python
# This is what we've implemented - design queries to avoid composite indexes
# or handle them gracefully with fallbacks
```

## 🏗️ Recommended Index Structure

For the Personal Wealth Management API, create these indexes:

### Users Collection
```javascript
// firestore.indexes.json
{
  "indexes": [
    {
      "collectionGroup": "users",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "is_active", "order": "ASCENDING"},
        {"fieldPath": "created_at", "order": "ASCENDING"}
      ]
    },
    {
      "collectionGroup": "users",
      "queryScope": "COLLECTION", 
      "fields": [
        {"fieldPath": "is_active", "order": "ASCENDING"},
        {"fieldPath": "email", "order": "ASCENDING"}
      ]
    }
  ]
}
```

### Portfolios Collection
```javascript
{
  "collectionGroup": "portfolios",
  "queryScope": "COLLECTION",
  "fields": [
    {"fieldPath": "user_id", "order": "ASCENDING"},
    {"fieldPath": "created_at", "order": "DESCENDING"}
  ]
}
```

### Transactions Collection
```javascript
{
  "collectionGroup": "transactions", 
  "queryScope": "COLLECTION",
  "fields": [
    {"fieldPath": "portfolio_id", "order": "ASCENDING"},
    {"fieldPath": "user_id", "order": "ASCENDING"},
    {"fieldPath": "transaction_date", "order": "DESCENDING"}
  ]
}
```

## 🚀 Production Best Practices

### 1. **Query Design Principles**
- **Minimize composite indexes**: Design queries to use single-field indexes when possible
- **Filter first, then order**: Apply filters before ordering to reduce index complexity
- **Limit result sets**: Always use `.limit()` to prevent large data transfers

### 2. **Fallback Strategies**
```python
async def get_items_with_fallback(self, filter_field: str, order_field: str):
    try:
        # Try composite query first
        return await self._complex_query(filter_field, order_field)
    except Exception:
        # Fallback to simpler query with in-memory processing
        return await self._simple_query_with_memory_filter(filter_field, order_field)
```

### 3. **Index Monitoring**
- Monitor Firestore usage in Firebase Console
- Set up alerts for index creation requirements
- Review query performance regularly

## 📝 firestore.indexes.json Template

Create this file in your project root:

```json
{
  "indexes": [
    {
      "collectionGroup": "users",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "is_active", "order": "ASCENDING"},
        {"fieldPath": "created_at", "order": "ASCENDING"}
      ]
    },
    {
      "collectionGroup": "portfolios", 
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "user_id", "order": "ASCENDING"},
        {"fieldPath": "created_at", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "holdings",
      "queryScope": "COLLECTION", 
      "fields": [
        {"fieldPath": "portfolio_id", "order": "ASCENDING"},
        {"fieldPath": "updated_at", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "transactions",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "portfolio_id", "order": "ASCENDING"}, 
        {"fieldPath": "user_id", "order": "ASCENDING"},
        {"fieldPath": "transaction_date", "order": "DESCENDING"}
      ]
    }
  ],
  "fieldOverrides": []
}
```

## 🔧 Deployment Commands

```bash
# Deploy only indexes
firebase deploy --only firestore:indexes

# Deploy everything
firebase deploy

# Check index status
firebase firestore:indexes
```

## ⚡ Performance Tips

1. **Batch Operations**: Use batch writes for multiple document operations
2. **Pagination**: Implement proper pagination with cursors
3. **Caching**: Cache frequently accessed data
4. **Denormalization**: Consider duplicating data to reduce query complexity

## 🎯 Current Status

✅ **Fixed**: Users endpoint now works without composite indexes
✅ **Implemented**: Fallback query strategy for robustness  
✅ **Optimized**: Memory-based filtering for small datasets
⏳ **Recommended**: Create composite indexes for production performance

The application is now resilient to Firestore index requirements while maintaining optimal performance!
