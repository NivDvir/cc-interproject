"""Tests for six_laws_kit.heads.packet: the packet wording, its schema, and the command line."""

from __future__ import annotations

import json

from six_laws_kit.heads import packet


def test_packet_wording_covers_the_required_phrases():
    assert "Read your own CLAUDE.md" in packet.PACKET
    assert "Read nothing outside this directory" in packet.PACKET
    assert "Describe THIS project" in packet.PACKET
    assert "shared registry" in packet.PACKET
    assert "Invent nothing" in packet.PACKET
    assert "NOT STATED" in packet.PACKET
    assert "Do not describe any other project" in packet.PACKET
    for field in ("name", "owns", "asks_others_to_watch_for", "contact_subject"):
        assert field in packet.PACKET


def test_row_schema_shape():
    schema = packet.ROW_SCHEMA
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "name",
        "owns",
        "asks_others_to_watch_for",
        "contact_subject",
    }
    props = schema["properties"]
    assert props["name"]["maxLength"] == 120
    assert props["owns"]["maxLength"] == 400
    assert props["asks_others_to_watch_for"]["maxLength"] == 400
    assert props["contact_subject"]["maxLength"] == 200


def test_build_command_with_schema():
    command = packet.build_command("claude", json_schema=True)
    assert command[0] == "claude"
    assert "--json-schema" in command
    index = command.index("--json-schema")
    schema_arg = command[index + 1]
    assert json.loads(schema_arg) == packet.ROW_SCHEMA


def test_build_command_without_schema():
    command = packet.build_command("claude", json_schema=False)
    assert "--json-schema" not in command
    assert "--max-turns" in command
    assert "--max-budget-usd" in command
