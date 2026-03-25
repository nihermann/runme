from __future__ import annotations

import json
import os
from pathlib import Path

from .models import AppState, Category, Command


APP_HOME = Path.home() / ".runme-desktop"
SCRIPTS_DIR = APP_HOME / "scripts"
STATE_PATH = APP_HOME / "commands.json"


class Storage:
    def __init__(self) -> None:
        APP_HOME.mkdir(parents=True, exist_ok=True)
        SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppState:
        if not STATE_PATH.exists():
            state = self._default_state()
            self.save(state)
            return state
        data = json.loads(STATE_PATH.read_text())
        return AppState.from_dict(data)

    def save(self, state: AppState) -> None:
        STATE_PATH.write_text(json.dumps(state.to_dict(), indent=2))

    def create_script(self, command_id: str, content: str = "") -> str:
        path = SCRIPTS_DIR / f"{command_id}.sh"
        if not content:
            content = "#!/usr/bin/env bash\n\n"
        path.write_text(content)
        os.chmod(path, 0o755)
        return str(path)

    def update_script(self, script_path: str, content: str) -> None:
        path = Path(script_path)
        path.write_text(content)
        os.chmod(path, 0o755)

    def read_script(self, script_path: str) -> str:
        path = Path(script_path)
        if not path.exists():
            return "#!/usr/bin/env bash\n\n"
        return path.read_text()

    def clone_script(self, source_script_path: str, new_command_id: str) -> str:
        content = self.read_script(source_script_path)
        return self.create_script(new_command_id, content)

    def delete_script(self, script_path: str) -> None:
        path = Path(script_path)
        if path.exists():
            path.unlink()

    def _default_state(self) -> AppState:
        category = Category.create("Getting Started")
        command = Command.create(
            name="Example Command",
            working_directory=str(Path.home()),
            script_path="",
        )
        command.script_path = self.create_script(
            command.id,
            "#!/usr/bin/env bash\n\necho \"RunMe is ready\"\npwd\n",
        )
        category.commands.append(command)
        return AppState(categories=[category])
