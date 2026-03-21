"""Tests for Telegram message chunking."""

from python.helpers.telegram_client import MAX_TELEGRAM_LENGTH, chunk_message


class TestChunkMessage:
    def test_short_message_returns_single_chunk(self):
        msg = "Hello, world!"
        chunks = chunk_message(msg)
        assert chunks == ["Hello, world!"]

    def test_empty_message_returns_empty_list(self):
        assert chunk_message("") == []

    def test_long_message_splits_at_newlines(self):
        line = "x" * 100 + "\n"
        msg = line * 50  # 5050 chars > 4096
        chunks = chunk_message(msg)
        assert len(chunks) >= 2
        assert all(len(c) <= MAX_TELEGRAM_LENGTH for c in chunks)

    def test_preserves_markdown_code_blocks(self):
        code = "```\n" + "a" * 200 + "\n```"
        msg = "Before\n" + code + "\n" + "x" * 4000
        chunks = chunk_message(msg)
        assert "```" in chunks[0]
        block_count = chunks[0].count("```")
        assert block_count % 2 == 0  # balanced fences

    def test_single_line_exceeding_limit_force_splits(self):
        msg = "x" * 5000  # no newlines
        chunks = chunk_message(msg)
        assert len(chunks) >= 2
        assert all(len(c) <= MAX_TELEGRAM_LENGTH for c in chunks)
        assert "".join(chunks) == msg

    def test_chunk_numbering_when_multiple(self):
        msg = ("line\n") * 2000  # well over limit
        chunks = chunk_message(msg, add_part_numbers=True)
        assert len(chunks) > 1
        assert chunks[0].endswith("(1/" + str(len(chunks)) + ")")

    def test_no_numbering_for_single_chunk(self):
        msg = "short message"
        chunks = chunk_message(msg, add_part_numbers=True)
        assert len(chunks) == 1
        assert "(1/1)" not in chunks[0]
