from app import app


def test_index_lists_notes():
    client = app.test_client()
    page = client.get("/").get_data(as_text=True)
    assert "buy oat milk" in page
