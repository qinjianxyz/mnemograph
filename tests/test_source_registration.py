from mnemograph.ingest.register import compute_content_hash, register_source


def test_register_source_normalizes_url_registration():
    record = register_source(
        source_type="url",
        locator="HTTPS://Acme.com/pricing/?plan=pro#section",
        content="Pro plan costs $49 per month.",
    )

    assert record.normalized_locator == "https://acme.com/pricing?plan=pro"
    assert record.source_type == "url"
    assert record.content_hash == compute_content_hash(
        "Pro plan costs $49 per month."
    )


def test_compute_content_hash_is_stable():
    assert compute_content_hash("same input") == compute_content_hash("same input")
