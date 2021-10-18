import asyncio
from http import HTTPStatus
from unittest.mock import AsyncMock, patch  # Requires Python 3.8+.

import pytest
from httpx import Response

import purger


@pytest.mark.asyncio
@patch.object(purger.httpx.AsyncClient, "get", autospec=True)
async def test_get_forked_repos_ok(mock_async_get):
    mock_async_get.return_value = Response(
        status_code=HTTPStatus.OK,
    )
    mock_async_get.return_value.json = lambda: [
        {"fork": True, "url": "https://dummy_url.com"}
    ]

    result = await purger.get_forked_repos(
        username="dummy_username",
        token="dummy_token",
    )
    assert result == ["https://dummy_url.com"]


@pytest.mark.asyncio
@patch.object(purger.httpx.AsyncClient, "get", autospec=True)
async def test_get_forked_repos_empty(mock_async_get):
    mock_async_get.return_value = Response(
        status_code=HTTPStatus.OK,
    )
    mock_async_get.return_value.json = lambda: []

    result = await purger.get_forked_repos(
        username="dummy_username",
        token="dummy_token",
    )
    assert result == []


@pytest.mark.asyncio
@patch.object(purger.httpx.AsyncClient, "get", autospec=True)
async def test_get_forked_repos_error(mock_async_get):
    mock_async_get.return_value = Response(
        status_code=HTTPStatus.FORBIDDEN,
    )
    mock_async_get.return_value.json = lambda: []

    with pytest.raises(Exception):
        result = await purger.get_forked_repos(
            username="dummy_username",
            token="dummy_token",
        )
        assert result == []


@pytest.mark.asyncio
@patch.object(purger.httpx.AsyncClient, "delete", autospec=True)
async def test_delete_forked_repo_ok(mock_async_delete, capsys):
    # Test dry run ok.
    mock_async_delete.return_value = Response(
        status_code=HTTPStatus.OK,
    )
    mock_async_delete.return_value.json = lambda: []

    result = await purger.delete_forked_repo(
        url="https://dummy_url.com",
        token="dummy_token",
    )
    out, err = capsys.readouterr()

    assert result is None
    assert err == ""
    assert "https://dummy_url.com" in out

    # Test delete ok.
    result = await purger.delete_forked_repo(
        url="https://dummy_url.com",
        token="dummy_token",
        delete=True,
    )
    out, err = capsys.readouterr()

    assert result is None
    assert err == ""
    assert "Deleting..." in out


@pytest.mark.asyncio
@patch.object(purger.httpx.AsyncClient, "delete", autospec=True)
async def test_delete_forked_repo_error(mock_async_delete, capsys):
    mock_async_delete.return_value = Response(
        status_code=HTTPStatus.FORBIDDEN,
    )
    mock_async_delete.return_value.json = lambda: []

    # Test delete error.
    with pytest.raises(Exception):
        await purger.delete_forked_repo(
            url="https://dummy_url.com",
            token="dummy_token",
            delete=True,
        )
    out, err = capsys.readouterr()

    assert err == ""
    assert "Deleting..." in out


@pytest.mark.asyncio
@patch.object(purger.httpx.AsyncClient, "get", autospec=True)
async def test_enqueue_ok(mock_async_get):
    mock_async_get.return_value = Response(
        status_code=HTTPStatus.OK,
    )
    mock_async_get.return_value.json = lambda: [
        {"fork": True, "url": "https://dummy_url_1.com"},
        {"fork": True, "url": "https://dummy_url_2.com"},
    ]

    queue = asyncio.Queue()
    event = asyncio.Event()

    result = await purger.enqueue(queue, event, "dummy_username", "dummy_token", 1)
    assert result is None 
    assert queue.qsize() == 2
    assert event.is_set() is False
