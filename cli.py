import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from config.settings import settings
from src.models.lead import BusinessProfile, OutreachChannel, LeadStatus
from src.storage.repository import lead_repo
from src.pipelines.discovery_pipeline import discovery_pipeline
from src.pipelines.outreach_pipeline import outreach_pipeline
from src.pipelines.chat_pipeline import chat_pipeline

app = typer.Typer(
    name="Standard Autonomous CLI",
    help="Standard Autonomous Multi-Agent Swarm & Outreach Engine."
)
console = Console()

@app.command()
def discover(
    category: str = typer.Option("restaurant", "--category", "-c", help="Business category (e.g. restaurant, salon, gym)"),
    location: str = typer.Option("Mumbai", "--location", "-l", help="City or area (e.g. Mumbai, Delhi, Bangalore)"),
    limit: int = typer.Option(5, "--limit", "-n", help="Max number of leads to discover"),
    source: str = typer.Option("google_maps", "--source", "-s", help="Source: google_maps or web_discovery"),
    only_no_website: bool = typer.Option(True, "--no-website/--all", help="Target only businesses without a website")
):
    """Run discovery pipeline to scrape and qualify high-potential businesses."""
    console.print(f"[bold cyan]🔍 Starting Discovery Pipeline...[/bold cyan]")
    console.print(f"Category: [yellow]{category}[/yellow] | Location: [yellow]{location}[/yellow] | Source: [yellow]{source}[/yellow]")
    
    leads = discovery_pipeline.run(
        category=category,
        location=location,
        limit=limit,
        source=source,
        only_no_website=only_no_website
    )

    if not leads:
        console.print("[bold yellow]No new leads found (or all candidates were already captured/duplicates).[/bold yellow]")
        return

    table = Table(title=f"Discovered Prospects ({len(leads)})")
    table.add_column("Company", style="bold white")
    table.add_column("Phone", style="green")
    table.add_column("Website", style="cyan")
    table.add_column("Rating", style="yellow")
    table.add_column("Status", style="magenta")

    for l in leads:
        p = l.profile
        table.add_row(
            p.company_name[:35],
            p.phone or "[dim]N/A[/dim]",
            "Yes" if p.has_website else "[red]None[/red]",
            p.rating or "N/A",
            l.status.value
        )

    console.print(table)
    console.print(f"[bold green]✓ Successfully saved {len(leads)} leads to repository.[/bold green]")


@app.command()
def list_leads(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (discovered, qualified, contacted)"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Filter by location"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max leads to display")
):
    """List captured leads stored in the local repository."""
    filter_status = LeadStatus(status) if status else None
    leads = lead_repo.list_all(
        status=filter_status,
        business_type=category,
        location=location
    )[:limit]

    if not leads:
        console.print("[dim]No leads found matching your criteria.[/dim]")
        return

    table = Table(title=f"Stored Leads ({len(leads)})")
    table.add_column("ID", style="dim")
    table.add_column("Company Name", style="bold white")
    table.add_column("Category", style="cyan")
    table.add_column("Location", style="yellow")
    table.add_column("Phone", style="green")
    table.add_column("Status", style="magenta")

    for l in leads:
        p = l.profile
        table.add_row(
            l.id,
            p.company_name[:30],
            p.business_type,
            p.location,
            p.phone or "[dim]N/A[/dim]",
            l.status.value
        )

    console.print(table)


@app.command()
def outreach(
    channel: str = typer.Option("whatsapp", "--channel", "-ch", help="Channel: whatsapp, email, telegram"),
    limit: int = typer.Option(3, "--limit", "-n", help="Number of leads to contact"),
    dry_run: bool = typer.Option(True, "--dry-run/--send", help="Preview outreach without sending")
):
    """Run automated AI pain-point enrichment and outreach dispatch."""
    outreach_ch = OutreachChannel(channel)
    console.print(f"[bold cyan]✉️ Running Outreach via {outreach_ch.value.upper()} (dry_run={dry_run})...[/bold cyan]")
    
    res = outreach_pipeline.run_batch(channel=outreach_ch, limit=limit, dry_run=dry_run)
    console.print(f"Processed: [bold]{res['total']}[/bold] | Succeeded: [green]{res['succeeded']}[/green] | Failed: [red]{res['failed']}[/red]")


@app.command()
def chat(
    company: str = typer.Option("Sample Business", "--company", "-c", help="Company name to simulate pitch with"),
    category: str = typer.Option("Software", "--category", help="Industry/Category"),
    location: str = typer.Option("San Francisco", "--location", help="Location")
):
    """Start an interactive multi-turn sales chat session with the AI."""
    profile = BusinessProfile(
        company_name=company,
        business_type=category,
        location=location
    )
    session = chat_pipeline.create_session(profile)
    console.print(f"\n[bold green]--- Starting AI Consultative Pitch for {company} ---[/bold green]")
    
    first_reply = chat_pipeline.generate_next_response(session)
    console.print(f"[bold cyan]Bot:[/bold cyan] {first_reply}")

    while True:
        try:
            user_msg = console.input("\n[bold yellow]You (type 'exit' to stop): [/bold yellow]")
            if user_msg.lower().strip() in ["exit", "quit"]:
                break
            reply = chat_pipeline.generate_next_response(session, user_msg)
            console.print(f"[bold cyan]Bot:[/bold cyan] {reply}")
        except KeyboardInterrupt:
            break

    console.print("\n[bold green]--- Extracting Lead Data ---[/bold green]")
    lead_out = chat_pipeline.extract_lead(session)
    if lead_out:
        console.print(f"Qualified: [bold]{lead_out.qualified}[/bold] | Budget: {lead_out.budget} | Email: {lead_out.contact_email}")
        console.print(f"Summary: {lead_out.summary}")


@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    reload: bool = typer.Option(True, "--reload", help="Auto-reload on code changes")
):
    """Launch the FastAPI Web Backend and Modern Command Center Dashboard."""
    import uvicorn
    console.print(f"[bold green]🚀 Launching Web Command Center on http://{host}:{port}[/bold green]")
    uvicorn.run("src.api.server:app", host=host, port=port, reload=reload)


@app.command()
def workforce():
    """Display Paperclip-style multi-agent workforce status, token usage, and conversion funnel."""
    from src.services.workforce import workforce_manager
    status = workforce_manager.get_workforce_status()

    table = Table(title="Autonomous Agent Workforce Org Chart")
    table.add_column("Agent Name", style="bold cyan")
    table.add_column("Role / Specialty", style="white")
    table.add_column("Tasks Processed", style="green")
    table.add_column("Tokens", style="yellow")
    table.add_column("Cost (USD)", style="magenta")

    for a in status.agents:
        table.add_row(
            a.name,
            a.role,
            str(a.tasks_processed),
            f"{a.tokens_consumed:,}",
            f"${a.estimated_cost_usd:.4f}"
        )
    console.print(table)

    console.print(f"\n[bold]Total Tokens:[/bold] {status.total_tokens:,} | [bold]Estimated Cost:[/bold] [green]${status.total_cost_usd:.4f}[/green]")
    console.print(f"[bold yellow]Pending Outbox Approvals:[/bold yellow] [bold]{status.pending_approval}[/bold]")
    
    funnel_str = " -> ".join([f"{k.upper()}: {v}" for k, v in status.funnel.items()])
    console.print(f"[cyan]Funnel:[/cyan] {funnel_str}\n")


@app.command()
def approve_lead(
    lead_id: str = typer.Argument(..., help="ID of lead to approve (e.g. lead_123)"),
    channel: str = typer.Option("whatsapp", "--channel", "-ch", help="Channel: whatsapp, email, telegram"),
    dry_run: bool = typer.Option(False, "--dry-run/--send", help="Dry run without live API call")
):
    """Approve a queued lead in the outbox and dispatch outreach."""
    from src.services.workforce import workforce_manager
    outreach_ch = OutreachChannel(channel)
    res = workforce_manager.approve_and_dispatch(lead_id, channel=outreach_ch, dry_run=dry_run)
    if res.get("success"):
        console.print(f"[bold green]✓ Lead {lead_id} approved and dispatched via {channel.upper()}![/bold green]")
    else:
        console.print(f"[bold red]✗ Failed to dispatch lead {lead_id}: {res.get('error')}[/bold red]")


@app.command()
def simulate_reply(
    lead_id: str = typer.Argument(..., help="ID of lead (e.g. lead_123)"),
    message: str = typer.Option("What are your charges?", "--msg", "-m", help="Prospect's incoming message or objection")
):
    """Simulate an inbound prospect reply and test Closer Agent objection handling."""
    from src.services.inbound_closer import inbound_closer
    console.print(f"[yellow]👤 Prospect:[/yellow] {message}")
    
    try:
        resp = inbound_closer.handle_incoming_message(lead_id, message)
        console.print(f"[cyan]🤖 Closer Agent (Intent: {resp.intent.value.upper()}, Status -> {resp.recommended_status.value}):[/cyan]")
        console.print(f"[bold white]{resp.reply_message}[/bold white]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")


@app.command()
def export(
    output_path: str = typer.Option("data/exports/leads.csv", "--output", "-o", help="File path to save CSV export")
):
    """Export all leads to a clean CSV file."""
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    csv_data = lead_repo.export_csv()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(csv_data)
    console.print(f"[bold green]✓ Exported leads to {output_path}[/bold green]")


@app.command(name="dev-check")
def dev_check():
    """Run unified IC Development Harness (ECC AgentShield, Superpowers TDD, Pstack & Stack connectivity)."""
    from src.services.dev_harness import run_dev_checks
    run_dev_checks()


@app.command(name="run-all")
def run_all():
    """Launch the complete IC Unified All-in-One Swarm Platform (Core :8000, Paperclip :3100, Studio :5173)."""
    import subprocess
    import webbrowser
    import time

    console.print("[bold cyan]============================================================[/bold cyan]")
    console.print("[bold cyan]⚡ IC (INTELLIGENCE CENTER) ALL-IN-ONE SWARM PLATFORM[/bold cyan]")
    console.print("[bold cyan]============================================================[/bold cyan]")
    
    console.print("\n[Phase 1] Verifying Paperclip Engine (:3100)... [green]ACTIVE[/green]")
    console.print("[Phase 2] Verifying React Swarm Studio (:5173)... [green]ACTIVE[/green]")
    console.print("[Phase 3] Booting Unified Agency OS Dashboard (:8000)...")

    time.sleep(1)
    webbrowser.open("http://127.0.0.1:8000")
    
    import uvicorn
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    app()

