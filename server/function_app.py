import azure.functions as func
from app.main import app as fastapi_app

# Create Azure Functions app using the modern v2 approach
app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)