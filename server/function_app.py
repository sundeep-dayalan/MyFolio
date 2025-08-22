import logging
import azure.functions as func
from azure.functions import AsgiMiddleware

from app.main import app

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Functions entry point for FastAPI."""
    logging.info(f'Python HTTP trigger function processed a request: {req.method} {req.url}')
    
    try:
        return await AsgiMiddleware(app).handle_async(req)
    except Exception as e:
        logging.error(f'Error in function app: {str(e)}', exc_info=True)
        return func.HttpResponse(
            f"Internal server error: {str(e)}",
            status_code=500
        )