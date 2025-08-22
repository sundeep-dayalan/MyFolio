import azure.functions as func
from fastapi import FastAPI

# Create a minimal FastAPI app for testing
test_app = FastAPI(
    title="Sage API Test",
    description="Minimal test version to verify Azure Functions deployment"
)

@test_app.get("/")
async def root():
    return {"message": "Azure Functions with FastAPI is working!", "status": "success"}

@test_app.get("/health")  
async def health():
    return {"status": "healthy", "service": "sage-api-test"}

@test_app.get("/api/v1/test")
async def api_test():
    return {"message": "API endpoint working", "version": "1.0"}

# Use this minimal app instead of the complex one
app = func.AsgiFunctionApp(app=test_app, http_auth_level=func.AuthLevel.ANONYMOUS)