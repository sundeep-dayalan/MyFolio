"""
Wealth management service for business logic.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from firebase_admin import firestore

from ..models.wealth import (
    AssetCreate, AssetUpdate, AssetResponse,
    PortfolioCreate, PortfolioUpdate, PortfolioResponse,
    HoldingCreate, HoldingUpdate, HoldingResponse,
    TransactionCreate, TransactionUpdate, TransactionResponse,
    PortfolioSummary
)
from ..exceptions import UserNotFoundError, ValidationError, FirebaseError
from ..utils.logger import get_logger
from ..utils.security import sanitize_input

logger = get_logger(__name__)


class WealthService:
    """Wealth management service class."""
    
    def __init__(self, db: firestore.Client):
        self.db = db
        self.assets_collection = "assets"
        self.portfolios_collection = "portfolios"
        self.holdings_collection = "holdings"
        self.transactions_collection = "transactions"
    
    # Asset management methods
    async def create_asset(self, asset_data: AssetCreate) -> AssetResponse:
        """Create a new asset."""
        try:
            asset_id = f"{asset_data.asset_type}_{asset_data.symbol}".lower()
            
            # Check if asset already exists
            existing_asset = await self.get_asset_by_id(asset_id)
            if existing_asset:
                return existing_asset  # Return existing asset instead of error
            
            now = datetime.utcnow()
            asset_doc = {
                **asset_data.dict(),
                "id": asset_id,
                "current_price": None,
                "created_at": now,
                "updated_at": now
            }
            
            doc_ref = self.db.collection(self.assets_collection).document(asset_id)
            doc_ref.set(asset_doc)
            
            logger.info(f"Asset created successfully: {asset_id}")
            return AssetResponse(**asset_doc)
            
        except Exception as e:
            logger.error(f"Error creating asset: {str(e)}")
            raise FirebaseError(f"Failed to create asset: {str(e)}")
    
    async def get_asset_by_id(self, asset_id: str) -> Optional[AssetResponse]:
        """Get asset by ID."""
        try:
            doc_ref = self.db.collection(self.assets_collection).document(asset_id)
            doc = doc_ref.get()
            
            if doc.exists:
                asset_data = doc.to_dict()
                return AssetResponse(**asset_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting asset {asset_id}: {str(e)}")
            raise FirebaseError(f"Failed to get asset: {str(e)}")
    
    # Portfolio management methods
    async def create_portfolio(self, user_id: str, portfolio_data: PortfolioCreate) -> PortfolioResponse:
        """Create a new portfolio for a user."""
        try:
            portfolio_id = f"{user_id}_{datetime.utcnow().timestamp()}"
            
            now = datetime.utcnow()
            portfolio_doc = {
                **portfolio_data.dict(),
                "id": portfolio_id,
                "user_id": user_id,
                "total_value": Decimal('0'),
                "created_at": now,
                "updated_at": now
            }
            
            doc_ref = self.db.collection(self.portfolios_collection).document(portfolio_id)
            doc_ref.set(portfolio_doc)
            
            logger.info(f"Portfolio created successfully: {portfolio_id}")
            return PortfolioResponse(**portfolio_doc)
            
        except Exception as e:
            logger.error(f"Error creating portfolio: {str(e)}")
            raise FirebaseError(f"Failed to create portfolio: {str(e)}")
    
    async def get_user_portfolios(self, user_id: str) -> List[PortfolioResponse]:
        """Get all portfolios for a user."""
        try:
            query = self.db.collection(self.portfolios_collection).where("user_id", "==", user_id)
            
            portfolios = []
            for doc in query.stream():
                portfolio_data = doc.to_dict()
                portfolios.append(PortfolioResponse(**portfolio_data))
            
            return portfolios
            
        except Exception as e:
            logger.error(f"Error getting portfolios for user {user_id}: {str(e)}")
            raise FirebaseError(f"Failed to get portfolios: {str(e)}")
    
    async def get_portfolio_by_id(self, portfolio_id: str, user_id: str) -> Optional[PortfolioResponse]:
        """Get portfolio by ID for a specific user."""
        try:
            doc_ref = self.db.collection(self.portfolios_collection).document(portfolio_id)
            doc = doc_ref.get()
            
            if doc.exists:
                portfolio_data = doc.to_dict()
                # Verify the portfolio belongs to the user
                if portfolio_data.get("user_id") == user_id:
                    return PortfolioResponse(**portfolio_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting portfolio {portfolio_id}: {str(e)}")
            raise FirebaseError(f"Failed to get portfolio: {str(e)}")
    
    # Holdings management methods
    async def create_holding(self, user_id: str, holding_data: HoldingCreate) -> HoldingResponse:
        """Create a new holding."""
        try:
            # Verify portfolio belongs to user
            portfolio = await self.get_portfolio_by_id(holding_data.portfolio_id, user_id)
            if not portfolio:
                raise ValidationError("Portfolio not found or access denied")
            
            # Verify asset exists
            asset = await self.get_asset_by_id(holding_data.asset_id)
            if not asset:
                raise ValidationError("Asset not found")
            
            holding_id = f"{holding_data.portfolio_id}_{holding_data.asset_id}"
            
            now = datetime.utcnow()
            current_value = holding_data.quantity * holding_data.average_cost
            gain_loss = Decimal('0')  # Will be calculated when we have current prices
            gain_loss_percentage = Decimal('0')
            
            holding_doc = {
                **holding_data.dict(),
                "id": holding_id,
                "current_value": current_value,
                "gain_loss": gain_loss,
                "gain_loss_percentage": gain_loss_percentage,
                "created_at": now,
                "updated_at": now
            }
            
            doc_ref = self.db.collection(self.holdings_collection).document(holding_id)
            doc_ref.set(holding_doc)
            
            logger.info(f"Holding created successfully: {holding_id}")
            
            # Return holding with asset data
            holding_response = HoldingResponse(**holding_doc)
            holding_response.asset = asset
            return holding_response
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating holding: {str(e)}")
            raise FirebaseError(f"Failed to create holding: {str(e)}")
    
    async def get_portfolio_holdings(self, portfolio_id: str, user_id: str) -> List[HoldingResponse]:
        """Get all holdings for a portfolio."""
        try:
            # Verify portfolio belongs to user
            portfolio = await self.get_portfolio_by_id(portfolio_id, user_id)
            if not portfolio:
                raise ValidationError("Portfolio not found or access denied")
            
            query = self.db.collection(self.holdings_collection).where("portfolio_id", "==", portfolio_id)
            
            holdings = []
            for doc in query.stream():
                holding_data = doc.to_dict()
                holding = HoldingResponse(**holding_data)
                
                # Get asset data
                asset = await self.get_asset_by_id(holding.asset_id)
                if asset:
                    holding.asset = asset
                    holdings.append(holding)
            
            return holdings
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error getting holdings for portfolio {portfolio_id}: {str(e)}")
            raise FirebaseError(f"Failed to get holdings: {str(e)}")
    
    # Transaction management methods
    async def create_transaction(self, user_id: str, transaction_data: TransactionCreate) -> TransactionResponse:
        """Create a new transaction."""
        try:
            # Verify portfolio belongs to user
            portfolio = await self.get_portfolio_by_id(transaction_data.portfolio_id, user_id)
            if not portfolio:
                raise ValidationError("Portfolio not found or access denied")
            
            # Verify asset exists
            asset = await self.get_asset_by_id(transaction_data.asset_id)
            if not asset:
                raise ValidationError("Asset not found")
            
            transaction_id = f"{user_id}_{datetime.utcnow().timestamp()}"
            
            now = datetime.utcnow()
            transaction_doc = {
                **transaction_data.dict(),
                "id": transaction_id,
                "user_id": user_id,
                "created_at": now,
                "updated_at": now
            }
            
            doc_ref = self.db.collection(self.transactions_collection).document(transaction_id)
            doc_ref.set(transaction_doc)
            
            logger.info(f"Transaction created successfully: {transaction_id}")
            
            # Return transaction with asset data
            transaction_response = TransactionResponse(**transaction_doc)
            transaction_response.asset = asset
            return transaction_response
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating transaction: {str(e)}")
            raise FirebaseError(f"Failed to create transaction: {str(e)}")
    
    async def get_portfolio_transactions(self, portfolio_id: str, user_id: str, limit: int = 50) -> List[TransactionResponse]:
        """Get recent transactions for a portfolio."""
        try:
            # Verify portfolio belongs to user
            portfolio = await self.get_portfolio_by_id(portfolio_id, user_id)
            if not portfolio:
                raise ValidationError("Portfolio not found or access denied")
            
            query = (
                self.db.collection(self.transactions_collection)
                .where("portfolio_id", "==", portfolio_id)
                .where("user_id", "==", user_id)
                .order_by("transaction_date", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            
            transactions = []
            try:
                for doc in query.stream():
                    transaction_data = doc.to_dict()
                    transaction = TransactionResponse(**transaction_data)
                    
                    # Get asset data
                    asset = await self.get_asset_by_id(transaction.asset_id)
                    if asset:
                        transaction.asset = asset
                        transactions.append(transaction)
                        
            except Exception as query_error:
                # Fallback: Use simpler query if composite index is not available
                logger.warning(f"Complex transaction query failed, using fallback: {str(query_error)}")
                
                fallback_query = (
                    self.db.collection(self.transactions_collection)
                    .where("portfolio_id", "==", portfolio_id)
                    .limit(limit * 2)  # Get extra to filter by user_id in memory
                )
                
                for doc in fallback_query.stream():
                    transaction_data = doc.to_dict()
                    
                    # Filter by user_id in memory
                    if transaction_data.get("user_id") == user_id:
                        transaction = TransactionResponse(**transaction_data)
                        
                        # Get asset data
                        asset = await self.get_asset_by_id(transaction.asset_id)
                        if asset:
                            transaction.asset = asset
                            transactions.append(transaction)
                        
                        if len(transactions) >= limit:
                            break
                
                # Sort by transaction_date in memory
                transactions.sort(key=lambda x: x.transaction_date, reverse=True)
            
            return transactions
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error getting transactions for portfolio {portfolio_id}: {str(e)}")
            raise FirebaseError(f"Failed to get transactions: {str(e)}")
    
    async def get_portfolio_summary(self, portfolio_id: str, user_id: str) -> PortfolioSummary:
        """Get comprehensive portfolio summary."""
        try:
            # Get portfolio
            portfolio = await self.get_portfolio_by_id(portfolio_id, user_id)
            if not portfolio:
                raise ValidationError("Portfolio not found or access denied")
            
            # Get holdings
            holdings = await self.get_portfolio_holdings(portfolio_id, user_id)
            
            # Get recent transactions
            recent_transactions = await self.get_portfolio_transactions(portfolio_id, user_id, 10)
            
            # Calculate summary metrics
            total_invested = sum(holding.quantity * holding.average_cost for holding in holdings)
            total_current_value = sum(holding.current_value for holding in holdings)
            total_gain_loss = total_current_value - total_invested
            total_gain_loss_percentage = (
                (total_gain_loss / total_invested * 100) if total_invested > 0 else Decimal('0')
            )
            
            return PortfolioSummary(
                portfolio=portfolio,
                holdings=holdings,
                recent_transactions=recent_transactions,
                total_invested=total_invested,
                total_current_value=total_current_value,
                total_gain_loss=total_gain_loss,
                total_gain_loss_percentage=total_gain_loss_percentage
            )
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error getting portfolio summary {portfolio_id}: {str(e)}")
            raise FirebaseError(f"Failed to get portfolio summary: {str(e)}")
