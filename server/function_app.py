import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="HttpTrigger")
def HttpTrigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    return func.HttpResponse(
        '{"status": "healthy", "message": "Azure Functions v4 is working!", "service": "sage-api"}',
        status_code=200,
        headers={'Content-Type': 'application/json'}
    )