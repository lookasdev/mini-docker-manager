import subprocess

from parsers import extract_memory_usage, parse_json_lines


DOCKER_NOT_FOUND_MESSAGE = "Comanda 'docker' nu a fost gasita - ruleaza aplicatia din Linux/WSL si verifica Docker CLI."
DOCKER_TIMEOUT_MESSAGE = "Comanda Docker a expirat - verifica daca daemonul Docker raspunde."


class DockerCommandError(RuntimeError):
    pass


def _run_docker_command(args: list[str], timeout: int = 8) -> str:
    command = ["docker", *args]

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as error:
        raise DockerCommandError(DOCKER_NOT_FOUND_MESSAGE) from error
    except subprocess.TimeoutExpired as error:
        raise DockerCommandError(DOCKER_TIMEOUT_MESSAGE) from error

    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "eroare necunoscuta docker"
        raise DockerCommandError(message)

    return completed.stdout


def _container_row(row: dict) -> dict:
    return {
        "id": row.get("ID", ""),
        "name": row.get("Names", ""),
        "image": row.get("Image", ""),
        "command": row.get("Command", ""),
        "ports": row.get("Ports", "-"),
        "status": row.get("Status", ""),
        "state": row.get("State", "unknown"),
    }


def _stats_row(row: dict) -> dict | None:
    container_id = row.get("ID", "")
    if not container_id:
        return None

    return {
        "id": container_id,
        "name": row.get("Name", ""),
        "cpu": row.get("CPUPerc", "0.00%"),
        "memory": extract_memory_usage(row.get("MemUsage", "0B / 0B")),
        "net_io": row.get("NetIO", "0B / 0B"),
        "block_io": row.get("BlockIO", "0B / 0B"),
        "pids": row.get("PIDs", "0"),
    }


def _image_row(row: dict) -> dict:
    repository = row.get("Repository", "<none>")
    tag = row.get("Tag", "latest")
    image_ref = row.get("ID", "")

    if repository != "<none>" and tag != "<none>":
        image_ref = f"{repository}:{tag}"

    return {
        "repository": repository,
        "tag": tag,
        "id": row.get("ID", ""),
        "size": row.get("Size", ""),
        "created": row.get("CreatedSince", ""),
        "ref": image_ref,
    }


def list_containers() -> list[dict]:
    output = _run_docker_command(["ps", "-a", "--format", "{{json .}}"])
    return [_container_row(row) for row in parse_json_lines(output)]


def list_stats() -> dict[str, dict]:
    output = _run_docker_command(["stats", "--no-stream", "--format", "{{json .}}"])
    stats: dict[str, dict] = {}

    for row in parse_json_lines(output):
        parsed_row = _stats_row(row)
        if parsed_row is None:
            continue

        stats[parsed_row["id"]] = parsed_row

    return stats


def start_container(container_id: str) -> None:
    _run_docker_command(["start", container_id])


def stop_container(container_id: str) -> None:
    _run_docker_command(["stop", "-t", "10", container_id], timeout=30)


def restart_container(container_id: str) -> None:
    _run_docker_command(["restart", "-t", "10", container_id], timeout=40)


def get_container_logs(container_id: str, tail: int = 30) -> str:
    return _run_docker_command(["logs", "--tail", str(tail), container_id])


def inspect_container(container_id: str) -> str:
    return _run_docker_command(["inspect", container_id])


def remove_container(container_id: str) -> None:
    _run_docker_command(["rm", "-f", container_id])


def list_images() -> list[dict]:
    output = _run_docker_command(["images", "--format", "{{json .}}"])
    return [_image_row(row) for row in parse_json_lines(output)]


def pull_image(image_name: str) -> str:
    return _run_docker_command(["pull", image_name], timeout=120).strip()


def run_container(
    image_name: str,
    container_name: str = "",
    port_mapping: str = "",
    program_name: str = "",
    command_text: str = "",
) -> str:
    command = ["run", "-d"]
    if container_name:
        command.extend(["--name", container_name])
    if port_mapping:
        command.extend(["-p", port_mapping])
    command.append(image_name)

    if command_text:
        program = program_name or "/bin/bash"
        command.extend([program, "-c", command_text])
    elif program_name:
        command.append(program_name)

    return _run_docker_command(command, timeout=20).strip()


def remove_image(image_id: str) -> None:
    _run_docker_command(["rmi", image_id])