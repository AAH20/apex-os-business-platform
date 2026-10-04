"""Retry policies for saga steps."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Set, Type


class BackoffStrategy(Enum):
    """Backoff strategies for retries."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_WITH_JITTER = "exponential_with_jitter"


@dataclass
class RetryPolicy:
    """Configuration for retrying a failed step."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    multiplier: float = 2.0
    jitter_factor: float = 0.1
    retryable_exceptions: Optional[Set[Type[Exception]]] = None
    non_retryable_exceptions: Optional[Set[Type[Exception]]] = None
    on_retry: Optional[Callable[[int, float, Exception], None]] = None

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if a failed attempt should be retried."""
        if attempt >= self.max_retries:
            return False
        if self.non_retryable_exceptions and type(exception) in self.non_retryable_exceptions:
            return False
        if self.retryable_exceptions and type(exception) not in self.retryable_exceptions:
            return False
        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate the delay before the next retry attempt."""
        if self.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.initial_delay
        elif self.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.initial_delay * (attempt + 1)
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.multiplier ** attempt)
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL_WITH_JITTER:
            base = self.initial_delay * (self.multiplier ** attempt)
            jitter = base * self.jitter_factor * (2 * random.random() - 1)
            delay = base + jitter
        else:
            delay = self.initial_delay

        return min(delay, self.max_delay)


class RetryExecutor:
    """Executes a callable with retry logic."""

    def __init__(self, policy: Optional[RetryPolicy] = None) -> None:
        self.policy = policy or RetryPolicy()

    def execute(
        self,
        fn: Callable,
        *args,
        **kwargs,
    ) -> tuple[bool, any, Optional[Exception]]:
        """Execute a function with retries.

        Returns (success, result, last_exception).
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.policy.max_retries + 1):
            try:
                result = fn(*args, **kwargs)
                return True, result, None
            except Exception as e:
                last_exception = e
                if not self.policy.should_retry(attempt, e):
                    break
                if attempt < self.policy.max_retries:
                    delay = self.policy.get_delay(attempt)
                    if self.policy.on_retry:
                        self.policy.on_retry(attempt + 1, delay, e)
                    time.sleep(delay)

        return False, None, last_exception

    def execute_with_timeout(
        self,
        fn: Callable,
        timeout: float,
        *args,
        **kwargs,
    ) -> tuple[bool, any, Optional[Exception]]:
        """Execute a function with retries and a timeout per attempt.

        Returns (success, result, last_exception).
        """
        import concurrent.futures

        last_exception: Optional[Exception] = None

        for attempt in range(self.policy.max_retries + 1):
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(fn, *args, **kwargs)
                    result = future.result(timeout=timeout)
                    return True, result, None
            except concurrent.futures.TimeoutError as e:
                last_exception = e
                if not self.policy.should_retry(attempt, e):
                    break
                if attempt < self.policy.max_retries:
                    delay = self.policy.get_delay(attempt)
                    if self.policy.on_retry:
                        self.policy.on_retry(attempt + 1, delay, e)
                    time.sleep(delay)
            except Exception as e:
                last_exception = e
                if not self.policy.should_retry(attempt, e):
                    break
                if attempt < self.policy.max_retries:
                    delay = self.policy.get_delay(attempt)
                    if self.policy.on_retry:
                        self.policy.on_retry(attempt + 1, delay, e)
                    time.sleep(delay)

        return False, None, last_exception
