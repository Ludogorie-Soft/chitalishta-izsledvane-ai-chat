"""Rate limiting and abuse protection service."""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import BlockedIP, RateLimitState, RateLimitViolation

logger = structlog.get_logger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, limit_type: str, retry_after: int):
        self.limit_type = limit_type  # 'minute', 'hour', 'day'
        self.retry_after = retry_after  # Seconds until retry is allowed
        super().__init__(f"Rate limit exceeded: {limit_type}")


class AbuseDetected(Exception):
    """Exception raised when abuse is detected."""

    def __init__(self, abuse_type: str, details: dict):
        self.abuse_type = abuse_type
        self.details = details
        super().__init__(f"Abuse detected: {abuse_type}")


class RateLimiter:
    """Rate limiting and abuse protection service using PostgreSQL storage."""

    def __init__(self, db: Session):
        """
        Initialize rate limiter.

        Args:
            db: Database session
        """
        self.db = db
        self.enabled = settings.rate_limit_enabled
        self.abuse_protection_enabled = settings.abuse_protection_enabled

    def check_rate_limit(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        method: str = "POST",
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is within rate limits.

        Args:
            identifier: IP address or conversation_id
            identifier_type: 'ip' or 'session'
            endpoint: API endpoint path
            method: HTTP method

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
            - is_allowed: True if request is allowed, False if rate limited
            - retry_after_seconds: Seconds until retry is allowed (None if allowed)

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        if not self.enabled:
            return True, None

        now = datetime.utcnow()

        # Get or create rate limit state
        state = (
            self.db.query(RateLimitState)
            .filter(
                and_(
                    RateLimitState.identifier == identifier,
                    RateLimitState.identifier_type == identifier_type,
                )
            )
            .first()
        )

        if not state:
            # Create new state
            state = RateLimitState(
                identifier=identifier,
                identifier_type=identifier_type,
                requests_minute=0,
                requests_hour=0,
                requests_day=0,
                last_request_at=now,
            )
            self.db.add(state)
            self.db.flush()

        # Check and update minute window
        if state.first_request_minute is None:
            state.first_request_minute = now
            state.requests_minute = 1
        elif (now - state.first_request_minute).total_seconds() < 60:
            state.requests_minute += 1
        else:
            # Reset minute window
            state.first_request_minute = now
            state.requests_minute = 1

        # Check minute limit
        if state.requests_minute > settings.rate_limit_per_minute:
            retry_after = 60 - int((now - state.first_request_minute).total_seconds())
            self._log_violation(
                identifier,
                identifier_type,
                "rate_limit",
                endpoint,
                method,
                limit_exceeded="minute",
                details={"requests": state.requests_minute, "limit": settings.rate_limit_per_minute},
            )
            state.updated_at = now
            self.db.commit()
            raise RateLimitExceeded("minute", retry_after)

        # Check and update hour window
        if state.first_request_hour is None:
            state.first_request_hour = now
            state.requests_hour = 1
        elif (now - state.first_request_hour).total_seconds() < 3600:
            state.requests_hour += 1
        else:
            # Reset hour window
            state.first_request_hour = now
            state.requests_hour = 1

        # Check hour limit
        if state.requests_hour > settings.rate_limit_per_hour:
            retry_after = 3600 - int((now - state.first_request_hour).total_seconds())
            self._log_violation(
                identifier,
                identifier_type,
                "rate_limit",
                endpoint,
                method,
                limit_exceeded="hour",
                details={"requests": state.requests_hour, "limit": settings.rate_limit_per_hour},
            )
            state.updated_at = now
            self.db.commit()
            raise RateLimitExceeded("hour", retry_after)

        # Check and update day window
        if state.first_request_day is None:
            state.first_request_day = now
            state.requests_day = 1
        elif (now - state.first_request_day).total_seconds() < 86400:
            state.requests_day += 1
        else:
            # Reset day window
            state.first_request_day = now
            state.requests_day = 1

        # Check day limit
        if state.requests_day > settings.rate_limit_per_day:
            retry_after = 86400 - int((now - state.first_request_day).total_seconds())
            self._log_violation(
                identifier,
                identifier_type,
                "rate_limit",
                endpoint,
                method,
                limit_exceeded="day",
                details={"requests": state.requests_day, "limit": settings.rate_limit_per_day},
            )
            state.updated_at = now
            self.db.commit()
            raise RateLimitExceeded("day", retry_after)

        # Update last request timestamp
        state.last_request_at = now
        state.updated_at = now
        self.db.commit()

        return True, None

    def check_abuse(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        method: str,
        request_body: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Check for abuse patterns.

        Args:
            identifier: IP address or conversation_id
            identifier_type: 'ip' or 'session'
            endpoint: API endpoint path
            method: HTTP method
            request_body: Request body content (for query length and SQL injection checks)
            user_agent: User agent string

        Raises:
            AbuseDetected: If abuse is detected
        """
        if not self.abuse_protection_enabled:
            return

        now = datetime.utcnow()

        # Check if IP is blocked
        if identifier_type == "ip":
            blocked = (
                self.db.query(BlockedIP)
                .filter(
                    and_(
                        BlockedIP.ip_address == identifier,
                        BlockedIP.blocked_until > now,
                    )
                )
                .first()
            )
            if blocked:
                raise AbuseDetected(
                    "ip_blocked",
                    {
                        "ip": identifier,
                        "blocked_until": blocked.blocked_until.isoformat(),
                        "reason": blocked.block_reason,
                    },
                )

        # Check for very long queries (resource exhaustion)
        if request_body and len(request_body) > settings.abuse_max_query_length:
            self._log_violation(
                identifier,
                identifier_type,
                "abuse_long_query",
                endpoint,
                method,
                details={"query_length": len(request_body), "max_length": settings.abuse_max_query_length},
            )
            if identifier_type == "ip":
                self._block_ip(identifier, "abuse_long_query", {"query_length": len(request_body)})
            raise AbuseDetected(
                "long_query",
                {"query_length": len(request_body), "max_length": settings.abuse_max_query_length},
            )

        # Note: SQL injection detection is NOT performed here because:
        # 1. User queries are natural language (Bulgarian), not SQL
        # 2. The SQL agent (sql_agent.py) has comprehensive validation:
        #    - Blocks dangerous keywords (DELETE, DROP, etc.)
        #    - Enforces SELECT-only queries
        #    - Validates column names
        #    - Sanitizes all SQL queries
        # 3. The SQL agent is the proper security layer for SQL safety
        # 4. Pattern matching on natural language causes false positives
        # If SQL injection detection is needed, it should be done at the SQL agent level,
        # not on the user's natural language input.

        # Check for rapid repeated requests (DoS)
        if identifier_type == "ip":
            window_start = now - timedelta(seconds=settings.abuse_rapid_requests_window_seconds)
            recent_requests = (
                self.db.query(func.count(RateLimitViolation.id))
                .filter(
                    and_(
                        RateLimitViolation.identifier == identifier,
                        RateLimitViolation.identifier_type == "ip",
                        RateLimitViolation.created_at >= window_start,
                    )
                )
                .scalar()
            )
            if recent_requests >= settings.abuse_max_rapid_requests:
                self._log_violation(
                    identifier,
                    identifier_type,
                    "abuse_dos",
                    endpoint,
                    method,
                    details={
                        "requests_in_window": recent_requests,
                        "window_seconds": settings.abuse_rapid_requests_window_seconds,
                    },
                )
                self._block_ip(identifier, "abuse_dos", {"requests_in_window": recent_requests})
                raise AbuseDetected(
                    "dos",
                    {
                        "requests_in_window": recent_requests,
                        "window_seconds": settings.abuse_rapid_requests_window_seconds,
                    },
                )

    # SQL injection detection removed - see check_abuse() method for explanation
    # The SQL agent (sql_agent.py) provides comprehensive SQL security validation

    def _block_ip(self, ip_address: str, reason: str, details: dict) -> None:
        """
        Block an IP address temporarily.

        Args:
            ip_address: IP address to block
            reason: Reason for blocking
            details: Additional context
        """
        now = datetime.utcnow()
        blocked_until = now + timedelta(hours=settings.abuse_ip_block_duration_hours)

        # Check if IP is already blocked
        existing = self.db.query(BlockedIP).filter(BlockedIP.ip_address == ip_address).first()

        if existing:
            # Update existing block
            existing.blocked_until = blocked_until
            existing.violation_count += 1
            existing.block_details = details
        else:
            # Create new block
            blocked = BlockedIP(
                ip_address=ip_address,
                blocked_at=now,
                blocked_until=blocked_until,
                block_reason=reason,
                violation_count=1,
                block_details=details,
            )
            self.db.add(blocked)

        self.db.commit()

        logger.warning(
            "ip_blocked",
            ip_address=ip_address,
            reason=reason,
            blocked_until=blocked_until.isoformat(),
        )

    def _log_violation(
        self,
        identifier: str,
        identifier_type: str,
        violation_type: str,
        endpoint: str,
        method: str,
        limit_exceeded: Optional[str] = None,
        details: Optional[dict] = None,
        user_agent: Optional[str] = None,
        request_body_preview: Optional[str] = None,
    ) -> None:
        """
        Log a rate limit or abuse violation.

        Args:
            identifier: IP address or conversation_id
            identifier_type: 'ip' or 'session'
            violation_type: Type of violation
            endpoint: API endpoint path
            method: HTTP method
            limit_exceeded: Which limit was exceeded (for rate limit violations)
            details: Additional context
            user_agent: User agent string
            request_body_preview: Preview of request body (first 500 chars)
        """
        violation = RateLimitViolation(
            identifier=identifier,
            identifier_type=identifier_type,
            violation_type=violation_type,
            limit_exceeded=limit_exceeded,
            endpoint=endpoint,
            method=method,
            user_agent=user_agent,
            request_body_preview=request_body_preview[:500] if request_body_preview else None,
            violation_details=details,
        )
        self.db.add(violation)
        self.db.commit()

        logger.warning(
            "rate_limit_violation",
            identifier=identifier,
            identifier_type=identifier_type,
            violation_type=violation_type,
            endpoint=endpoint,
            limit_exceeded=limit_exceeded,
        )

    def cleanup_old_records(self) -> None:
        """
        Clean up old rate limit state and violation records.

        This should be called periodically (e.g., via cron job or background task).
        """
        if not self.enabled:
            return

        now = datetime.utcnow()

        # Clean up old rate limit state (older than 7 days with no recent activity)
        cutoff = now - timedelta(days=7)
        deleted_states = (
            self.db.query(RateLimitState)
            .filter(RateLimitState.last_request_at < cutoff)
            .delete()
        )

        # Clean up old violation logs (older than retention period)
        violation_cutoff = now - timedelta(days=settings.rate_limit_violation_retention_days)
        deleted_violations = (
            self.db.query(RateLimitViolation)
            .filter(RateLimitViolation.created_at < violation_cutoff)
            .delete()
        )

        # Clean up expired IP blocks
        deleted_blocks = (
            self.db.query(BlockedIP)
            .filter(BlockedIP.blocked_until < now)
            .delete()
        )

        self.db.commit()

        logger.info(
            "rate_limit_cleanup",
            deleted_states=deleted_states,
            deleted_violations=deleted_violations,
            deleted_blocks=deleted_blocks,
        )

