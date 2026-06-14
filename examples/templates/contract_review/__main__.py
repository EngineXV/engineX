"""CLI for Contract Review agent"""

import asyncio
import json
import sys

import click

from .agent import ContractReviewAgent, default_agent


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Contract Review — extract fields with human approval"""


@cli.command()
@click.option("--text", "-t", type=str, help="Contract text (headless)")
@click.option("--name", "-n", type=str, default="contract", help="Document name")
def run(text, name):
    """Run contract review (use TUI if --text omitted)"""
    if not text:
        click.echo("Use: ./engine run examples/templates/contract_review --tui", err=True)
        sys.exit(1)
    result = asyncio.run(
        default_agent.run({"contract_text": text, "document_name": name})
    )
    click.echo(json.dumps({"success": result.success, "output": result.output}, indent=2))
    sys.exit(0 if result.success else 1)


@cli.command()
def validate():
    """Validate agent structure"""
    v = default_agent.validate()
    click.echo("Agent is valid" if v["valid"] else f"Errors: {v['errors']}")
    sys.exit(0 if v["valid"] else 1)


@cli.command()
def info():
    """Show agent info"""
    click.echo(json.dumps(default_agent.info(), indent=2))


if __name__ == "__main__":
    cli()
