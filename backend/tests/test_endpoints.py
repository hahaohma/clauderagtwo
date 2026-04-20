"""
Endpoint tests for the RAG chatbot backend.

Endpoints under test
--------------------
GET  /api/courses  – Returns course catalog stats (total_courses, course_titles)
POST /api/query    – Processes a user query; returns answer, sources, session_id

Each test class covers one endpoint.  Within each class tests are ordered from
the most basic (does it respond at all?) to the more specific (schema, edge
cases, error paths).
"""


# ===========================================================================
# GET /api/courses
# ===========================================================================

class TestGetCourses:
    """Tests for GET /api/courses"""

    # --- status code --------------------------------------------------------

    def test_returns_200(self, client):
        resp = client.get("/api/courses")
        assert resp.status_code == 200

    # --- response schema ----------------------------------------------------

    def test_response_contains_total_courses(self, client):
        data = client.get("/api/courses").json()
        assert "total_courses" in data

    def test_response_contains_course_titles(self, client):
        data = client.get("/api/courses").json()
        assert "course_titles" in data

    def test_total_courses_is_integer(self, client):
        data = client.get("/api/courses").json()
        assert isinstance(data["total_courses"], int)

    def test_course_titles_is_list(self, client):
        data = client.get("/api/courses").json()
        assert isinstance(data["course_titles"], list)

    def test_no_extra_unexpected_fields(self, client):
        data = client.get("/api/courses").json()
        assert set(data.keys()) == {"total_courses", "course_titles"}

    # --- data correctness ---------------------------------------------------

    def test_course_titles_are_strings(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Course A", "Course B"],
        }
        data = client.get("/api/courses").json()
        for title in data["course_titles"]:
            assert isinstance(title, str)

    def test_total_courses_matches_returned_analytics(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["A", "B", "C"],
        }
        data = client.get("/api/courses").json()
        assert data["total_courses"] == 3
        assert data["course_titles"] == ["A", "B", "C"]

    def test_empty_catalog_returns_zero_and_empty_list(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }
        data = client.get("/api/courses").json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    # --- error handling -----------------------------------------------------

    def test_returns_500_when_analytics_raises(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("DB unavailable")
        resp = client.get("/api/courses")
        assert resp.status_code == 500

    def test_500_response_contains_detail(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("DB unavailable")
        data = client.get("/api/courses").json()
        assert "detail" in data


# ===========================================================================
# POST /api/query
# ===========================================================================

class TestPostQuery:
    """Tests for POST /api/query"""

    # --- status code --------------------------------------------------------

    def test_returns_200(self, client):
        resp = client.post("/api/query", json={"query": "What is Python?"})
        assert resp.status_code == 200

    # --- response schema ----------------------------------------------------

    def test_response_contains_answer(self, client):
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert "answer" in data

    def test_response_contains_sources(self, client):
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert "sources" in data

    def test_response_contains_session_id(self, client):
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert "session_id" in data

    def test_answer_is_string(self, client):
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert isinstance(data["answer"], str)

    def test_sources_is_list(self, client):
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert isinstance(data["sources"], list)

    def test_session_id_is_string(self, client):
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert isinstance(data["session_id"], str)

    def test_no_extra_unexpected_fields(self, client):
        data = client.post("/api/query", json={"query": "test"}).json()
        assert set(data.keys()) == {"answer", "sources", "session_id"}

    # --- session handling ---------------------------------------------------

    def test_creates_session_when_none_provided(self, client, mock_rag):
        mock_rag.session_manager.create_session.return_value = "session_auto_99"
        data = client.post("/api/query", json={"query": "Hello?"}).json()
        assert data["session_id"] == "session_auto_99"
        mock_rag.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, client, mock_rag):
        data = client.post(
            "/api/query",
            json={"query": "Follow-up question", "session_id": "my_existing_session"},
        ).json()
        assert data["session_id"] == "my_existing_session"
        # create_session must NOT be called when a session_id is already supplied
        mock_rag.session_manager.create_session.assert_not_called()

    def test_session_id_is_non_empty(self, client):
        data = client.post("/api/query", json={"query": "Hi"}).json()
        assert data["session_id"] != ""

    # --- query forwarding ---------------------------------------------------

    def test_query_text_forwarded_to_rag(self, client, mock_rag):
        client.post("/api/query", json={"query": "Tell me about decorators"})
        call_args = mock_rag.query.call_args
        # The first positional argument to rag_system.query() should contain
        # the user's question text
        assert "decorators" in call_args[0][0]

    def test_answer_matches_rag_return_value(self, client, mock_rag):
        mock_rag.query.return_value = ("Unique answer text XYZ", [])
        data = client.post("/api/query", json={"query": "anything"}).json()
        assert data["answer"] == "Unique answer text XYZ"

    def test_sources_match_rag_return_value(self, client, mock_rag):
        mock_rag.query.return_value = ("answer", ["fileA.txt", "fileB.txt"])
        data = client.post("/api/query", json={"query": "anything"}).json()
        assert data["sources"] == ["fileA.txt", "fileB.txt"]

    def test_empty_sources_list_returned(self, client, mock_rag):
        mock_rag.query.return_value = ("answer", [])
        data = client.post("/api/query", json={"query": "anything"}).json()
        assert data["sources"] == []

    # --- request validation -------------------------------------------------

    def test_missing_query_field_returns_422(self, client):
        resp = client.post("/api/query", json={"session_id": "abc"})
        assert resp.status_code == 422

    def test_empty_json_body_returns_422(self, client):
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_non_json_body_returns_422(self, client):
        resp = client.post(
            "/api/query",
            content=b"not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_null_query_returns_422(self, client):
        resp = client.post("/api/query", json={"query": None})
        assert resp.status_code == 422

    def test_empty_string_query_is_accepted(self, client):
        # Pydantic str fields accept empty strings by default
        resp = client.post("/api/query", json={"query": ""})
        assert resp.status_code == 200

    def test_numeric_query_returns_422(self, client):
        resp = client.post("/api/query", json={"query": 12345})
        assert resp.status_code == 422

    # --- error handling -----------------------------------------------------

    def test_returns_500_when_query_raises(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("LLM timeout")
        resp = client.post("/api/query", json={"query": "What is Python?"})
        assert resp.status_code == 500

    def test_500_response_contains_detail(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("LLM timeout")
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert "detail" in data
