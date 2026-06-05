"""
analytics.py
─────────────
Event tracking and analytics integration.

Supports:
- Segment.io (recommended)
- Mixpanel
- Amplitude
- Google Analytics
- Custom event tracking

Usage:
    from backend.analytics import get_analytics
    
    analytics = get_analytics()
    
    # Track event
    analytics.track(
        user_id="user_123",
        event="onboarding_completed",
        properties={
            "team": "engineering",
            "duration_seconds": 345,
        }
    )
    
    # Identify user
    analytics.identify(
        user_id="user_123",
        traits={
            "email": "user@company.com",
            "team": "engineering",
        }
    )
"""

import os
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel

from backend.logging_config import get_logger

logger = get_logger(__name__)


class Event(BaseModel):
    """Analytics event."""
    
    user_id: str
    event: str
    properties: dict[str, Any] = {}
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    
    class Config:
        extra = "allow"


class UserTraits(BaseModel):
    """User traits for identification."""
    
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    team: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    created_at: Optional[str] = None
    
    class Config:
        extra = "allow"


class Analytics:
    """Base analytics client."""
    
    def __init__(self, enabled: bool = True):
        """Initialize analytics."""
        self.enabled = enabled
        if not enabled:
            logger.info("Analytics disabled")
    
    def track(
        self,
        user_id: str,
        event: str,
        properties: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Track an event."""
        if not self.enabled:
            return
        
        event_data = Event(
            user_id=user_id,
            event=event,
            properties=properties or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
            **kwargs,
        )
        
        self._track_impl(event_data)
        
        logger.debug(
            "Event tracked",
            extra={
                "user_id": user_id,
                "event": event,
                "properties": properties,
            }
        )
    
    def identify(
        self,
        user_id: str,
        traits: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Identify a user."""
        if not self.enabled:
            return
        
        user_traits = UserTraits(
            user_id=user_id,
            **(traits or {}),
            **kwargs,
        )
        
        self._identify_impl(user_traits)
        
        logger.debug(
            "User identified",
            extra={
                "user_id": user_id,
                "traits": traits,
            }
        )
    
    def group(
        self,
        user_id: str,
        group_id: str,
        traits: Optional[dict[str, Any]] = None,
    ) -> None:
        """Associate user with a group/company."""
        if not self.enabled:
            return
        
        self._group_impl(user_id, group_id, traits or {})
    
    def page(
        self,
        user_id: str,
        page: str,
        properties: Optional[dict[str, Any]] = None,
    ) -> None:
        """Track page view."""
        if not self.enabled:
            return
        
        self._page_impl(user_id, page, properties or {})
    
    def _track_impl(self, event: Event) -> None:
        """Subclasses implement actual tracking."""
        pass
    
    def _identify_impl(self, traits: UserTraits) -> None:
        """Subclasses implement actual identification."""
        pass
    
    def _group_impl(self, user_id: str, group_id: str, traits: dict) -> None:
        """Subclasses implement group association."""
        pass
    
    def _page_impl(self, user_id: str, page: str, properties: dict) -> None:
        """Subclasses implement page tracking."""
        pass


class SegmentAnalytics(Analytics):
    """Segment.io integration (recommended)."""
    
    def __init__(self, write_key: str):
        """Initialize Segment client."""
        super().__init__(enabled=bool(write_key))
        
        if write_key:
            try:
                import analytics
                self.client = analytics.Client(write_key)
                logger.info("Segment.io analytics enabled")
            except ImportError:
                logger.warning("segment-analytics not installed, disabling Segment")
                self.enabled = False
        else:
            self.client = None
    
    def _track_impl(self, event: Event) -> None:
        """Track event via Segment."""
        if not self.client:
            return
        
        try:
            self.client.track(
                event.user_id,
                event.event,
                event.properties,
                {"timestamp": event.timestamp},
            )
        except Exception as e:
            logger.error(
                "Segment track failed",
                extra={"error": str(e), "event": event.event},
            )
    
    def _identify_impl(self, traits: UserTraits) -> None:
        """Identify user via Segment."""
        if not self.client:
            return
        
        try:
            self.client.identify(
                traits.user_id,
                traits.dict(exclude_none=True),
            )
        except Exception as e:
            logger.error(
                "Segment identify failed",
                extra={"error": str(e), "user_id": traits.user_id},
            )
    
    def _group_impl(self, user_id: str, group_id: str, traits: dict) -> None:
        """Group user via Segment."""
        if not self.client:
            return
        
        try:
            self.client.group(user_id, group_id, traits)
        except Exception as e:
            logger.error(
                "Segment group failed",
                extra={"error": str(e), "user_id": user_id},
            )


class MixpanelAnalytics(Analytics):
    """Mixpanel integration."""
    
    def __init__(self, token: str):
        """Initialize Mixpanel client."""
        super().__init__(enabled=bool(token))
        
        if token:
            try:
                from mixpanel import Mixpanel
                self.client = Mixpanel(token)
                logger.info("Mixpanel analytics enabled")
            except ImportError:
                logger.warning("mixpanel-python not installed, disabling Mixpanel")
                self.enabled = False
        else:
            self.client = None
    
    def _track_impl(self, event: Event) -> None:
        """Track event via Mixpanel."""
        if not self.client:
            return
        
        try:
            self.client.track(
                event.user_id,
                event.event,
                event.properties,
            )
        except Exception as e:
            logger.error(
                "Mixpanel track failed",
                extra={"error": str(e), "event": event.event},
            )
    
    def _identify_impl(self, traits: UserTraits) -> None:
        """Identify user via Mixpanel."""
        if not self.client:
            return
        
        try:
            self.client.people_set(
                traits.user_id,
                traits.dict(exclude_none=True),
            )
        except Exception as e:
            logger.error(
                "Mixpanel identify failed",
                extra={"error": str(e), "user_id": traits.user_id},
            )


class GoogleAnalyticsClient(Analytics):
    """Google Analytics integration."""
    
    def __init__(self, tracking_id: str):
        """Initialize Google Analytics client."""
        super().__init__(enabled=bool(tracking_id))
        
        if tracking_id:
            try:
                from google_analytics_python_client import Client
                self.client = Client(tracking_id)
                logger.info("Google Analytics enabled")
            except ImportError:
                logger.warning("google-analytics-python-client not installed")
                self.enabled = False
        else:
            self.client = None
    
    def _track_impl(self, event: Event) -> None:
        """Track event via Google Analytics."""
        if not self.client:
            return
        
        try:
            self.client.track(
                event.user_id,
                event.event,
                event.properties,
            )
        except Exception as e:
            logger.error(
                "Google Analytics track failed",
                extra={"error": str(e)},
            )


class LoggingAnalytics(Analytics):
    """Fallback analytics that just logs events."""
    
    def __init__(self):
        """Initialize logging analytics."""
        super().__init__(enabled=True)
    
    def _track_impl(self, event: Event) -> None:
        """Log event."""
        logger.info(
            f"[Analytics] {event.event}",
            extra={
                "user_id": event.user_id,
                "event": event.event,
                "properties": event.properties,
                "session_id": event.session_id,
            }
        )
    
    def _identify_impl(self, traits: UserTraits) -> None:
        """Log user identification."""
        logger.info(
            f"[Analytics] User identified",
            extra={
                "user_id": traits.user_id,
                "email": traits.email,
                "team": traits.team,
            }
        )


def get_analytics() -> Analytics:
    """
    Get configured analytics client.
    
    Priority:
    1. Segment.io (if SEGMENT_WRITE_KEY set)
    2. Mixpanel (if MIXPANEL_TOKEN set)
    3. Google Analytics (if GOOGLE_ANALYTICS_ID set)
    4. Logging fallback
    """
    segment_key = os.getenv("SEGMENT_WRITE_KEY")
    if segment_key:
        return SegmentAnalytics(segment_key)
    
    mixpanel_token = os.getenv("MIXPANEL_TOKEN")
    if mixpanel_token:
        return MixpanelAnalytics(mixpanel_token)
    
    ga_id = os.getenv("GOOGLE_ANALYTICS_ID")
    if ga_id:
        return GoogleAnalyticsClient(ga_id)
    
    # Fallback to logging
    return LoggingAnalytics()


# Global analytics instance
_analytics_instance: Optional[Analytics] = None


def get_analytics_instance() -> Analytics:
    """Get or create global analytics instance."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = get_analytics()
    return _analytics_instance
