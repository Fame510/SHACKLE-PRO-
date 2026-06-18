#!/usr/bin/env python3
"""
SHACKLE Client - Thin decorator for tool execution with daemon/fallback support
Auto-detects daemon availability and falls back to local execution
"""

import asyncio
import functools
import httpx
import json
import logging
import os
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ShackleClient:
    """Client for SHACKLE daemon with automatic fallback"""
    
    def __init__(
        self,
        socket_path: Optional[str] = None,
        session_id: Optional[str] = None,
        fallback_mode: bool = True
    ):
        self.socket_path = socket_path or os.getenv("SHACKLE_SOCKET", "/tmp/shackle.sock")
        self.session_id = session_id or os.getenv("SHACKLE_SESSION", "default")
        self.fallback_mode = fallback_mode
        self._daemon_available: Optional[bool] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> Optional[httpx.AsyncClient]:
        """Get or create HTTP client for Unix socket"""
        if self._client is None:
            try:
                # Create client with Unix socket transport
                transport = httpx.AsyncHTTPTransport(uds=self.socket_path)
                self._client = httpx.AsyncClient(
                    transport=transport,
                    base_url="http://localhost",
                    timeout=30.0
                )
            except Exception as e:
                logger.warning(f"Failed to create daemon client: {e}")
                return None
        return self._client
    
    async def check_daemon(self) -> bool:
        """Check if daemon is available"""
        if self._daemon_available is not None:
            return self._daemon_available
        
        try:
            client = await self._get_client()
            if client is None:
                self._daemon_available = False
                return False
            
            resp = await client.get("/health", timeout=2.0)
            self._daemon_available = resp.status_code == 200
            
            if self._daemon_available:
                logger.info("SHACKLE daemon detected and available")
            
            return self._daemon_available
            
        except Exception as e:
            logger.debug(f"Daemon not available: {e}")
            self._daemon_available = False
            return False
    
    async def pre_exec(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        estimated_cost: float = 0.0,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Pre-execution check
        Returns: {"decision": "ALLOW|DENY|HITL", "reason": "...", "hitl_token": "..."}
        """
        # Check if daemon is available
        if not await self.check_daemon():
            if self.fallback_mode:
                logger.debug(f"Daemon unavailable, allowing {tool_name} (fallback mode)")
                return {"decision": "ALLOW", "reason": "Fallback mode - daemon unavailable"}
            else:
                return {"decision": "DENY", "reason": "Daemon unavailable and fallback disabled"}
        
        try:
            client = await self._get_client()
            resp = await client.post("/pre_exec", json={
                "session_id": self.session_id,
                "tool_name": tool_name,
                "parameters": parameters,
                "estimated_cost": estimated_cost,
                "context": context
            })
            
            resp.raise_for_status()
            result = resp.json()
            
            # Handle HITL (blocking wait)
            if result["decision"] == "HITL":
                hitl_token = result.get("hitl_token")
                if hitl_token:
                    logger.info(f"HITL triggered for {tool_name}, waiting for human response...")
                    
                    # Wait for HITL response
                    hitl_resp = await client.get(f"/hitl_wait/{hitl_token}")
                    hitl_resp.raise_for_status()
                    hitl_data = hitl_resp.json()
                    
                    # Update decision based on human response
                    result["decision"] = hitl_data["decision"]
                    result["reason"] = hitl_data.get("notes", result.get("reason"))
            
            return result
            
        except Exception as e:
            logger.error(f"Error in pre_exec: {e}", exc_info=True)
            if self.fallback_mode:
                return {"decision": "ALLOW", "reason": f"Fallback mode - error: {e}"}
            else:
                return {"decision": "DENY", "reason": f"Daemon error: {e}"}
    
    async def post_exec(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Optional[Any] = None,
        error: Optional[str] = None,
        actual_cost: float = 0.0,
        execution_time_ms: float = 0.0
    ) -> Dict[str, Any]:
        """
        Post-execution logging
        Returns: {"status": "ACK|ERROR", "message": "..."}
        """
        if not await self.check_daemon():
            if self.fallback_mode:
                logger.debug(f"Daemon unavailable, skipping post_exec for {tool_name}")
                return {"status": "ACK", "message": "Fallback mode - logging skipped"}
            else:
                return {"status": "ERROR", "message": "Daemon unavailable"}
        
        try:
            client = await self._get_client()
            resp = await client.post("/post_exec", json={
                "session_id": self.session_id,
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "error": error,
                "actual_cost": actual_cost,
                "execution_time_ms": execution_time_ms
            })
            
            resp.raise_for_status()
            return resp.json()
            
        except Exception as e:
            logger.error(f"Error in post_exec: {e}", exc_info=True)
            return {"status": "ERROR", "message": str(e)}
    
    async def close(self):
        """Close the client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Decorator for automatic SHACKLE integration
def shackled(
    tool_name: Optional[str] = None,
    estimate_cost: Optional[Callable] = None,
    client: Optional[ShackleClient] = None
):
    """
    Decorator to wrap tool functions with SHACKLE governance
    
    Usage:
        @shackled(tool_name="my_tool", estimate_cost=lambda *args, **kwargs: 0.01)
        async def my_tool(arg1, arg2):
            # tool implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        _tool_name = tool_name or func.__name__
        _client = client or ShackleClient()
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Estimate cost
            estimated_cost = 0.0
            if estimate_cost:
                try:
                    estimated_cost = estimate_cost(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Cost estimation failed: {e}")
            
            # Pre-execution check
            pre_result = await _client.pre_exec(
                tool_name=_tool_name,
                parameters={"args": args, "kwargs": kwargs},
                estimated_cost=estimated_cost
            )
            
            decision = pre_result.get("decision")
            
            if decision == "DENY":
                reason = pre_result.get("reason", "No reason provided")
                raise PermissionError(f"SHACKLE denied execution: {reason}")
            
            # Execute the tool
            result = None
            error = None
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                error = str(e)
                raise
            finally:
                # Post-execution logging
                execution_time_ms = (time.time() - start_time) * 1000
                
                await _client.post_exec(
                    tool_name=_tool_name,
                    parameters={"args": args, "kwargs": kwargs},
                    result=result,
                    error=error,
                    actual_cost=estimated_cost,  # Use estimated for now
                    execution_time_ms=execution_time_ms
                )
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Example usage and testing
async def example_usage():
    """Example of using SHACKLE client"""
    
    # Initialize client
    client = ShackleClient(session_id="example_session")
    
    # Define a tool with decorator
    @shackled(tool_name="example_tool", estimate_cost=lambda x: 0.01, client=client)
    async def example_tool(value: str):
        print(f"Executing tool with value: {value}")
        await asyncio.sleep(0.1)
        return {"result": f"processed_{value}"}
    
    # Use the tool - SHACKLE will automatically govern it
    try:
        result = await example_tool("test_value")
        print(f"Tool result: {result}")
    except PermissionError as e:
        print(f"Tool execution denied: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
