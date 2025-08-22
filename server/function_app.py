import logging
import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Get the route path
    route = req.route_params.get('route', '')
    method = req.method
    
    logging.info(f'Route: {route}, Method: {method}')
    
    # Handle different routes
    if route == '' or route == '/':
        # Root endpoint
        response_data = {
            "message": "Azure Functions with FastAPI is working!",
            "status": "success",
            "method": method
        }
    elif route == 'health':
        # Health check endpoint
        response_data = {
            "status": "healthy", 
            "service": "sage-api-test",
            "timestamp": "2025-01-22"
        }
    elif route.startswith('api/v1/'):
        # API endpoints
        response_data = {
            "message": "API endpoint working",
            "version": "1.0",
            "route": route,
            "method": method
        }
    else:
        # Default response for any other route
        response_data = {
            "message": f"Route {route} processed successfully",
            "method": method,
            "status": "working"
        }

    return func.HttpResponse(
        json.dumps(response_data),
        status_code=200,
        headers={'Content-Type': 'application/json'}
    )