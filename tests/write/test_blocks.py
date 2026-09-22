from __future__ import annotations

from cc_interproject.write import blocks


def test_render_wraps_body_between_markers_for_the_given_id_and_version():
    text = blocks.render("project-pointer", 1, "hello\n")
    assert text == (
        "<!-- cc-interproject:begin id=project-pointer v=1 -->\n"
        "hello\n"
        "<!-- cc-interproject:end id=project-pointer -->\n"
    )


def test_render_adds_a_trailing_newline_to_the_body_when_missing():
    text = blocks.render("registry", 1, "no newline")
    assert "no newline\n<!-- cc-interproject:end" in text


def test_contains_true_after_insert_false_before():
    original = "# Alpha\n\nSome content.\n"
    block = blocks.render("project-pointer", 1, "pointer body\n")
    assert blocks.contains(original, "project-pointer") is False
    new_text, _leading, _trailing = blocks.insert(original, block)
    assert blocks.contains(new_text, "project-pointer") is True


def test_insert_then_strip_round_trips_when_text_already_ends_with_a_newline():
    original = "# Alpha\n\nSome content.\n"
    block = blocks.render("project-pointer", 1, "pointer body\n")
    new_text, leading_blank_added, trailing_newline_added = blocks.insert(original, block)
    assert leading_blank_added is True
    assert trailing_newline_added is False
    stripped, found = blocks.strip(new_text, "project-pointer")
    assert found is True
    assert stripped == original


def test_insert_then_strip_round_trips_with_crlf_line_endings():
    original = "# Alpha\r\nSome content.\r\n"
    block = blocks.render("registry", 1, "body\r\n")
    new_text, leading_blank_added, _trailing = blocks.insert(original, block)
    assert leading_blank_added is True
    stripped, found = blocks.strip(new_text, "registry")
    assert found is True
    assert stripped == original


def test_insert_on_empty_text_adds_no_leading_blank():
    block = blocks.render("registry", 1, "body\n")
    new_text, leading_blank_added, trailing_newline_added = blocks.insert("", block)
    assert leading_blank_added is False
    assert trailing_newline_added is False
    assert new_text == block


def test_double_insert_guarded_by_contains_is_a_noop():
    text = "abc\n"
    block = blocks.render("project-pointer", 1, "x\n")
    once, _, _ = blocks.insert(text, block)
    guarded = once if blocks.contains(once, "project-pointer") else blocks.insert(once, block)[0]
    assert guarded == once


def test_strip_reports_not_found_when_marker_is_absent():
    text = "abc\n"
    result, found = blocks.strip(text, "project-pointer")
    assert found is False
    assert result == text


def test_strip_reports_not_found_when_marker_appears_twice():
    text = "abc\n"
    block = blocks.render("project-pointer", 1, "x\n")
    twice, _, _ = blocks.insert(text, block)
    twice, _, _ = blocks.insert(twice, block)
    result, found = blocks.strip(twice, "project-pointer")
    assert found is False
    assert result == twice
