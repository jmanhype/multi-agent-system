"""Sandbox execution with resource limits and timeout enforcement.

Implements FR-024 to FR-026: Sandbox execution, timeout enforcement, resource monitoring.
"""

import signal
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
import psutil


@dataclass
class ResourceQuota:
    """Resource limits for sandbox execution."""
    max_memory_mb: int = 1024
    max_cpu_percent: float = 80.0
    max_execution_seconds: float = 30.0
    max_rows: int = 10000


@dataclass
class SandboxResult:
    """Result from sandboxed execution."""
    success: bool
    result: Any
    error: Optional[str]
    execution_time_seconds: float
    peak_memory_mb: float
    avg_cpu_percent: float
    violations: list


class SandboxTimeoutError(Exception):
    """Execution exceeded timeout."""
    pass


class SandboxResourceError(Exception):
    """Resource limit exceeded."""
    pass


class SandboxExecutor:
    """Execute operations with resource monitoring and limits.
    
    Features:
    - Timeout enforcement (FR-025)
    - Memory monitoring (FR-026)
    - CPU usage tracking (FR-026)
    - Graceful degradation on resource violations
    """
    
    def __init__(self, quota: Optional[ResourceQuota] = None):
        """Initialize sandbox executor.
        
        Args:
            quota: Resource limits (uses defaults if None)
        """
        self.quota = quota or ResourceQuota()
        self._process = psutil.Process()
    
    def execute_in_sandbox(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> SandboxResult:
        """Execute function with resource monitoring.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            SandboxResult with execution metrics
        """
        start_time = time.time()
        violations = []
        
        initial_memory = self._get_memory_usage_mb()
        peak_memory = initial_memory
        cpu_samples = []
        
        result = None
        error = None
        success = False
        
        try:
            with self._timeout_handler(self.quota.max_execution_seconds):
                memory_before = self._get_memory_usage_mb()
                
                result = func(*args, **kwargs)
                
                memory_after = self._get_memory_usage_mb()
                peak_memory = max(peak_memory, memory_after)
                
                if memory_after - initial_memory > self.quota.max_memory_mb:
                    violations.append(
                        f"Memory usage exceeded limit: "
                        f"{memory_after - initial_memory:.1f}MB > {self.quota.max_memory_mb}MB"
                    )
                
                cpu_samples.append(self._process.cpu_percent(interval=0.1))
                
                success = True
        
        except SandboxTimeoutError as e:
            error = f"Execution timeout: {str(e)}"
            violations.append(f"Timeout exceeded: {self.quota.max_execution_seconds}s")
        
        except MemoryError as e:
            error = f"Memory exhausted: {str(e)}"
            violations.append("Memory exhausted")
        
        except Exception as e:
            error = f"Execution error: {str(e)}"
            success = False
        
        execution_time = time.time() - start_time
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
        
        return SandboxResult(
            success=success,
            result=result,
            error=error,
            execution_time_seconds=execution_time,
            peak_memory_mb=peak_memory - initial_memory,
            avg_cpu_percent=avg_cpu,
            violations=violations,
        )
    
    @contextmanager
    def _timeout_handler(self, seconds: float):
        """Context manager for timeout enforcement.
        
        Args:
            seconds: Timeout in seconds
        
        Raises:
            SandboxTimeoutError: If execution exceeds timeout
        """
        def timeout_handler(signum, frame):
            raise SandboxTimeoutError(f"Execution exceeded {seconds}s timeout")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(seconds))
        
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            memory_info = self._process.memory_info()
            return memory_info.rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    def monitor_resources(self) -> Dict[str, float]:
        """Get current resource usage metrics.
        
        Returns:
            Dict with memory_mb, cpu_percent
        """
        return {
            "memory_mb": self._get_memory_usage_mb(),
            "cpu_percent": self._process.cpu_percent(interval=0.1),
        }


class DockerSandbox:
    """Docker-based sandbox for production isolation.
    
    NOTE: This is a placeholder for production deployment.
    Production systems should use Docker/gVisor for true process isolation.
    
    Features (to be implemented):
    - Container-based execution
    - Network isolation
    - Filesystem isolation
    - Resource limits via cgroups
    """
    
    def __init__(self, image: str = "python:3.11-slim"):
        """Initialize Docker sandbox.
        
        Args:
            image: Docker image to use
        """
        self.image = image
        raise NotImplementedError(
            "Docker sandbox is not yet implemented. "
            "For MVP, use SandboxExecutor with Python-level resource limits. "
            "Production deployment should implement this class using docker-py."
        )
    
    def execute(self, code: str, timeout: float = 30.0) -> Dict[str, Any]:
        """Execute code in isolated Docker container.
        
        Args:
            code: Python code to execute
            timeout: Execution timeout
        
        Returns:
            Execution result with stdout, stderr, exit_code
        """
        raise NotImplementedError("Docker sandbox not implemented")