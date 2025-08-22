import azure.functions as func
import logging

app = func.FunctionApp()

@app.function_name(name="HttpTrigger")
@app.route(route="HttpTrigger", auth_level=func.AuthLevel.ANONYMOUS)
def test_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    return func.HttpResponse(
        body='{"status": "healthy", "message": "Azure Functions is working!", "service": "sage-api"}',
        status_code=200,
        mimetype="application/json"
    )