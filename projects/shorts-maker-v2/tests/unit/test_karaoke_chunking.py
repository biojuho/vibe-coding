def test_karaoke_chunking_and_ssml():
    import json
    import tempfile
    from pathlib import Path

    from shorts_maker_v2.render.karaoke import (
        WordSegment,
        apply_ssml_break_correction,
        group_into_chunks,
        group_word_segments,
        load_words_json,
        sentence_boundary_chunks,
    )

    words = [
        WordSegment("Hello,", 0.0, 0.5),
        WordSegment("world!", 0.6, 1.0),
        WordSegment("This", 1.5, 2.0),
        WordSegment("is", 2.1, 2.5),
        WordSegment("a", 2.6, 2.7),
        WordSegment("test.", 2.8, 3.5),
    ]

    # Test SSML correction
    ssml_text = '<speak>Hello, world! <break time="500ms"/> This is a test.</speak>'
    corrected = apply_ssml_break_correction(words, ssml_text)
    # The first break time is 0.5s. It should add 0.5s to all words since first start is 0
    assert corrected[0].start == 0.0 + 0.5

    # Test ssml no break
    no_break = apply_ssml_break_correction(words, "Hello world")
    assert no_break == words

    # Test sentence_boundary_chunks
    chunks = sentence_boundary_chunks(words, max_words=3)
    # Expected:
    # Hello, (has comma) -> boundary
    # world! (has exclamation) -> boundary
    # This is a (max 3) -> boundary
    # test. (has period) -> boundary
    assert len(chunks) == 4
    assert chunks[0][2] == "Hello,"
    assert chunks[1][2] == "world!"
    assert chunks[2][2] == "This is a"
    assert chunks[3][2] == "test."

    # Test group_word_segments
    grouped = group_word_segments(words, chunk_size=3, boundary_aware=True)
    assert len(grouped) == 4
    assert grouped[0][2] == "Hello,"

    grouped_no_bound = group_word_segments(words, chunk_size=3, boundary_aware=False)
    assert len(grouped_no_bound) == 2
    assert grouped_no_bound[0][2] == "Hello, world! This"
    assert len(grouped_no_bound[0][3]) == 3

    # Test group_into_chunks
    into_chunks = group_into_chunks(words, chunk_size=3, boundary_aware=False)
    assert len(into_chunks) == 2
    assert into_chunks[0][2] == "Hello, world! This"

    # Test JSON load
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "words.json"
        json_path.write_text(json.dumps([
            {"word": "Hi ", "start": "0.1", "end": "0.5"},
            {"word": " ", "start": "0.5", "end": "0.6"},  # Should be skipped
            {"word": "Test", "start": "0.6", "end": "1.0"}
        ]), encoding="utf-8")
        loaded = load_words_json(json_path)
        assert len(loaded) == 2
        assert loaded[0].word == "Hi"
        assert loaded[0].start == 0.1
