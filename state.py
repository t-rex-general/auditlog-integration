import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EventState:
    """Represents the last processed event state."""

    event_id: str | None = None
    event_saved_time: str | None = None
    cursor: str | None = None

    def is_resumable(self) -> bool:
        """Check if we have enough state to resume from last event."""
        return self.event_id is not None and self.event_saved_time is not None


class StateManager:
    """Manages persistent state for token and last processed event."""

    def __init__(
        self, token_file: str = "token.txt", state_file: str = "last_event.txt"
    ):
        self.token_file = token_file
        self.state_file = state_file

    def get_token(self) -> str:
        """Load auth token from file."""
        try:
            with open(self.token_file, "r") as file:
                token = file.read().strip()
                logger.debug("Token loaded from file")
                return token
        except FileNotFoundError:
            logger.warning(f"{self.token_file} not found, returning empty string")
            return ""
        except Exception as e:
            logger.error(f"Failed to read token: {e}")
            raise

    def set_token(self, token: str) -> None:
        """Save auth token to file."""
        try:
            with open(self.token_file, "w") as file:
                file.write(token)
            logger.info("Token saved to file")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
            raise

    def get_state(self) -> EventState:
        """Load last event state from file."""
        try:
            with open(self.state_file, "r") as file:
                content = file.read()
                if not content:
                    logger.info(f"{self.state_file} is empty")
                    return EventState()
                data = json.loads(content)
                state = EventState(
                    event_id=data.get("event_id"),
                    event_saved_time=data.get("event_saved_time"),
                    cursor=data.get("cursor"),
                )
                logger.info(f"State loaded: event_id={state.event_id}")
                return state
        except FileNotFoundError:
            logger.info(f"{self.state_file} not found, starting fresh")
            return EventState()
        except Exception as e:
            logger.error(f"Failed to read state: {e}")
            raise

    def save_state(self, state: EventState) -> None:
        """Save event state to file."""
        try:
            data = {
                "event_id": state.event_id,
                "event_saved_time": state.event_saved_time,
                "cursor": state.cursor,
            }
            with open(self.state_file, "w") as file:
                json.dump(data, file)
            logger.debug(f"State saved: event_id={state.event_id}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise
