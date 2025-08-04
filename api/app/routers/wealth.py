"""
Wealth management routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from firebase_admin import firestore

from ..models.wealth import (
    AssetCreate, AssetResponse,
    PortfolioCreate, PortfolioResponse, PortfolioSummary,
    HoldingCreate, HoldingResponse,
    TransactionCreate, TransactionResponse
)
from ..services.wealth_service import WealthService
from ..dependencies import get_firestore_client, get_current_user_id
from ..exceptions import ValidationError

router = APIRouter(prefix="/wealth", tags=["wealth-management"])


def get_wealth_service(db: firestore.Client = Depends(get_firestore_client)) -> WealthService:
    """Get wealth service dependency."""
    return WealthService(db)


# Asset routes
@router.post("/assets", response_model=AssetResponse, status_code=201)
async def create_asset(
    asset_data: AssetCreate,
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Create a new asset."""
    return await wealth_service.create_asset(asset_data)


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Get asset by ID."""
    asset = await wealth_service.get_asset_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# Portfolio routes
@router.post("/portfolios", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(
    portfolio_data: PortfolioCreate,
    current_user_id: str = Depends(get_current_user_id),
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Create a new portfolio."""
    return await wealth_service.create_portfolio(current_user_id, portfolio_data)


@router.get("/portfolios", response_model=List[PortfolioResponse])
async def get_user_portfolios(
    current_user_id: str = Depends(get_current_user_id),
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Get all portfolios for the current user."""
    return await wealth_service.get_user_portfolios(current_user_id)


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: str,
    current_user_id: str = Depends(get_current_user_id),
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Get portfolio by ID."""
    portfolio = await wealth_service.get_portfolio_by_id(portfolio_id, current_user_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get("/portfolios/{portfolio_id}/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    portfolio_id: str,
    current_user_id: str = Depends(get_current_user_id),
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Get comprehensive portfolio summary."""
    try:
        return await wealth_service.get_portfolio_summary(portfolio_id, current_user_id)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Holdings routes
@router.post("/portfolios/{portfolio_id}/holdings", response_model=HoldingResponse, status_code=201)
async def create_holding(
    portfolio_id: str,
    holding_data: HoldingCreate,
    current_user_id: str = Depends(get_current_user_id),
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Create a new holding in a portfolio."""
    # Override portfolio_id from URL
    holding_data.portfolio_id = portfolio_id
    
    try:
        return await wealth_service.create_holding(current_user_id, holding_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/portfolios/{portfolio_id}/holdings", response_model=List[HoldingResponse])
async def get_portfolio_holdings(
    portfolio_id: str,
    current_user_id: str = Depends(get_current_user_id),
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Get all holdings for a portfolio."""
    try:
        return await wealth_service.get_portfolio_holdings(portfolio_id, current_user_id)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Transaction routes
@router.post("/portfolios/{portfolio_id}/transactions", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    portfolio_id: str,
    transaction_data: TransactionCreate,
    current_user_id: str = Depends(get_current_user_id),
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Create a new transaction in a portfolio."""
    # Override portfolio_id from URL
    transaction_data.portfolio_id = portfolio_id
    
    try:
        return await wealth_service.create_transaction(current_user_id, transaction_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/portfolios/{portfolio_id}/transactions", response_model=List[TransactionResponse])
async def get_portfolio_transactions(
    portfolio_id: str,
    limit: int = Query(50, ge=1, le=100, description="Number of transactions to return"),
    current_user_id: str = Depends(get_current_user_id),
    wealth_service: WealthService = Depends(get_wealth_service)
):
    """Get recent transactions for a portfolio."""
    try:
        return await wealth_service.get_portfolio_transactions(portfolio_id, current_user_id, limit)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
