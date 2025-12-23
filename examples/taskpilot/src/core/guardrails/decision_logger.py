"""Centralized decision logging."""
import json
import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from taskpilot.core.guardrails.decision_log import PolicyDecision  # type: ignore

logger = logging.getLogger(__name__)


class DecisionLogger:
    """Centralized decision logging."""

    def __init__(
        self,
        log_file: Optional[Path] = None,
        db_url: Optional[str] = None,
        batch_size: int = 100,
        flush_interval: float = 5.0,
    ):
        """Initialize decision logger.

        Args:
            log_file: Optional path to log file (JSONL format)
            db_url: Optional database URL (not implemented yet)
            batch_size: Number of decisions to batch before flushing
            flush_interval: Seconds between automatic flushes
        """
        self.log_file = log_file
        self.db_url = db_url
        self.batch: List[PolicyDecision] = []
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._flush_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the background flush task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop(self):
        """Stop the background flush task and flush remaining decisions."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self.flush()

    async def log_decision(self, decision: PolicyDecision):
        """Log a policy decision.

        Args:
            decision: Policy decision to log
        """
        async with self._lock:
            self.batch.append(decision)

            if len(self.batch) >= self.batch_size:
                await self.flush()

    async def flush(self):
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
        
        # Track flush latency
        flush_latency = (time.time() - flush_start) * 1000
        try:
            from taskpilot.core.observability import get_metrics_collector
            from taskpilot.core.metric_names import OBSERVABILITY_DECISION_LOG_FLUSH_LATENCY_MS
            metrics = get_metrics_collector()
            metrics.record_histogram(OBSERVABILITY_DECISION_LOG_FLUSH_LATENCY_MS, flush_latency)
        except Exception:
            pass  # Don't fail on metrics tracking

    async def _write_to_file(self, decisions: List[PolicyDecision]):
        """Write decisions to file (JSONL format).

        Args:
            decisions: List of decisions to write
        """
        if not self.log_file:
            return

        # Ensure directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.log_file, "a", encoding="utf-8") as f:
            for decision in decisions:
                decision_dict = decision.to_dict()
                f.write(json.dumps(decision_dict, default=str) + "\n")
                
                # Also log to Python logger for Kibana (via Filebeat)
                # This makes decision logs available in Kibana alongside application logs
                context = decision_dict.get("context", {})
                
                # Build extra fields for logging - include all context fields
                extra_fields = {
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
                    "policy_version": decision_dict.get("policy_version")
                }
                
                # Add context fields (like task_id for human approvals)
                if context:
                    for key, value in context.items():
                        if key not in ["tool_name", "agent_id", "request_id"]:  # Avoid duplicates
                            extra_fields[f"context_{key}"] = value
                
                logger.info(
                    f"[POLICY] {decision.decision_type.value} decision: {decision.result.value}",
                    extra=extra_fields
                )

    async def _write_to_db(self, decisions: List[PolicyDecision]):
        """Write decisions to database (placeholder for future implementation).

        Args:
            decisions: List of decisions to write
        """
        # TODO: Implement database writing
        # For now, just log that we would write to DB
        logger.debug(f"Would write {len(decisions)} decisions to database")

    async def _periodic_flush(self):
        """Periodically flush decisions."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}", exc_info=True)


# Global decision logger instance
_decision_logger: Optional[DecisionLogger] = None


def get_decision_logger() -> DecisionLogger:
    """Get the global decision logger instance.

    Returns:
        Global DecisionLogger instance
    """
    global _decision_logger
    if _decision_logger is None:
        # Use configured path from PathConfig
        try:
            from taskpilot.core.config import get_paths
            paths = get_paths()
            log_file = paths.decision_logs_file
        except Exception:
            # Fallback to old behavior if config not available
            from pathlib import Path
            taskpilot_dir = Path(__file__).parent.parent.parent.parent
            log_file = taskpilot_dir / "decision_logs.jsonl"
        _decision_logger = DecisionLogger(log_file=log_file)
    return _decision_logger


def set_decision_logger(logger_instance: DecisionLogger):
    """Set the global decision logger instance (for testing).

    Args:
        logger_instance: DecisionLogger instance to use
    """
    global _decision_logger
    _decision_logger = logger_instance
