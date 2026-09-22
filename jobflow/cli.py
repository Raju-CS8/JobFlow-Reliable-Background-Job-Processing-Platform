"""Command-line interface for JobFlow."""

import click
import logging
from jobflow.worker.worker import Worker


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@click.group()
def cli():
    """JobFlow CLI."""
    pass


@cli.command()
@click.option(
    "--worker-id",
    default=None,
    help="Unique worker identifier. If not provided, generated from hostname + PID.",
)
@click.option(
    "--poll-interval",
    type=float,
    default=1.0,
    help="Seconds to sleep when no jobs available.",
)
def worker(worker_id: str, poll_interval: float):
    """Start a worker process."""
    click.echo(f"Starting JobFlow worker (poll_interval={poll_interval}s)...")
    
    w = Worker(worker_id=worker_id)
    w.run(poll_interval=poll_interval)


@cli.command()
def api():
    """Start the FastAPI server."""
    import uvicorn
    
    click.echo("Starting JobFlow API on http://127.0.0.1:8000")
    uvicorn.run(
        "jobflow.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    cli()