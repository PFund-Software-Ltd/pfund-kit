import os
import subprocess
import shutil

import click


@click.command(
    name='docker-compose',
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    )
)
@click.pass_context
def docker_compose(ctx):
    """Run docker-compose commands with the project's compose.yml file.

    This is a convenience wrapper that automatically uses the compose.yml
    from your project's config directory.

    Examples:
        pfeed docker-compose up -d      # Start services in background
        pfeed docker-compose ps          # List running services
        pfeed docker-compose logs -f     # Follow logs
        pfeed docker-compose down        # Stop and remove services
    """
    # Check if docker is installed
    if not shutil.which('docker'):
        click.echo("Error: docker is not installed or not in PATH", err=True)
        click.echo("Please install Docker: https://docs.docker.com/get-docker/", err=True)
        ctx.exit(1)

    config = ctx.obj['config']
    compose_file_path = config.docker_compose_file_path

    # Check if compose file exists
    if not compose_file_path.exists():
        click.echo(f"Error: compose.yml not found at {compose_file_path}", err=True)
        ctx.exit(1)

    click.echo(f'Using compose.yml from: {compose_file_path}')

    # Let the project-specific config prepare the docker context
    # (e.g., set env vars, ensure directories exist, check prerequisites)
    config.prepare_docker_context()

    # Build the docker compose command with the config's compose file
    # Use 'docker compose' (plugin) instead of deprecated 'docker-compose' (standalone)
    command = ['docker', 'compose', '--file', str(compose_file_path)] + ctx.args

    # Run docker compose with the current environment
    result = subprocess.run(command, env=os.environ)
    ctx.exit(result.returncode)
