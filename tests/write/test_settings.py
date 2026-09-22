from __future__ import annotations

import json
from pathlib import Path

from six_laws_kit.write import settings

FOREIGN = {
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": "echo foreign", "timeout": 5}],
            }
        ]
    }
}


def _additions() -> list[dict]:
    return settings.hook_additions(["python3"], Path("/home/.claude/hooks/six-laws"))


def test_load_missing_file_returns_empty_dict(tmp_path: Path):
    assert settings.load(tmp_path / "nope.json") == {}


def test_load_reads_existing_json(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(FOREIGN), encoding="utf-8")
    assert settings.load(path) == FOREIGN


def test_hook_additions_has_the_three_documented_entries():
    additions = _additions()
    assert [a["event"] for a in additions] == ["UserPromptSubmit", "Stop", "PreToolUse"]
    assert [a["matcher"] for a in additions] == [
        None,
        None,
        "Agent|Task|SendMessage|Read|Grep|Glob|Bash|WebFetch",
    ]
    assert [a["timeout"] for a in additions] == [10, 20, 5]
    assert all("python3" in a["command"] for a in additions)


def test_merge_hooks_adds_all_three_and_preserves_the_foreign_hook():
    merged, added = settings.merge_hooks(FOREIGN, _additions())
    assert len(added) == 3
    assert merged["hooks"]["PostToolUse"] == FOREIGN["hooks"]["PostToolUse"]
    assert "UserPromptSubmit" in merged["hooks"]
    assert "Stop" in merged["hooks"]
    assert "PreToolUse" in merged["hooks"]


def test_merge_hooks_is_idempotent():
    additions = _additions()
    merged, _added = settings.merge_hooks(FOREIGN, additions)
    merged_again, added_again = settings.merge_hooks(merged, additions)
    assert added_again == []
    assert merged_again == merged


def test_merge_hooks_does_not_mutate_its_input():
    original = json.loads(json.dumps(FOREIGN))
    settings.merge_hooks(FOREIGN, _additions())
    assert original == FOREIGN


def test_remove_hooks_drops_only_the_commands_given_and_empty_groups():
    additions = _additions()
    merged, added = settings.merge_hooks(FOREIGN, additions)
    commands = [entry["command"] for entry in added]
    restored = settings.remove_hooks(merged, commands)
    assert restored == FOREIGN
    assert "UserPromptSubmit" not in restored.get("hooks", {})
    assert "Stop" not in restored.get("hooks", {})
    assert "PreToolUse" not in restored.get("hooks", {})


def test_remove_hooks_survives_when_the_foreign_hook_is_the_only_one_left():
    merged, added = settings.merge_hooks(FOREIGN, _additions())
    commands = [entry["command"] for entry in added]
    restored = settings.remove_hooks(merged, commands)
    assert restored["hooks"]["PostToolUse"][0]["hooks"][0]["command"] == "echo foreign"


def test_same_purpose_hooks_matches_known_basenames():
    found = settings.same_purpose_hooks(
        {
            "hooks": {
                "Stop": [
                    {
                        "matcher": None,
                        "hooks": [
                            {
                                "type": "command",
                                "command": 'python3 "/home/.claude/hooks/labor_tally.py"',
                                "timeout": 20,
                            }
                        ],
                    }
                ]
            }
        }
    )
    assert found == ['python3 "/home/.claude/hooks/labor_tally.py"']


def test_same_purpose_hooks_ignores_unrelated_commands():
    assert settings.same_purpose_hooks(FOREIGN) == []


def test_preview_returns_before_and_after_text(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(FOREIGN, indent=2) + "\n", encoding="utf-8")
    before, after = settings.preview(path, _additions())
    assert before == json.dumps(FOREIGN, indent=2) + "\n"
    assert before != after
    assert "PreToolUse" in after


def test_preview_of_a_missing_file_treats_it_as_empty(tmp_path: Path):
    before, after = settings.preview(tmp_path / "nope.json", _additions())
    assert before == "{}\n"
    assert "UserPromptSubmit" in after
