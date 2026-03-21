"""Tests for writer.py."""

from pathlib import Path
from unittest import mock

from openapi2skill import writer
from openapi2skill.models import Endpoint, TagGroup


def test_generate_filename_simple() -> None:
    """Test simple path to filename conversion."""
    result = writer.generate_filename("GET", "/users")
    assert result == "get_users.md"


def test_generate_filename_with_path_param() -> None:
    """Test path parameter braces are stripped."""
    result = writer.generate_filename("POST", "/users/{id}")
    assert result == "post_users_id.md"


def test_generate_filename_nested_path() -> None:
    """Test complex nested path."""
    result = writer.generate_filename("POST", "/api/users/{id}/roles")
    assert result == "post_api_users_id_roles.md"


def test_generate_filename_root_path() -> None:
    """Test root path."""
    result = writer.generate_filename("GET", "/")
    assert result == "get.md"


def test_generate_filename_multiple_path_params() -> None:
    """Test multiple path parameters."""
    result = writer.generate_filename("GET", "/orgs/{org_id}/repos/{repo_id}")
    assert result == "get_orgs_org_id_repos_repo_id.md"


def test_generate_filename_uppercase_method() -> None:
    """Test that method is lowercased."""
    result = writer.generate_filename("DELETE", "/users/{id}")
    assert result.startswith("delete_")


def test_assign_filenames_no_collision() -> None:
    """Test unique filenames are assigned without modification."""
    endpoints = [
        Endpoint(
            path="/users",
            method="GET",
            summary="",
            description="",
            tag="Users",
            parameters=[],
            request_body=None,
            responses=[],
        ),
        Endpoint(
            path="/products",
            method="GET",
            summary="",
            description="",
            tag="Products",
            parameters=[],
            request_body=None,
            responses=[],
        ),
    ]

    result = writer.assign_filenames(endpoints)

    assert result["GET_/users"] == "get_users.md"
    assert result["GET_/products"] == "get_products.md"


def test_assign_filenames_collision() -> None:
    """Test that collisions are resolved with _2, _3 suffixes."""
    # Two endpoints that would generate the same filename
    endpoints = [
        Endpoint(
            path="/users",
            method="GET",
            summary="",
            description="",
            tag="Users",
            parameters=[],
            request_body=None,
            responses=[],
        ),
        Endpoint(
            path="/Users",  # Different case, same filename
            method="GET",
            summary="",
            description="",
            tag="Users",
            parameters=[],
            request_body=None,
            responses=[],
        ),
    ]

    result = writer.assign_filenames(endpoints)

    assert result["GET_/users"] == "get_users.md"
    assert result["GET_/Users"] == "get_users_2.md"


def test_assign_filenames_multiple_collisions() -> None:
    """Test multiple collisions are handled correctly."""
    endpoints = [
        Endpoint(
            path="/test",
            method="GET",
            summary="",
            description="",
            tag="Test",
            parameters=[],
            request_body=None,
            responses=[],
        ),
        Endpoint(
            path="/Test",
            method="GET",
            summary="",
            description="",
            tag="Test",
            parameters=[],
            request_body=None,
            responses=[],
        ),
        Endpoint(
            path="/TEST",
            method="GET",
            summary="",
            description="",
            tag="Test",
            parameters=[],
            request_body=None,
            responses=[],
        ),
    ]

    result = writer.assign_filenames(endpoints)

    assert result["GET_/test"] == "get_test.md"
    assert result["GET_/Test"] == "get_test_2.md"
    assert result["GET_/TEST"] == "get_test_3.md"


def test_write_output_creates_directory(tmp_path: Path) -> None:
    """Test that timestamped directory is created."""
    base_dir = str(tmp_path / "output")
    skill_md = "# Test"
    tag_api_lists = []
    references = []

    with mock.patch("openapi2skill.writer.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-03-19_120000"
        result = writer.write_output(base_dir, skill_md, tag_api_lists, references)

    assert result.endswith("2026-03-19_120000")
    assert Path(result).exists()


def test_write_output_creates_reference_subdir(tmp_path: Path) -> None:
    """Test that reference subdirectory is created."""
    base_dir = str(tmp_path / "output")
    skill_md = "# Test"
    tag_api_lists = []
    references = []

    with mock.patch("openapi2skill.writer.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-03-19_120000"
        result = writer.write_output(base_dir, skill_md, tag_api_lists, references)

    reference_dir = Path(result) / "reference"
    assert reference_dir.exists()
    assert reference_dir.is_dir()


def test_write_output_writes_skill_md(tmp_path: Path) -> None:
    """Test that SKILL.md is written correctly."""
    base_dir = str(tmp_path / "output")
    skill_md = "# My API\n\nThis is a test."
    tag_api_lists = []
    references = []

    with mock.patch("openapi2skill.writer.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-03-19_120000"
        result = writer.write_output(base_dir, skill_md, tag_api_lists, references)

    skill_file = Path(result) / "SKILL.md"
    assert skill_file.exists()
    assert skill_file.read_text() == skill_md


def test_write_output_writes_references(tmp_path: Path) -> None:
    """Test that reference files are written correctly."""
    base_dir = str(tmp_path / "output")
    skill_md = "# Test"
    tag_api_lists = []
    references = [
        ("get_users.md", "# Get Users\n\nContent here."),
        ("post_users.md", "# Create User\n\nMore content."),
    ]

    with mock.patch("openapi2skill.writer.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-03-19_120000"
        result = writer.write_output(base_dir, skill_md, tag_api_lists, references)

    ref_dir = Path(result) / "reference"
    assert (ref_dir / "get_users.md").exists()
    assert (ref_dir / "post_users.md").exists()
    assert (ref_dir / "get_users.md").read_text() == "# Get Users\n\nContent here."
    assert (ref_dir / "post_users.md").read_text() == "# Create User\n\nMore content."


def test_write_output_returns_path(tmp_path: Path) -> None:
    """Test that the created directory path is returned."""
    base_dir = str(tmp_path / "output")
    skill_md = "# Test"
    tag_api_lists = []
    references = []

    with mock.patch("openapi2skill.writer.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-03-19_143052"
        result = writer.write_output(base_dir, skill_md, tag_api_lists, references)

    assert "2026-03-19_143052" in result
    assert Path(result).is_absolute() or result.startswith("./")


def test_write_output_creates_base_dir(tmp_path: Path) -> None:
    """Test that base output directory is created if it doesn't exist."""
    base_dir = str(tmp_path / "new_output_dir")
    skill_md = "# Test"
    tag_api_lists = []
    references = []

    with mock.patch("openapi2skill.writer.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-03-19_120000"
        writer.write_output(base_dir, skill_md, tag_api_lists, references)

    assert Path(base_dir).exists()


def test_write_output_empty_references(tmp_path: Path) -> None:
    """Test writing with no reference files."""
    base_dir = str(tmp_path / "output")
    skill_md = "# Empty API"
    tag_api_lists = []
    references = []

    with mock.patch("openapi2skill.writer.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-03-19_120000"
        result = writer.write_output(base_dir, skill_md, tag_api_lists, references)

    reference_dir = Path(result) / "reference"
    assert reference_dir.exists()
    # Reference dir should be empty
    assert list(reference_dir.iterdir()) == []


# Tests for generate_tag_filename


def test_generate_tag_filename_simple() -> None:
    """Test simple tag name to filename conversion."""
    result = writer.generate_tag_filename("Users")
    assert result == "users_api_list.md"


def test_generate_tag_filename_with_spaces() -> None:
    """Test tag name with spaces."""
    result = writer.generate_tag_filename("Prompt Optimization")
    assert result == "prompt_optimization_api_list.md"


def test_generate_tag_filename_with_special_chars() -> None:
    """Test tag name with special characters."""
    result = writer.generate_tag_filename("RAG/Search")
    assert result == "ragsearch_api_list.md"


def test_generate_tag_filename_with_slash() -> None:
    """Test tag name with slash is sanitized."""
    result = writer.generate_tag_filename("API/v1")
    assert result == "apiv1_api_list.md"


def test_generate_tag_filename_with_multiple_underscores() -> None:
    """Test multiple underscores are collapsed."""
    result = writer.generate_tag_filename("API  __  Test")
    assert result == "api_test_api_list.md"


def test_generate_tag_filename_leading_trailing_spaces() -> None:
    """Test leading/trailing underscores are stripped."""
    result = writer.generate_tag_filename("  Test  ")
    assert result == "test_api_list.md"


def test_generate_tag_filename_uppercase() -> None:
    """Test uppercase is converted to lowercase."""
    result = writer.generate_tag_filename("PROJECTS")
    assert result == "projects_api_list.md"


# Tests for assign_tag_filenames


def test_assign_tag_filenames_no_collision() -> None:
    """Test unique tag filenames are assigned without modification."""
    tag_groups = [
        TagGroup(
            name="Users",
            description="",
            endpoints=[
                Endpoint(
                    path="/users",
                    method="GET",
                    summary="",
                    description="",
                    tag="Users",
                    parameters=[],
                    request_body=None,
                    responses=[],
                )
            ],
        ),
        TagGroup(
            name="Products",
            description="",
            endpoints=[
                Endpoint(
                    path="/products",
                    method="GET",
                    summary="",
                    description="",
                    tag="Products",
                    parameters=[],
                    request_body=None,
                    responses=[],
                )
            ],
        ),
    ]

    result = writer.assign_tag_filenames(tag_groups)

    assert result["Users"] == "users_api_list.md"
    assert result["Products"] == "products_api_list.md"


def test_assign_tag_filenames_collision() -> None:
    """Test that tag filename collisions are resolved with _2 suffix."""
    # Two tags that would generate the same filename
    tag_groups = [
        TagGroup(
            name="RAG/Search",
            description="",
            endpoints=[
                Endpoint(
                    path="/rag/search",
                    method="GET",
                    summary="",
                    description="",
                    tag="RAG/Search",
                    parameters=[],
                    request_body=None,
                    responses=[],
                )
            ],
        ),
        TagGroup(
            name="RAG\\Search",  # Different tag, same sanitized filename (both slashes removed)
            description="",
            endpoints=[
                Endpoint(
                    path="/rag",
                    method="GET",
                    summary="",
                    description="",
                    tag="RAG\\Search",
                    parameters=[],
                    request_body=None,
                    responses=[],
                )
            ],
        ),
    ]

    result = writer.assign_tag_filenames(tag_groups)

    assert result["RAG/Search"] == "ragsearch_api_list.md"
    assert result["RAG\\Search"] == "ragsearch_api_list_2.md"


def test_assign_tag_filenames_multiple_collisions() -> None:
    """Test multiple collisions are handled correctly."""
    tag_groups = [
        TagGroup(
            name="Test",
            description="",
            endpoints=[
                Endpoint(
                    path="/test",
                    method="GET",
                    summary="",
                    description="",
                    tag="Test",
                    parameters=[],
                    request_body=None,
                    responses=[],
                )
            ],
        ),
        TagGroup(
            name="TEST",  # Same lowercase
            description="",
            endpoints=[
                Endpoint(
                    path="/test2",
                    method="GET",
                    summary="",
                    description="",
                    tag="TEST",
                    parameters=[],
                    request_body=None,
                    responses=[],
                )
            ],
        ),
        TagGroup(
            name="test",  # Same lowercase
            description="",
            endpoints=[
                Endpoint(
                    path="/test3",
                    method="GET",
                    summary="",
                    description="",
                    tag="test",
                    parameters=[],
                    request_body=None,
                    responses=[],
                )
            ],
        ),
    ]

    result = writer.assign_tag_filenames(tag_groups)

    assert result["Test"] == "test_api_list.md"
    assert result["TEST"] == "test_api_list_2.md"
    assert result["test"] == "test_api_list_3.md"


# Tests for write_output with tag API lists


def test_write_output_writes_tag_api_lists(tmp_path: Path) -> None:
    """Test that tag API list files are written to reference/."""
    base_dir = str(tmp_path / "output")
    skill_md = "# Test"
    tag_api_lists = [
        ("users_api_list.md", "# Users API\n\nUser endpoints."),
        ("products_api_list.md", "# Products API\n\nProduct endpoints."),
    ]
    references = []

    with mock.patch("openapi2skill.writer.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-03-19_120000"
        result = writer.write_output(base_dir, skill_md, tag_api_lists, references)

    ref_dir = Path(result) / "reference"
    assert (ref_dir / "users_api_list.md").exists()
    assert (ref_dir / "products_api_list.md").exists()
    assert (
        ref_dir / "users_api_list.md"
    ).read_text() == "# Users API\n\nUser endpoints."
    assert (
        ref_dir / "products_api_list.md"
    ).read_text() == "# Products API\n\nProduct endpoints."
