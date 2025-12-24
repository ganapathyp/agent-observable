"""Centralized decision logging."""
from __future__ import annotations

import json
import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional, Callable, Any

from .decision import PolicyDecision

logger = logging.getLogger(__name__)


class DecisionLogger:
    """Centralized decision logging."""

    def __init__(
        self,
        log_file: Optional[Path] = None,
        db_url: Optional[str] = None,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        metrics_callback: Optional[Callable[[str, float], None]] = None,
    ):
        """Initialize decision logger.

        Args:
            log_file: Optional path to log file (JSONL format)
            db_url: Optional database URL (not implemented yet)
            batch_size: Number of decisions to batch before flushing
            flush_interval: Seconds between automatic flushes
            metrics_callback: Optional callback for tracking metrics (name, value)
        """
        self.log_file = log_file
        self.db_url = db_url
        self.batch: List[PolicyDecision] = []
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._flush_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._metrics_callback = metrics_callback

    async def start(self) -> None:
        """Start the background flush task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop(self) -> None:
        """Stop the background flush task and flush remaining decisions."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self.flush()

    async def log_decision(self, decision: PolicyDecision) -> None:
        """Log a policy decision.

        Args:
            decision: Policy decision to log
        """
        should_flush = False
        async with self._lock:
            self.batch.append(decision)
            if len(self.batch) >= self.batch_size:
                should_flush = True

        # Flush outside the lock to avoid deadlock
        if should_flush:
            await self.flush()

    async def flush(self) -> None:
        """Flush batched decisions."""
        flush_start = time.time()

        async with self._lock:
            if not self.batch:
                return

            decisions_to_flush = self.batch.copy()
            self.batch.clear()

        # Write to file
        if self.log_file:
            try:
                await self._write_to_file(decisions_to_flush)
            except Exception as e:
                logger.error(f"Error writing decisions to file: {e}", exc_info=True)

        # Write to database (if configured)
        if self.db_url:
            try:
                await self._write_to_db(decisions_to_flush)
            except Exception as e:
                logger.error(f"Error writing decisions to database: {e}", exc_info=True)

        # Track flush latency via callback if provided
        flush_latency = (time.time() - flush_start) * 1000
        if self._metrics_callback:
            try:
                self._metrics_callback("decision_log_flush_latency_ms", flush_latency)
            except Exception:
                pass  # Don't fail on metrics tracking

    async def _write_to_file(self, decisions: List[PolicyDecision]) -> None:
        """Write decisions to file (JSONL format).

        Args:
            decisions: List of decisions to write
        """
        if not self.log_file:
            return

        # Ensure directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Use executor for file I/O to avoid blocking the event loop
        def _write_sync():
            with open(self.log_file, "a", encoding="utf-8") as f:
                for decision in decisions:
                    decision_dict = decision.to_dict()
                    f.write(json.dumps(decision_dict, default=str) + "\n")

                    # Also log to Python logger for structured logging
                    context = decision_dict.get("context", {})

                    # Build extra fields for logging
                    extra_fields: dict[str, Any] = {
                        "log_type": "policy_decision",
                        "decision_id": decision_dict.get("decision_id"),
                        "decision_type": decision.decision_type.value,
                        "result": decision.result.value,
                        "reason": decision_dict.get("reason"),
                        "tool_name": context.get("tool_name") or decision_dict.get("tool_name"),
                        "agent_id": context.get("agent_id") or decision_dict.get("agent_id"),
                        "latency_ms": decision_dict.get("latency_ms"),
                        "request_id": context.get("request_id"),
                        "timestamp": decision_dict.get("timestamp"),
                        "policy_version": decision_dict.get("policy_version"),
                    }

                    # Add context fields
                    if context:
                        for key, value in context.items():
                            if key not in ["tool_name", "agent_id", "request_id"]:
                                extra_fields[f"context_{key}"] = value

                    logger.info(
                        f"[POLICY] {decision.decision_type.value} decision: {decision.result.value}",
                        extra=extra_fields,
                    )

        # Run file I/O in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_sync)

    async def _write_to_db(self, decisions: List[PolicyDecision]) -> None:
        """Write decisions to database (placeholder for future implementation).

        Args:
            decisions: List of decisions to write
        """
        # TODO: Implement database writing
        logger.debug(f"Would write {len(decisions)} decisions to database")

    async def _periodic_flush(self) -> None:
        """Periodically flush decisions."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}", exc_info=True)
