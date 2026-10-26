from wordcut.asr.remote import RemoteHost, RemoteTranscriber, _last_progress_line


def test_ssh_command_never_prompts() -> None:
    command = RemoteHost("leitao").ssh_command("true")

    assert command[:5] == ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
    assert command[-2:] == ["leitao", "true"]


def test_launch_command_detaches_and_records_status() -> None:
    transcriber = RemoteTranscriber(RemoteHost("leitao", home="/opt/cp"), model="large-v3")

    command = transcriber._launch_command("abc123")

    assert command.startswith("setsid nohup sh -c ")
    assert command.endswith("&")
    assert "/opt/cp/jobs/abc123/audio.wav" in command
    assert "echo $? > /opt/cp/jobs/abc123/status" in command


def test_last_progress_line_handles_carriage_returns() -> None:
    log = "INFO load\netapa 1/2: reconhecimento\nProgress: 10.0%...\rProgress: 12.5%...\n"

    assert _last_progress_line(log) == "Progress: 12.5%..."


def test_last_progress_line_empty_when_no_progress() -> None:
    assert _last_progress_line("INFO loading model\n") == ""
