import logging
import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    # Get request details
    method = req.method
    url = req.url
    
    logging.info(f'Method: {method}, URL: {url}')
    
    # Simple response that works for any request
    response_data = {
        "status": "healthy",
        "message": "Azure Functions is working!",
        "service": "sage-api",
        "method": method,
        "url": str(url),
        "timestamp": "2025-01-22"
    }
    
    logging.info(f'Returning response: {response_data}')

    return func.HttpResponse(
        json.dumps(response_data),
        status_code=200,
        headers={
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    )