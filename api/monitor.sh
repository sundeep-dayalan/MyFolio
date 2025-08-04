#!/bin/bash

# Personal Wealth Management API Monitoring Script
set -e

# Configuration
PROJECT_ID="fit-guide-465001-p3"
SERVICE_NAME="myfolio-api"
REGION="us-central1"
SERVICE_URL="https://myfolio-api-681015953939.us-central1.run.app"

echo "🔍 Monitoring Personal Wealth Management API"
echo "=============================================="
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "URL: $SERVICE_URL"
echo ""

# Check service status
echo "📊 Service Status:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url,status.conditions[0].type,status.conditions[0].status)" 2>/dev/null || {
    echo "❌ Failed to get service status"
    exit 1
}

echo ""

# Health check
echo "🏥 Health Check:"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$SERVICE_URL/health" 2>/dev/null || echo -e "error\n000")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health check passed (HTTP $HTTP_CODE)"
    echo "Response: $HEALTH_BODY"
else
    echo "❌ Health check failed (HTTP $HTTP_CODE)"
    echo "Response: $HEALTH_BODY"
fi

echo ""

# Recent logs
echo "📋 Recent Logs (last 10 entries):"
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
    --limit=10 \
    --format="value(timestamp,severity,textPayload)" \
    --project=$PROJECT_ID 2>/dev/null || {
    echo "⚠️  Could not retrieve logs"
}

echo ""

# Service metrics (if available)
echo "📈 Service Metrics:"
REVISION=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.latestReadyRevisionName)" 2>/dev/null)
if [ -n "$REVISION" ]; then
    echo "Latest Revision: $REVISION"
    
    # Get traffic allocation
    TRAFFIC=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.traffic[0].percent)" 2>/dev/null)
    echo "Traffic Allocation: ${TRAFFIC:-0}%"
else
    echo "⚠️  Could not retrieve revision information"
fi

echo ""
echo "🔧 Useful Commands:"
echo "  View all logs: gcloud logs read --service=$SERVICE_NAME --limit=50"
echo "  Update deployment: ./deploy.sh"
echo "  Scale to zero: gcloud run services update $SERVICE_NAME --region=$REGION --min-instances=0"
echo "  View service details: gcloud run services describe $SERVICE_NAME --region=$REGION"
