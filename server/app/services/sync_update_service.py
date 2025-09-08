from datetime import datetime, timezone
from typing import Optional
from ..database import cosmos_client
from ..models.sync import (
    SyncInfo,
    TransactionSyncInfo,
    SyncStatus,
    SyncInitiatorType,
    SyncType,
    SyncState,  # Import the new SyncState model
)
from ..exceptions import BankNotFoundError, DatabaseError
from ..constants import Containers
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SyncUpdateService:
    async def update_sync_status(
        self,
        user_id: str,
        item_id: str,
        sync_type: SyncType,
        status: SyncStatus,
        initiator_type: Optional[SyncInitiatorType] = None,
        initiator_id: Optional[str] = None,
        error: Optional[Exception] = None,
        next_cursor: Optional[str] = None,
    ) -> None:
        """
        Fetches a bank document and updates the status of a specific sync type
        within the new 'syncs' object.
        """
        logger.info(
            f"Updating {sync_type.value} sync status to '{status.value}' for item {item_id}"
        )

        try:
            await cosmos_client.ensure_connected()
            # 1. Fetch the existing bank document
            bank_document = cosmos_client.get_item(Containers.BANKS, item_id, user_id)
            if not bank_document:
                raise BankNotFoundError(
                    f"Bank document not found for item_id: {item_id}"
                )

            # 2. Load the current sync state into a Pydantic model
            syncs = SyncState.model_validate(bank_document.get("syncs", {}))

            # 3. Create the new SyncInfo record for this update
            now = datetime.now(timezone.utc)
            
            # Create the appropriate sync record type based on sync_type
            if sync_type == SyncType.TRANSACTIONS:
                new_sync_record = TransactionSyncInfo(
                    status=status,
                    initiator_type=initiator_type,
                    initiator_id=initiator_id,
                    next_cursor=next_cursor,
                )
            else:
                new_sync_record = SyncInfo(
                    status=status,
                    initiator_type=initiator_type,
                    initiator_id=initiator_id,
                )

            # Preserve start time if the sync was already in progress
            if status in [SyncStatus.COMPLETED, SyncStatus.ERROR]:
                existing_record = getattr(syncs, sync_type.value, SyncInfo())
                new_sync_record.started_at = existing_record.started_at or now
                new_sync_record.completed_at = now
            else:  # PENDING or SYNCING
                new_sync_record.started_at = now

            if error:
                new_sync_record.error_message = str(error)

            # 4. Update the correct field in the syncs object (e.g., syncs.accounts)
            setattr(syncs, sync_type.value, new_sync_record)

            # 5. Prepare the final update payload and save to the database
            update_data = {
                # Update the entire 'syncs' object
                "syncs": syncs.model_dump(mode="json", by_alias=True),
                "updatedAt": now.isoformat(),
            }
            cosmos_client.update_item(Containers.BANKS, item_id, user_id, update_data)

        except Exception as e:
            logger.error(
                f"Failed to update sync status for item {item_id}: {e}",
                exc_info=True,
            )
            # Re-raise as a database error to ensure the calling process fails
            raise DatabaseError(f"Failed to update sync status: {e}")


sync_update_service = SyncUpdateService()
