from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


def make_id() -> str:
    return uuid4().hex[:10]


@dataclass
class Command:
    id: str
    name: str
    working_directory: str
    script_path: str
    open_in_terminal: bool = False
    last_run_at: Optional[str] = None

    @classmethod
    def create(cls, name: str, working_directory: str, script_path: str) -> "Command":
        return cls(
            id=make_id(),
            name=name,
            working_directory=working_directory,
            script_path=script_path,
        )

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Command":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            working_directory=str(data.get("working_directory", "")),
            script_path=str(data["script_path"]),
            open_in_terminal=bool(data.get("open_in_terminal", False)),
            last_run_at=str(data["last_run_at"]) if data.get("last_run_at") else None,
        )


@dataclass
class Category:
    id: str
    name: str
    commands: List[Command] = field(default_factory=list)

    @classmethod
    def create(cls, name: str) -> "Category":
        return cls(id=make_id(), name=name)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "commands": [command.to_dict() for command in self.commands],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Category":
        commands = [Command.from_dict(item) for item in data.get("commands", [])]
        return cls(id=str(data["id"]), name=str(data["name"]), commands=commands)


@dataclass
class AppState:
    categories: List[Category] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {"categories": [category.to_dict() for category in self.categories]}

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "AppState":
        categories = [Category.from_dict(item) for item in data.get("categories", [])]
        return cls(categories=categories)

    def find_category(self, category_id: str) -> Category:
        for category in self.categories:
            if category.id == category_id:
                return category
        raise KeyError(category_id)

    def find_command(self, command_id: str) -> Command:
        for category in self.categories:
            for command in category.commands:
                if command.id == command_id:
                    return command
        raise KeyError(command_id)

    def command_path(self, command: Command) -> Path:
        return Path(command.script_path)
