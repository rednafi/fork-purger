import asyncio
import importlib
import textwrap
from http import HTTPStatus
from unittest.mock import patch  # Requires Python 3.8+.

import pytest
from click.testing import CliRunner
from httpx import Response

import purger.main as purger


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

    result = await purger.enqueue(
        queue=queue,
        event=event,
        username="dummy_username",
        token="dummy_token",
        stop_after=1,
    )
    assert result is None
    assert queue.qsize() == 2
    assert event.is_set() is False


@patch("purger.main.delete_forked_repo", autospec=True)
async def test_dequeue_ok(mock_delete_forked_repo):
    mock_delete_forked_repo.return_value = None

    queue = asyncio.Queue()
    event = asyncio.Event()
    queue.put_nowait("https://dummy_url_1.com")
    queue.put_nowait("https://dummy_url_2.com")

    event.set()

    result = await purger.dequeue(
        queue=queue,
        event=event,
        token="dummy_token",
        delete=False,
        stop_after=2,
    )

    assert result is None
    assert queue.qsize() == 0
    assert event.is_set() is True


@patch("purger.main.MAX_CONCURRENCY", default=1)
@patch("purger.main.enqueue", autospec=True)
@patch("purger.main.dequeue", autospec=True)
@patch("purger.main.asyncio.Queue", autospec=True)
@patch("purger.main.asyncio.Event", autospec=True)
@patch("purger.main.asyncio.create_task", autospec=True)
@patch("purger.main.asyncio.wait", autospec=True)
async def test_orchestrator_ok(
    mock_wait,
    mock_create_task,
    mock_event,
    mock_queue,
    mock_dequeue,
    mock_enqueue,
    _,
):

    # Mocked futures.
    done_future = asyncio.Future()
    done_future.set_result(42)
    await done_future

    pending_future = asyncio.Future()
    done_futures, pending_futures = [done_future], [pending_future]

    mock_wait.return_value = (done_futures, pending_futures)

    # Called the mocked function.
    await purger.orchestrator(
        username="dummy_username",
        token="dummy_token",
        delete=False,
    )

    # Assert.
    mock_queue.assert_called_once()
    mock_queue().join.assert_called_once()
    mock_event.assert_called_once()
    mock_create_task.assert_called()
    mock_wait.assert_awaited_once()
    mock_enqueue.assert_called_once()
    mock_dequeue.assert_called_once()


@patch("purger.main.orchestrator", autospec=True)
@patch("purger.main.asyncio.run", autospec=True)
def test__cli(mock_asyncio_run, mock_orchestrator):
    runner = CliRunner()

    # Test cli without any arguments.
    result = runner.invoke(purger._cli, [])
    assert result.exit_code != 0

    result = runner.invoke(
        purger._cli,
        ["--username=dummy_username", "--token=dummy_token"],
    )
    assert result.exit_code == 0
    mock_orchestrator.assert_called_once()
    mock_asyncio_run.assert_called_once()

    result = runner.invoke(
        purger._cli,
        ["--username=dummy_username", "--token=dummy_token", "--no-debug"],
    )
    assert result.exit_code == 0
    mock_orchestrator.assert_called()
    mock_asyncio_run.assert_called()

    result = runner.invoke(
        purger._cli,
        ["--username=dummy_username", "--token=dummy_token", "--delete"],
    )
    assert result.exit_code == 0
    mock_orchestrator.assert_called()
    mock_asyncio_run.assert_called()


@patch("purger.main.click.command", autospec=True)
@patch("purger.main.click.option", autospec=True)
@patch("purger.main._cli", autospec=True)
def test_dummy_cli(mock_cli, mock_click_option, mock_click_command, capsys):

    # Decorators are executed during import time. So for the 'patch' to work,
    # the module needs to be reloaded.
    importlib.reload(purger)

    # Since we're invoking the cli function without any parameter, it should
    # exit with an error code > 0.
    purger.cli()
    err, out = capsys.readouterr()

    # Test greeting message.
    greet_msg = textwrap.dedent(
        """
                +-+-+-+-+ +-+-+-+-+-+-+
                |F|o|r|k| |P|u|r|g|e|r|
                +-+-+-+-+ +-+-+-+-+-+-+
        """
    )

    assert greet_msg in err
    assert out == ""
