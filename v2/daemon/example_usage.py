#!/usr/bin/env python3
"""
Example usage of SHACKLE client decorator
Demonstrates integration patterns
"""

import asyncio
import random
from client import ShackleClient, shackled


# Initialize SHACKLE client
shackle = ShackleClient(
    session_id="example_app",
    fallback_mode=True  # Allow execution if daemon unavailable
)


# Example 1: Simple tool with fixed cost
@shackled(
    tool_name="file_read",
    estimate_cost=lambda path: 0.001,
    client=shackle
)
async def read_file(path: str):
    """Read file with SHACKLE governance"""
    print(f"Reading file: {path}")
    await asyncio.sleep(0.1)  # Simulate I/O
    return {"content": f"Contents of {path}", "size": 1024}


# Example 2: Variable cost based on parameters
def estimate_api_cost(endpoint: str, method: str = "GET"):
    """Estimate cost based on API endpoint"""
    costs = {
        "GET": 0.001,
        "POST": 0.01,
        "PUT": 0.01,
        "DELETE": 0.005
    }
    return costs.get(method, 0.001)


@shackled(
    tool_name="api_call",
    estimate_cost=estimate_api_cost,
    client=shackle
)
async def call_api(endpoint: str, method: str = "GET", data=None):
    """Make API call with SHACKLE governance"""
    print(f"Calling API: {method} {endpoint}")
    await asyncio.sleep(0.2)  # Simulate network
    return {"status": 200, "response": {"success": True}}


# Example 3: Database query with dynamic cost
@shackled(
    tool_name="db_query",
    estimate_cost=lambda query, limit=100: 0.0001 * limit,
    client=shackle
)
async def query_database(query: str, limit: int = 100):
    """Execute database query with SHACKLE governance"""
    print(f"Executing query (limit={limit}): {query}")
    await asyncio.sleep(0.15)
    return {"rows": [{"id": i, "value": f"row_{i}"} for i in range(min(limit, 10))]}


# Example 4: Expensive computation
@shackled(
    tool_name="ml_inference",
    estimate_cost=lambda model, batch_size=1: 0.1 * batch_size,
    client=shackle
)
async def run_ml_model(model: str, batch_size: int = 1):
    """Run ML inference with SHACKLE governance"""
    print(f"Running model {model} with batch_size={batch_size}")
    await asyncio.sleep(0.5)  # Simulate computation
    return {"predictions": [random.random() for _ in range(batch_size)]}


# Example 5: External service call
@shackled(
    tool_name="send_email",
    estimate_cost=lambda to, cc=None: 0.01 * (1 + len(cc or [])),
    client=shackle
)
async def send_email(to: str, subject: str, body: str, cc=None):
    """Send email with SHACKLE governance"""
    recipients = [to] + (cc or [])
    print(f"Sending email to {len(recipients)} recipient(s)")
    await asyncio.sleep(0.3)
    return {"sent": True, "message_id": "msg_12345"}


async def main():
    """Run example workflows"""
    print("=" * 70)
    print("SHACKLE Client Decorator Examples")
    print("=" * 70)
    
    try:
        # Workflow 1: Simple file operations
        print("\n[Workflow 1: File Operations]")
        result = await read_file("/etc/hosts")
        print(f"✓ Read file: {result['size']} bytes")
        
        result = await read_file("/var/log/system.log")
        print(f"✓ Read file: {result['size']} bytes")
        
        # Workflow 2: API interactions
        print("\n[Workflow 2: API Calls]")
        result = await call_api("/users", method="GET")
        print(f"✓ GET request: {result['status']}")
        
        result = await call_api("/users", method="POST", data={"name": "Alice"})
        print(f"✓ POST request: {result['status']}")
        
        # Workflow 3: Database queries
        print("\n[Workflow 3: Database Queries]")
        result = await query_database("SELECT * FROM users WHERE active = true", limit=10)
        print(f"✓ Query returned {len(result['rows'])} rows")
        
        result = await query_database("SELECT * FROM logs ORDER BY created DESC", limit=1000)
        print(f"✓ Large query returned {len(result['rows'])} rows")
        
        # Workflow 4: ML inference
        print("\n[Workflow 4: ML Inference]")
        result = await run_ml_model("sentiment_classifier", batch_size=5)
        print(f"✓ Model inference: {len(result['predictions'])} predictions")
        
        # This might trigger budget warning
        result = await run_ml_model("large_transformer", batch_size=100)
        print(f"✓ Large batch inference: {len(result['predictions'])} predictions")
        
        # Workflow 5: Communications
        print("\n[Workflow 5: Email Sending]")
        result = await send_email(
            to="user@example.com",
            subject="Test",
            body="Hello world"
        )
        print(f"✓ Email sent: {result['message_id']}")
        
        result = await send_email(
            to="user@example.com",
            subject="Broadcast",
            body="Important announcement",
            cc=["user2@example.com", "user3@example.com"]
        )
        print(f"✓ Broadcast email sent: {result['message_id']}")
        
        # Workflow 6: Repeat operations (should trigger HITL)
        print("\n[Workflow 6: Repeat Operation Detection]")
        for i in range(5):
            try:
                result = await read_file("/etc/hosts")  # Same call repeatedly
                print(f"  Attempt {i+1}: Success")
            except PermissionError as e:
                print(f"  Attempt {i+1}: Blocked - {e}")
                break
        
    except PermissionError as e:
        print(f"\n✗ Operation denied by SHACKLE: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        await shackle.close()
    
    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
