import asyncio
import logging

from auth import AuthClient, TokenExpiredError
from client import AuditLogClient
from config import Settings
from processor import EventProcessor

logger = logging.getLogger(__name__)


class PollingRunner:
    """Main polling loop that orchestrates fetching and processing events."""

    def __init__(
        self,
        settings: Settings,
        auth: AuthClient,
        client: AuditLogClient,
        processor: EventProcessor,
    ):
        self.settings = settings
        self.auth = auth
        self.client = client
        self.processor = processor
        self.iteration = 0

    async def run(self) -> None:
        """Run the main polling loop."""
        logger.info("=" * 60)
        logger.info("Audit SIEM Integration starting")
        logger.info("=" * 60)
        logger.info("Press Ctrl+C to gracefully shutdown")

        # Ensure we have a valid token before starting
        await self.auth.ensure_valid_token()

        cursor = self.processor.cursor

        if self.processor.needs_deduplication:
            logger.info("Resuming from last event, will check for duplicates")
        else:
            logger.info("Starting fresh, no previous event found")

        while True:
            self.iteration += 1
            logger.info(f"--- Iteration {self.iteration} ---")

            try:
                response = await self.client.fetch_logs(cursor)
            except TokenExpiredError:
                logger.warning("Token expired, refreshing token")
                await self.auth.refresh_token()
                continue
            except Exception as e:
                logger.error(f"Unexpected error fetching audit logs: {e}")
                logger.info(f"Waiting {self.settings.poll_interval} seconds before retry")
                await asyncio.sleep(self.settings.poll_interval)
                continue

            # Process the batch
            await self.processor.process_batch(response.events, cursor)

            # Handle pagination
            if response.next_cursor:
                self.processor.reset_deduplication()
                logger.info(
                    f"More data available, moving to next page "
                    f"(cursor={response.next_cursor[:20]}...)"
                )
                cursor = response.next_cursor
                continue

            # No more data - wait before next poll
            logger.info(
                f"No more data available, waiting {self.settings.poll_interval} "
                "seconds before next check"
            )
            self.processor.enable_deduplication()
            await asyncio.sleep(self.settings.poll_interval)
