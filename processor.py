import logging
from dataclasses import dataclass

from savers import EventSaver
from state import EventState, StateManager

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """Result of processing a batch of events."""

    saved_count: int
    found_last_event: bool


class EventProcessor:
    """Handles event deduplication and saving."""

    def __init__(self, state_manager: StateManager, saver: EventSaver):
        self.state_manager = state_manager
        self.saver = saver
        self._state: EventState = state_manager.get_state()
        self._needs_dedup: bool = self._state.is_resumable()

    @property
    def cursor(self) -> str | None:
        """Current cursor position."""
        return self._state.cursor

    @property
    def needs_deduplication(self) -> bool:
        """Whether we need to check for duplicate events."""
        return self._needs_dedup

    def reset_deduplication(self) -> None:
        """Reset deduplication flag (called when moving to next page)."""
        self._needs_dedup = False

    def enable_deduplication(self) -> None:
        """Enable deduplication (called when caught up and waiting)."""
        self._needs_dedup = True

    async def process_batch(
        self, events: list[dict], cursor: str | None
    ) -> ProcessResult:
        """
        Process a batch of events, handling deduplication if needed.

        Args:
            events: List of events from the API
            cursor: Current cursor value

        Returns:
            ProcessResult with count of saved events and dedup status
        """
        if not events:
            logger.info("No events in batch")
            return ProcessResult(saved_count=0, found_last_event=True)

        if not self._needs_dedup:
            # Fresh start or moved to new page - save all events
            logger.info(f"Saving {len(events)} new events")
            await self.saver.add_events(events)
            self._update_state(events[-1], cursor)
            return ProcessResult(saved_count=len(events), found_last_event=True)

        # Need to deduplicate - find last saved event
        logger.info("Checking for events after last saved event")
        return await self._process_with_dedup(events, cursor)

    async def _process_with_dedup(
        self, events: list[dict], cursor: str | None
    ) -> ProcessResult:
        """Process events with deduplication logic."""
        for i, event in enumerate(events):
            if self._matches_last_event(event):
                if i == len(events) - 1:
                    logger.info("Last event found at end of batch, no new events")
                    return ProcessResult(saved_count=0, found_last_event=True)

                new_events = events[i + 1 :]
                logger.info(f"Found {len(new_events)} new events after last saved event")
                await self.saver.add_events(new_events)
                self._update_state(events[-1], cursor)
                return ProcessResult(saved_count=len(new_events), found_last_event=True)

        logger.warning("Last event not found in current batch")
        return ProcessResult(saved_count=0, found_last_event=False)

    def _matches_last_event(self, event: dict) -> bool:
        """Check if event matches the last saved event."""
        return (
            event.get("event_id") == self._state.event_id
            and event.get("event_saved_time") == self._state.event_saved_time
        )

    def _update_state(self, last_event: dict, cursor: str | None) -> None:
        """Update and persist state with the last processed event."""
        self._state = EventState(
            event_id=last_event["event_id"],
            event_saved_time=last_event["event_saved_time"],
            cursor=cursor,
        )
        self.state_manager.save_state(self._state)
