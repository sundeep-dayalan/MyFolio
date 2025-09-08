"""
Plaid-related Pydantic models for data validation and serialization.
"""

from __future__ import annotations
from datetime import datetime
from datetime import date as DateType
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Literal, Dict, Any

from .sync import SyncInfo, SyncState


class PlaidEnvironment(str, Enum):
    """Plaid environment enumeration."""

    SANDBOX = "sandbox"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class PlaidTokenStatus(str, Enum):
    """Plaid token status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class PlaidAccessToken(BaseModel):
    """Plaid access token model for database storage."""

    user_id: str = Field(..., description="User ID from authentication")
    access_token: str = Field(..., description="Encrypted Plaid access token")
    item_id: str = Field(..., description="Plaid item ID")
    institution_id: Optional[str] = Field(None, description="Institution ID")
    institution_name: Optional[str] = Field(None, description="Institution name")
    status: PlaidTokenStatus = Field(default=PlaidTokenStatus.ACTIVE)
    environment: PlaidEnvironment = Field(default=PlaidEnvironment.SANDBOX)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        extra = "ignore"
        use_enum_values = True
        arbitrary_types_allowed = True


class PlaidAccount(BaseModel):
    """Plaid account model."""

    account_id: str
    name: str
    official_name: Optional[str] = None
    type: str
    subtype: Optional[str] = None
    mask: Optional[str] = None

    class Config:
        extra = "ignore"
        from_attributes = True


class PlaidBalance(BaseModel):
    """Plaid balance model."""

    available: Optional[float] = None
    current: Optional[float] = None
    iso_currency_code: Optional[str] = None
    limit: Optional[float] = None
    last_updated_datetime: Optional[datetime] = None
    unofficial_currency_code: Optional[str] = None

    class Config:
        extra = "ignore"
        from_attributes = True


class PlaidAccountWithBalance(BaseModel):
    """Plaid account with balance information."""

    account_id: str
    name: str
    official_name: Optional[str] = None
    type: str
    subtype: Optional[str] = None
    mask: Optional[str] = None
    balances: PlaidBalance
    item_id: Optional[str] = None  # Bank identifier
    institution_name: Optional[str] = None
    institution_id: Optional[str] = None
    logo: Optional[str] = None  # Institution logo URL

    class Config:
        extra = "ignore"
        from_attributes = True


class LinkTokenRequest(BaseModel):
    """Link token creation request."""

    user_id: Optional[str] = Field(None, description="Will be set from authentication")

    class Config:
        extra = "ignore"
        from_attributes = True


class PublicTokenExchangeRequest(BaseModel):
    """Public token exchange request."""

    public_token: str = Field(..., description="Plaid public token from Link")

    class Config:
        extra = "ignore"
        from_attributes = True


class PlaidWebhookRequest(BaseModel):
    """Plaid webhook request model."""

    webhook_type: str
    webhook_code: str
    item_id: str
    error: Optional[Dict[str, Any]] = None
    new_transactions: Optional[int] = None
    removed_transactions: Optional[List[str]] = None

    class Config:
        extra = "ignore"
        from_attributes = True


# https://plaid.com/docs/api/accounts/#accounts-get-response-accounts-type:~:text=and%20corresponding%20subtypes.-,Possible%20values,-%3A%20investment%2C
class AccountType(str, Enum):
    INVESTMENT = "investment"
    CREDIT = "credit"
    DEPOSITORY = "depository"
    LOAN = "loan"
    BROKERAGE = "brokerage"
    OTHER = "other"


# https://plaid.com/docs/api/accounts/#accounts-get-response-accounts-type:~:text=and%20corresponding%20subtypes.-,Possible%20values,-%3A%20401a%2C
class AccountSubtype(str, Enum):
    """A comprehensive list of account subtypes based on Plaid documentation."""

    # Depository Accounts
    CHECKING = "checking"
    SAVINGS = "savings"
    HSA = "hsa"
    CASH_MANAGEMENT = "cash management"
    MONEY_MARKET = "money market"
    CD = "cd"
    PAYPAL = "paypal"
    PREPAID = "prepaid"
    EBT = "ebt"
    CASH_ISA = "cash isa"
    OVERDRAFT = "overdraft"

    # Loan and Credit Accounts
    CREDIT_CARD = "credit card"
    LOAN = "loan"
    STUDENT = "student"
    MORTGAGE = "mortgage"
    HOME_EQUITY = "home equity"
    LINE_OF_CREDIT = "line of credit"
    AUTO = "auto"
    COMMERCIAL = "commercial"
    CONSTRUCTION = "construction"
    CONSUMER = "consumer"

    # Investment & Brokerage Accounts
    BROKERAGE = "brokerage"
    NON_TAXABLE_BROKERAGE_ACCOUNT = "non-taxable brokerage account"
    STOCK_PLAN = "stock plan"
    MUTUAL_FUND = "mutual fund"
    T_529 = "529"
    EDUCATION_SAVINGS_ACCOUNT = "education savings account"
    UGMA = "ugma"
    UTMA = "utma"
    ISA = "isa"
    SIPP = "sipp"
    GIC = "gic"

    # Retirement Accounts
    T_401A = "401a"
    FOUR_OH_ONE_K = "401k"
    T_403B = "403B"
    T_457B = "457b"
    IRA = "ira"
    ROTH = "roth"
    ROTH_401K = "roth 401k"
    PENSION = "pension"
    RETIREMENT = "retirement"
    PROFIT_SHARING_PLAN = "profit sharing plan"
    THRIFT_SAVINGS_PLAN = "thrift savings plan"
    SEP_IRA = "sep ira"
    SIMPLE_IRA = "simple ira"
    KEOGH = "keogh"
    SARSEP = "sarsep"

    # Canadian Retirement Accounts
    TFSA = "tfsa"
    LIF = "lif"
    LIRA = "lira"
    LRIF = "lrif"
    LRSP = "lrsp"
    PRIF = "prif"
    RDSP = "rdsp"
    RESP = "resp"
    RLIF = "rlif"
    RRIF = "rrif"
    RRSP = "rrsp"

    # Insurance & Annuities
    LIFE_INSURANCE = "life insurance"
    FIXED_ANNUITY = "fixed annuity"
    VARIABLE_ANNUITY = "variable annuity"
    OTHER_ANNUITY = "other annuity"
    OTHER_INSURANCE = "other insurance"
    HEALTH_REIMBURSEMENT_ARRANGEMENT = "health reimbursement arrangement"

    # Other Account Types
    BUSINESS = "business"
    CRYPTO_EXCHANGE = "crypto exchange"
    NON_CUSTODIAL_WALLET = "non-custodial wallet"
    PAYROLL = "payroll"
    TRUST = "trust"
    OTHER = "other"


# https://plaid.com/docs/api/accounts/#accounts-get-response-accounts-type:~:text=via%20Database%20Auth.-,Possible%20values,-%3A%20automatically_verified%2C
class VerificationStatus(str, Enum):
    AUTOMATICALLY_VERIFIED = "automatically_verified"
    PENDING_AUTOMATIC_VERIFICATION = "pending_automatic_verification"
    PENDING_MANUAL_VERIFICATION = "pending_manual_verification"
    MANUALLY_VERIFIED = "manually_verified"
    VERIFICATION_EXPIRED = "verification_expired"
    VERIFICATION_FAILED = "verification_failed"
    UNSENT = "unsent"
    DATABASE_MATCHED = "database_matched"
    DATABASE_INSIGHTS_PASS = "database_insights_pass"
    DATABASE_INSIGHTS_PASS_WITH_CAUTION = "database_insights_pass_with_caution"
    DATABASE_INSIGHTS_FAIL = "database_insights_fail"


class Balance(BaseModel):
    """A set of fields describing the balance for an account."""

    available: Optional[float] = None
    current: Optional[float] = None
    limit: Optional[float] = None
    iso_currency_code: Optional[str] = None
    unofficial_currency_code: Optional[str] = None
    last_updated_datetime: Optional[datetime] = Field(
        None, description="Timestamp in ISO 8601 format"
    )


class PreviousReturns(BaseModel):
    """Information about known ACH returns for the account and routing number."""

    has_previous_administrative_return: bool


class NetworkStatus(BaseModel):
    """Status information about the account and routing number in the Plaid network."""

    has_numbers_match: bool
    is_numbers_match_verified: bool


class VerificationInsights(BaseModel):
    """Insights from performing database verification for the account."""

    name_match_score: Optional[int] = None
    network_status: NetworkStatus
    previous_returns: PreviousReturns
    account_number_format: Literal["valid", "invalid", "unknown"]


class Account(BaseModel):
    """A financial institution account associated with an Item."""

    account_id: str
    balances: Balance
    mask: Optional[str] = None
    name: str
    official_name: Optional[str] = None
    type: AccountType
    subtype: Optional[AccountSubtype] = None
    verification_status: Optional[VerificationStatus] = None
    verification_name: Optional[str] = None
    verification_insights: Optional[VerificationInsights] = None
    persistent_account_id: Optional[str] = None
    holder_category: Optional[Literal["business", "personal", "unrecognized"]] = None


class PlaidError(BaseModel):
    """An error object returned by the Plaid API."""

    error_type: str
    error_code: str
    error_code_reason: Optional[str] = None
    error_message: str
    display_message: Optional[str] = None
    request_id: str
    causes: Optional[List[Dict[str, Any]]] = None
    status: Optional[int] = None
    documentation_url: Optional[str] = None
    suggested_action: Optional[str] = None


class Item(BaseModel):
    """Metadata about the Item."""

    item_id: str
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    webhook: Optional[str] = None
    error: Optional[PlaidError] = None
    available_products: List[str]
    billed_products: List[str]
    products: List[str]
    consented_products: Optional[List[str]] = None
    consent_expiration_time: Optional[datetime] = None
    update_type: Literal["background", "user_present_required"]
    auth_method: Optional[
        Literal[
            "INSTANT_AUTH",
            "INSTANT_MATCH",
            "AUTOMATED_MICRODEPOSITS",
            "SAME_DAY_MICRODEPOSITS",
            "INSTANT_MICRODEPOSITS",
            "DATABASE_MATCH",
            "DATABASE_INSIGHTS",
            "TRANSFER_MIGRATED",
            "INVESTMENTS_FALLBACK",
        ]
    ] = None


class PlaidAccountsGetResponse(BaseModel):
    """The top-level response object from Plaid's /accounts/get endpoint."""

    accounts: List[Account]
    item: Item
    request_id: str


# https://plaid.com/docs/api/accounts/#accounts-get-response-accounts-type:~:text=fallback%20flow.-,Possible%20values%3A,-INSTANT_AUTH%2C%20INSTANT_MATCH
class AuthMethod(str, Enum):
    """The method used to populate Auth data for the Item."""

    INSTANT_AUTH = "INSTANT_AUTH"
    INSTANT_MATCH = "INSTANT_MATCH"
    AUTOMATED_MICRODEPOSITS = "AUTOMATED_MICRODEPOSITS"
    SAME_DAY_MICRODEPOSITS = "SAME_DAY_MICRODEPOSITS"
    INSTANT_MICRODEPOSITS = "INSTANT_MICRODEPOSITS"
    DATABASE_MATCH = "DATABASE_MATCH"
    DATABASE_INSIGHTS = "DATABASE_INSIGHTS"
    TRANSFER_MIGRATED = "TRANSFER_MIGRATED"
    INVESTMENTS_FALLBACK = "INVESTMENTS_FALLBACK"


# https://plaid.com/docs/api/accounts/#accounts-get-response-item-available-products:~:text=resolving%20the%20error-,available_products,-JSON
class PlaidProduct(str, Enum):
    """Represents a Plaid product."""

    # Core Products
    ASSETS = "assets"
    AUTH = "auth"
    BALANCE = "balance"
    IDENTITY = "identity"
    INVESTMENTS = "investments"
    LIABILITIES = "liabilities"
    PAYMENT_INITIATION = "payment_initiation"
    TRANSACTIONS = "transactions"

    # Identity Products
    IDENTITY_MATCH = "identity_match"
    IDENTITY_VERIFICATION = "identity_verification"

    # Income & Employment Products
    INCOME = "income"
    INCOME_VERIFICATION = "income_verification"
    EMPLOYMENT = "employment"

    # Credit & Reporting Products
    CREDIT_DETAILS = "credit_details"
    CRA_BASE_REPORT = "cra_base_report"
    CRA_INCOME_INSIGHTS = "cra_income_insights"
    CRA_PARTNER_INSIGHTS = "cra_partner_insights"
    CRA_NETWORK_INSIGHTS = "cra_network_insights"
    CRA_CASHFLOW_INSIGHTS = "cra_cashflow_insights"
    CRA_MONITORING = "cra_monitoring"
    CRA_PLAID_CREDIT_SCORE = "cra_plaid_credit_score"

    # Transaction & Financial Management Products
    RECURRING_TRANSACTIONS = "recurring_transactions"
    TRANSACTIONS_REFRESH = "transactions_refresh"
    STATEMENTS = "statements"

    # Risk & Fraud Products
    SIGNAL = "signal"
    BEACON = "beacon"

    # Payment & Transfer Products
    TRANSFER = "transfer"
    STANDING_ORDERS = "standing_orders"
    PROCESSOR_PAYMENTS = "processor_payments"
    PAY_BY_BANK = "pay_by_bank"
    PROTECT_LINKED_BANK = "protect_linked_bank"

    # Other Products
    INVESTMENTS_AUTH = "investments_auth"
    PROCESSOR_IDENTITY = "processor_identity"
    PROFILE = "profile"
    LAYER = "layer"
    BALANCE_PLUS = "balance_plus"


class UpdateStatus(BaseModel):
    """Information about the last successful and failed updates for a product."""

    last_successful_update: Optional[datetime] = None
    last_failed_update: Optional[datetime] = None


class LastWebhook(BaseModel):
    """Information about the last webhook fired for the Item."""

    sent_at: Optional[datetime] = None
    code_sent: Optional[str] = None


class PlaidItemStatus(BaseModel):
    """Status information about the Item's data connections."""

    investments: Optional[UpdateStatus] = None
    transactions: Optional[UpdateStatus] = None
    last_webhook: Optional[LastWebhook] = None


class PlaidItem(BaseModel):
    """Metadata about the Item, which represents a connection to a financial institution."""

    item_id: str
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    available_products: List[PlaidProduct]
    billed_products: List[PlaidProduct]
    products: List[PlaidProduct]
    consented_products: Optional[List[PlaidProduct]] = None
    error: Optional[PlaidError] = None
    webhook: Optional[str] = None
    update_type: Literal["background", "user_present_required"]
    auth_method: Optional[AuthMethod] = None
    consent_expiration_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    consented_use_cases: Optional[List[str]] = None
    consented_data_scopes: Optional[List[str]] = None


class PlaidItemGetResponse(BaseModel):
    """The complete response object from an endpoint like /item/get."""

    item: PlaidItem
    status: Optional[PlaidItemStatus] = None


# https://plaid.com/docs/api/institutions/#search-institutions:~:text=Minimum%3A%200-,country_codes,-required
class CountryCode(str, Enum):
    """A list of the country codes supported by the institution."""

    US = "US"
    GB = "GB"
    ES = "ES"
    NL = "NL"
    FR = "FR"
    IE = "IE"
    CA = "CA"
    DE = "DE"
    IT = "IT"
    PL = "PL"
    DK = "DK"
    NO = "NO"
    SE = "SE"
    EE = "EE"
    LT = "LT"
    LV = "LV"
    PT = "PT"
    BE = "BE"
    AT = "AT"
    FI = "FI"


# https://plaid.com/docs/api/institutions/#institutions-get-response-institutions-status-item-logins-status
class HealthStatus(str, Enum):
    """The health status of a product, now deprecated in favor of the breakdown object."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"


# https://plaid.com/docs/api/institutions/#institutions-get-response-institutions-status-item-logins-breakdown-refresh-interval
class RefreshInterval(str, Enum):
    """The refresh interval for subscription products."""

    NORMAL = "NORMAL"
    DELAYED = "DELAYED"
    STOPPED = "STOPPED"


# https://plaid.com/docs/api/institutions/#institutions-get-response-institutions-status-health-incidents-incident-updates-status
class IncidentStatus(str, Enum):
    """The status of a health incident."""

    INVESTIGATING = "INVESTIGATING"
    IDENTIFIED = "IDENTIFIED"
    SCHEDULED = "SCHEDULED"
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"


# https://plaid.com/docs/api/institutions/#institutions-get-response-institutions-payment-initiation-metadata-standing-order-metadata-valid-standing-order-intervals
class StandingOrderInterval(str, Enum):
    """Valid standing order intervals supported by the institution."""

    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class StatusBreakdown(BaseModel):
    """A detailed breakdown of an institution's performance for a request type."""

    success: float
    error_plaid: float
    error_institution: float
    refresh_interval: Optional[RefreshInterval] = None


class ProductStatusHealth(BaseModel):
    """A representation of the status health of a request type (e.g., item_logins, auth)."""

    status: HealthStatus = Field(
        ..., description="This field is deprecated in favor of the breakdown object."
    )
    last_status_change: datetime
    breakdown: StatusBreakdown


class IncidentUpdate(BaseModel):
    """An update on a health incident."""

    description: str
    status: IncidentStatus
    updated_date: datetime


class HealthIncident(BaseModel):
    """Details of a recent health incident associated with the institution."""

    start_date: datetime
    end_date: Optional[datetime] = None
    title: str
    incident_updates: List[IncidentUpdate]


class StandingOrderMetadata(BaseModel):
    """Metadata related to valid Payment Initiation standing order configurations."""

    supports_standing_order_end_date: bool
    supports_standing_order_negative_execution_days: bool
    valid_standing_order_intervals: List[StandingOrderInterval]


class PaymentInitiationMetadata(BaseModel):
    """Metadata that captures what specific payment configurations an institution supports."""

    supports_international_payments: bool
    supports_sepa_instant: bool
    maximum_payment_amount: Dict[str, str]
    supports_refund_details: bool
    standing_order_metadata: Optional[StandingOrderMetadata] = None
    supports_payment_consents: Optional[bool] = None  # Added based on docs


class SupportedAuthMethods(BaseModel):
    """Metadata specifically related to which auth methods an institution supports."""

    instant_auth: bool
    instant_match: bool
    automated_micro_deposits: bool
    instant_micro_deposits: Optional[bool] = (
        None  # Marked as optional as it can be null
    )


class AuthMetadata(BaseModel):
    """Metadata that captures information about the Auth features of an institution."""

    supported_methods: Optional[SupportedAuthMethods] = None


class PlaidInstitutionStatus(BaseModel):
    """The status of an institution, determined by the health of its various products."""

    item_logins: Optional[ProductStatusHealth] = None
    transactions_updates: Optional[ProductStatusHealth] = None
    auth: Optional[ProductStatusHealth] = None
    identity: Optional[ProductStatusHealth] = None
    investments_updates: Optional[ProductStatusHealth] = None
    liabilities_updates: Optional[ProductStatusHealth] = None
    liabilities: Optional[ProductStatusHealth] = (
        None  # Note: both liabilities and liabilities_updates exist
    )
    investments: Optional[ProductStatusHealth] = None


class PlaidInstitution(BaseModel):
    """Represents the complete details for a single financial institution."""

    institution_id: str
    name: str
    products: List[PlaidProduct]
    country_codes: List[CountryCode]
    url: Optional[str] = None
    primary_color: Optional[str] = None
    logo: Optional[str] = None
    routing_numbers: List[str]
    dtc_numbers: Optional[List[str]] = None
    oauth: bool

    # Nested object for health status
    status: Optional[PlaidInstitutionStatus] = None

    # Nested list for health incidents
    health_incidents: Optional[List[HealthIncident]] = None

    # Nested objects for metadata
    payment_initiation_metadata: Optional[PaymentInitiationMetadata] = None
    auth_metadata: Optional[AuthMetadata] = None


# Transaction-related classes temporarily disabled to fix recursion issue
# Will need to be restored with proper forward reference handling


class Location(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    store_number: Optional[str] = None


class PersonalFinanceCategory(BaseModel):
    """
    Plaid's personal finance category taxonomy for the transaction.
    """

    primary: str
    detailed: str
    confidence: Optional[str] = None


class Counterparty(BaseModel):
    name: str
    entity_id: Optional[str] = None
    type: CounterpartyType
    website: Optional[str] = None
    logo_url: Optional[str] = None
    confidence_level: Optional[ConfidenceLevel] = None
    account_numbers: Optional[AccountNumbers] = None
    merchant_entity_id: Optional[str] = None


class SystemMetadata(BaseModel):
    """
    Internal metadata for tracking the document's lifecycle in Cosmos DB.
    This is NOT part of the Plaid API response.
    """

    created_at: datetime
    updated_at: datetime
    is_removed: bool
    source_sync_cursor: str


class TransactionDocument(BaseModel):
    """
    A production-grade Pydantic model for a Plaid transaction stored in Cosmos DB.
    This model reflects the flattened, enriched, and metadata-tracked document structure.
    """

    # --- Core Identifiers & Partitioning ---
    id: str = Field(
        ...,
        description="The unique document ID in Cosmos DB (e.g., 'user-12345-transaction-abc').",
    )
    user_id: str = Field(
        ...,
        alias="userId",
        description="The Partition Key for the Cosmos DB container.",
    )
    type: Literal["transaction"] = Field(
        ...,
        description="The document type, for co-locating different data in one container.",
    )

    # --- Plaid-Specific Foreign Keys ---
    plaid_transaction_id: str = Field(..., alias="plaidTransactionId")
    plaid_account_id: str = Field(..., alias="plaidAccountId")
    plaid_item_id: str = Field(..., alias="plaidItemId")

    # --- System Metadata ---
    meta: SystemMetadata = Field(
        ...,
        alias="_meta",
        description="Internal metadata for document lifecycle tracking.",
    )

    # --- Primary Transaction Data ---
    description: str = Field(
        ...,
        description="The clean merchant name or transaction description for display.",
    )
    amount: float = Field(
        ...,
        description="Transaction amount. Positive for outflows (debits), negative for inflows (credits).",
    )
    currency: str = Field(..., description="The ISO-4217 currency code.")
    date: DateType = Field(
        ..., description="The date the transaction posted (YYYY-MM-DD)."
    )
    authorized_date: Optional[DateType] = Field(
        None,
        alias="authorizedDate",
        description="The date the transaction was authorized.",
    )
    is_pending: bool = Field(
        ...,
        alias="isPending",
        description="True if the transaction is pending or unsettled.",
    )

    # --- Enrichment & Categorization Data ---
    category: PersonalFinanceCategory
    payment_channel: str = Field(
        ...,
        alias="paymentChannel",
        description="The channel used to make a payment (e.g., 'in store', 'online').",
    )
    location: Optional[Location] = None
    counterparties: List[Counterparty]

    # --- Reconciliation & Auxiliary Data ---
    pending_transaction_id: Optional[str] = Field(None, alias="pendingTransactionId")
    original_description: Optional[str] = Field(
        None,
        alias="originalDescription",
        description="The raw description from the financial institution.",
    )

    # --- Future-Proofing Raw Data ---
    raw_plaid_data: Transaction | TransactionsUpdateResponse | RemovedTransaction = (
        Field(
            ...,
            alias="_rawPlaidData",
            description="The complete, unaltered JSON object from Plaid for this transaction.",
        )
    )

    class Config:
        # This allows the model to be created from a dictionary that has extra fields,
        # which can be useful if Plaid adds new properties to their API.
        extra = "ignore"


class TransactionsUpdateStatusEnum(str, Enum):
    TRANSACTIONS_UPDATE_STATUS_UNKNOWN = "TRANSACTIONS_UPDATE_STATUS_UNKNOWN"
    NOT_READY = "NOT_READY"
    INITIAL_UPDATE_COMPLETE = "INITIAL_UPDATE_COMPLETE"
    HISTORICAL_UPDATE_COMPLETE = "HISTORICAL_UPDATE_COMPLETE"

    class Config:
        extra = "ignore"


class HolderCategory(str, Enum):
    BUSINESS = "business"
    PERSONAL = "personal"
    UNRECOGNIZED = "unrecognized"

    class Config:
        extra = "ignore"


class AccountNumberFormat(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"

    class Config:
        extra = "ignore"


class TransactionType(str, Enum):
    DIGITAL = "digital"
    PLACE = "place"
    SPECIAL = "special"
    UNRESOLVED = "unresolved"


class PaymentChannel(str, Enum):
    ONLINE = "online"
    IN_STORE = "in store"
    OTHER = "other"

    class Config:
        extra = "ignore"


class ConfidenceLevel(str, Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

    class Config:
        extra = "ignore"


class TransactionCode(str, Enum):
    ADJUSTMENT = "adjustment"
    ATM = "atm"
    BANK_CHARGE = "bank charge"
    BILL_PAYMENT = "bill payment"
    CASH = "cash"
    CASHBACK = "cashback"
    CHEQUE = "cheque"
    DIRECT_DEBIT = "direct debit"
    INTEREST = "interest"
    PURCHASE = "purchase"
    STANDING_ORDER = "standing order"
    TRANSFER = "transfer"

    class Config:
        extra = "ignore"


class CounterpartyType(str, Enum):
    MERCHANT = "merchant"
    FINANCIAL_INSTITUTION = "financial_institution"
    PAYMENT_APP = "payment_app"
    MARKETPLACE = "marketplace"
    PAYMENT_TERMINAL = "payment_terminal"
    INCOME_SOURCE = "income_source"

    class Config:
        extra = "ignore"


class PaymentMeta(BaseModel):
    reference_number: Optional[str] = None
    ppd_id: Optional[str] = None
    payee: Optional[str] = None
    by_order_of: Optional[str] = None
    payer: Optional[str] = None
    payment_method: Optional[str] = None
    payment_processor: Optional[str] = None
    reason: Optional[str] = None


class International(BaseModel):
    iban: Optional[str] = Field(None, min_length=15, max_length=34)
    bic: Optional[str] = Field(None, min_length=8, max_length=11)


class Bacs(BaseModel):
    account: Optional[str] = None
    sort_code: Optional[str] = None


class AccountNumbers(BaseModel):
    bacs: Optional[Bacs] = None
    international: Optional[International] = None


class Transaction(BaseModel):
    account_id: str
    amount: float
    iso_currency_code: Optional[str] = None
    unofficial_currency_code: Optional[str] = None
    check_number: Optional[str] = None
    date: DateType
    location: Location
    name: str  # Deprecated field
    merchant_name: Optional[str] = None
    original_description: Optional[str] = None
    payment_meta: PaymentMeta
    pending: bool
    pending_transaction_id: Optional[str] = None
    account_owner: Optional[str] = None
    transaction_id: str
    transaction_type: Optional[TransactionType] = None  # Deprecated field
    logo_url: Optional[str] = None
    website: Optional[str] = None
    authorized_date: Optional[DateType] = None
    authorized_datetime: Optional[datetime] = None
    datetime: Optional[datetime] = None
    payment_channel: PaymentChannel
    personal_finance_category: Optional[PersonalFinanceCategory] = None
    transaction_code: Optional[TransactionCode] = None
    personal_finance_category_icon_url: Optional[str] = None
    counterparties: List[Counterparty]


class RemovedTransaction(BaseModel):
    transaction_id: str
    account_id: str


class TransactionsUpdateResponse(BaseModel):
    """
    A Pydantic model representing the response for transaction updates from the API.
    """

    transactions_update_status: TransactionsUpdateStatusEnum
    accounts: List[Account]
    added: List[Transaction]
    modified: List[Transaction]
    removed: List[RemovedTransaction]
    next_cursor: str
    has_more: bool
