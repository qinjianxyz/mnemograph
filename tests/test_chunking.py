from mnemograph.ingest.chunk import chunk_text


def test_chunk_text_preserves_paragraph_boundaries():
    text = "\n\n".join(
        [
            "Paragraph one has a complete thought.",
            "Paragraph two also stays intact.",
            "Paragraph three should become its own chunk.",
        ]
    )

    chunks = chunk_text(text, max_chars=70)

    assert [chunk.text for chunk in chunks] == [
        "Paragraph one has a complete thought.",
        "Paragraph two also stays intact.",
        "Paragraph three should become its own chunk.",
    ]


def test_chunk_text_splits_single_oversized_paragraph():
    sentence = "Stripe helps internet businesses accept payments worldwide."
    text = " ".join([sentence] * 40)

    chunks = chunk_text(text, max_chars=200)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 240 for chunk in chunks)


def test_chunk_text_splits_single_oversized_sentence_by_words():
    text = " ".join(["railway"] * 400)

    chunks = chunk_text(text, max_chars=200)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 240 for chunk in chunks)
