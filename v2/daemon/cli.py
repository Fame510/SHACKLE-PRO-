#!/usr/bin/env python3
"""
SHACKLE CLI - Command-line interface for daemon management and inspection
"""

import asyncio
import click
import json
from pathlib import Path
from client import ShackleClient
from state import StateManager
from audit import AuditLogger
import os


@click.group()
def cli():
    """SHACKLE Sovereign Daemon CLI"""
    pass


@cli.command()
@click.option('--socket', default='/tmp/shackle.sock', help='Unix socket path')
def health(socket):
    """Check daemon health"""
    async def check():
        client = ShackleClient(socket_path=socket)
        is_available = await client.check_daemon()
        
        if is_available:
            click.echo("✓ Daemon is healthy")
            click.echo(f"  Socket: {socket}")
        else:
            click.echo("✗ Daemon is not available")
            click.echo(f"  Socket: {socket}")
            click.echo("  Make sure daemon is running: python daemon.py")
        
        await client.close()
    
    asyncio.run(check())


@cli.command()
@click.option('--redis-url', default='redis://localhost:6379/0', envvar='REDIS_URL')
@click.argument('session_id')
def budget(redis_url, session_id):
    """Check budget status for a session"""
    async def check():
        state = StateManager(redis_url)
        await state.connect()
        
        status = await state.get_budget_status(session_id)
        
        click.echo(f"Budget Status: {session_id}")
        click.echo(f"  Spent:     ${status['spent']:.4f}")
        click.echo(f"  Limit:     ${status['limit']:.4f}")
        click.echo(f"  Remaining: ${status['remaining']:.4f}")
        click.echo(f"  Used:      {status['percentage']:.1f}%")
        
        await state.close()
    
    asyncio.run(check())


@cli.command()
@click.option('--redis-url', default='redis://localhost:6379/0', envvar='REDIS_URL')
@click.argument('session_id')
@click.argument('limit', type=float)
def set_budget(redis_url, session_id, limit):
    """Set budget limit for a session"""
    async def set_limit():
        state = StateManager(redis_url)
        await state.connect()
        
        await state.set_budget_limit(session_id, limit)
        click.echo(f"✓ Set budget limit for {session_id}: ${limit:.2f}")
        
        await state.close()
    
    asyncio.run(set_limit())


@cli.command()
@click.option('--postgres-url', envvar='POSTGRES_URL', required=True)
@click.argument('session_id')
@click.option('--limit', default=20, help='Number of logs to show')
def logs(postgres_url, session_id, limit):
    """Show audit logs for a session"""
    async def show_logs():
        audit = AuditLogger(postgres_url)
        await audit.connect()
        
        entries = await audit.get_session_logs(session_id, limit=limit)
        
        if not entries:
            click.echo(f"No logs found for session: {session_id}")
            await audit.close()
            return
        
        click.echo(f"Audit Logs: {session_id} (last {len(entries)} entries)")
        click.echo("-" * 80)
        
        for entry in entries:
            click.echo(f"{entry['timestamp']} | {entry['event_type']:10s} | {entry['tool_name']:20s}")
            
            if entry['decision']:
                click.echo(f"  Decision: {entry['decision']}")
            if entry['reason']:
                click.echo(f"  Reason: {entry['reason']}")
            if entry['cost']:
                click.echo(f"  Cost: ${float(entry['cost']):.4f}")
            if entry['execution_time_ms']:
                click.echo(f"  Time: {float(entry['execution_time_ms']):.2f}ms")
            if entry['error']:
                click.echo(f"  Error: {entry['error']}")
            
            click.echo()
        
        await audit.close()
    
    asyncio.run(show_logs())


@cli.command()
@click.option('--postgres-url', envvar='POSTGRES_URL', required=True)
def stats(postgres_url):
    """Show aggregate statistics"""
    async def show_stats():
        audit = AuditLogger(postgres_url)
        await audit.connect()
        
        data = await audit.get_stats()
        
        click.echo("SHACKLE Statistics")
        click.echo("=" * 50)
        click.echo(f"Total logs:   {data.get('total_logs', 0)}")
        click.echo(f"Total cost:   ${data.get('total_cost', 0):.4f}")
        click.echo()
        
        click.echo("By Event Type:")
        for event_type, count in data.get('by_type', {}).items():
            click.echo(f"  {event_type:15s} {count:6d}")
        click.echo()
        
        click.echo("By Decision:")
        for decision, count in data.get('by_decision', {}).items():
            click.echo(f"  {decision:15s} {count:6d}")
        
        await audit.close()
    
    asyncio.run(show_stats())


@cli.command()
@click.option('--postgres-url', envvar='POSTGRES_URL', required=True)
@click.argument('log_id', type=int)
def verify(postgres_url, log_id):
    """Verify cryptographic signature of a log entry"""
    async def verify_log():
        audit = AuditLogger(postgres_url)
        await audit.connect()
        
        is_valid = await audit.verify_log_integrity(log_id)
        
        if is_valid:
            click.echo(f"✓ Log entry {log_id} signature is VALID")
        else:
            click.echo(f"✗ Log entry {log_id} signature is INVALID")
        
        await audit.close()
    
    asyncio.run(verify_log())


@cli.command()
@click.option('--redis-url', default='redis://localhost:6379/0', envvar='REDIS_URL')
@click.argument('session_id')
@click.confirmation_option(prompt='Are you sure you want to clear all session state?')
def clear(redis_url, session_id):
    """Clear all state for a session"""
    async def clear_state():
        state = StateManager(redis_url)
        await state.connect()
        
        await state.clear_session(session_id)
        click.echo(f"✓ Cleared all state for session: {session_id}")
        
        await state.close()
    
    asyncio.run(clear_state())


@cli.command()
def version():
    """Show version information"""
    click.echo("SHACKLE Sovereign Daemon v2.0.0")
    click.echo("Governance system for tool execution control")
    click.echo()
    click.echo("Components:")
    click.echo("  - FastAPI daemon with Unix socket + WebSocket")
    click.echo("  - Redis state manager (budget + repeat detection)")
    click.echo("  - Postgres audit logger (Ed25519 signatures)")
    click.echo("  - Python client decorator")


if __name__ == '__main__':
    cli()
