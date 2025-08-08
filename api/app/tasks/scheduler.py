"""
Background task scheduler for token cleanup and maintenance.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
from ..services.plaid_service import PlaidService
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TokenScheduler:
    """Handles scheduled token maintenance tasks."""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.plaid_service = PlaidService()

    def start(self):
        """Start the scheduler with all scheduled tasks."""
        try:
            # Daily cleanup at 2:00 AM UTC
            self.scheduler.add_job(
                func=self._daily_cleanup,
                trigger=CronTrigger(hour=2, minute=0),
                id="daily_token_cleanup",
                name="Daily Token Cleanup",
                replace_existing=True,
            )

            # Weekly analytics at 1:00 AM UTC on Sundays
            self.scheduler.add_job(
                func=self._weekly_analytics,
                trigger=CronTrigger(day_of_week=6, hour=1, minute=0),
                id="weekly_analytics",
                name="Weekly Token Analytics",
                replace_existing=True,
            )

            self.scheduler.start()
            logger.info("Token scheduler started successfully")

            # Ensure scheduler shuts down when app exits
            atexit.register(self.shutdown)

        except Exception as e:
            logger.error(f"Failed to start token scheduler: {e}")

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("Token scheduler shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")

    def _daily_cleanup(self):
        """Daily token cleanup task."""
        try:
            logger.info("Starting scheduled token cleanup")
            stats = self.plaid_service.cleanup_expired_tokens(days_threshold=90)
            logger.info(f"Scheduled cleanup completed: {stats}")
        except Exception as e:
            logger.error(f"Scheduled token cleanup failed: {e}")

    def _weekly_analytics(self):
        """Weekly analytics generation task."""
        try:
            logger.info("Starting scheduled analytics generation")
            analytics = self.plaid_service.get_token_analytics()
            logger.info(f"Weekly analytics generated: {analytics}")
        except Exception as e:
            logger.error(f"Scheduled analytics generation failed: {e}")


# Global scheduler instance
token_scheduler = TokenScheduler()
