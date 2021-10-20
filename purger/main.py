from __future__ import annotations

import asyncio
import sys
import textwrap
from http import HTTPStatus
from pprint import pformat

import click
import httpx

MAX_CONCURRENCY = 5


async def get_forked_repos(
    username: str,
    token: str,
    page: int = 1,
    per_page: int = 100,
) -> list[str]:

    """Get the URLs of forked repos in a page."""

    url = (
        f"https://api.github.com/users/{username}/repos"
        f"?page={page}&per_page={per_page}"
    )

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Token {token}",
    }

    forked_urls = []  # type: list[str]
    async with httpx.AsyncClient(http2=True) as client:
        res = await client.get(url, headers=headers)

        if not res.status_code == HTTPStatus.OK:
            raise Exception(f"{pformat(res.json())}")

        results = res.json()

        if not results:
            return forked_urls

        for result in results:
            if result["fork"] is True:
                forked_urls.append(result["url"])

    return forked_urls


async def delete_forked_repo(url: str, token: str, delete: bool = False) -> None:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Token {token}",
    }
    if not delete:
        print(url)
        return None

    client = httpx.AsyncClient(http2=True)

    async with client:
        print(f"Deleting... {url}")

        res = await client.delete(url, headers=headers)

        status_code = res.status_code
        if status_code not in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            raise Exception(f"HTTP error: {res.status_code}.")


async def enqueue(
    queue: asyncio.Queue[str],
    event: asyncio.Event,
    username: str,
    token: str,
    stop_after: int | None = None,
) -> None:
    """
    Collects the URLs of all the forked repos and inject them into an
    async queue.

    Parameters
    ----------
    queue : asyncio.Queue[str]
        Async queue where the forked repo URLs are injected.
    event : asyncio.Event
        Async event for coroutine synchronization.
    username : str
        Github username.
    token : str
        Github access token.
    stop_after : int | None
        Stop the while loop after `stop_after` iterations.
    """

    page = 1
    while True:
        forked_urls = await get_forked_repos(
            username=username,
            token=token,
            page=page,
        )
        if not forked_urls:
            break

        for forked_url in forked_urls:
            await queue.put(forked_url)

        if stop_after == page:
            break

        page += 1
        event.set()
        await asyncio.sleep(0.3)


async def dequeue(
    queue: asyncio.Queue[str],
    event: asyncio.Event,
    token: str,
    delete: bool,
    stop_after: int | None = None,
) -> None:
    """
    Collects forked repo URLs from the async queue and deletes
    them concurrently.

    Parameters
    ----------
    queue : asyncio.Queue[str]
        Async queue where the forked repo URLs are popped off.
    event : asyncio.Event
        Async event for coroutine synchronization.
    token : str
        Github access token.
    delete : bool
        Whether to delete the forked repos or not.
    stop_after : asyncio.Event
        Stop the while loop after `stop_after` iterations.
    """
    cnt = 0
    while True:
        await event.wait()

        forked_url = await queue.get()

        await delete_forked_repo(forked_url, token, delete)

        # Yields control to the event loop.
        await asyncio.sleep(0)

        queue.task_done()
        cnt += 1

        if stop_after and stop_after == cnt:
            break


async def orchestrator(username: str, token: str, delete: bool) -> None:
    """
    Coordinates the enqueue and dequeue functions in a
    producer-consumer setup.
    """

    queue = asyncio.Queue()  # type: asyncio.Queue[str]
    event = asyncio.Event()  # type: asyncio.Event

    enqueue_task = asyncio.create_task(enqueue(queue, event, username, token))

    dequeue_tasks = [
        asyncio.create_task(dequeue(queue, event, token, delete))
        for _ in range(MAX_CONCURRENCY)
    ]

    dequeue_tasks.append(enqueue_task)

    done, pending = await asyncio.wait(
        dequeue_tasks,
        return_when=asyncio.FIRST_COMPLETED,
    )

    for fut in done:
        try:
            exc = fut.exception()
            if exc:
                raise exc
        except asyncio.exceptions.InvalidStateError:
            pass

    for t in pending:
        t.cancel()

    # This runs the 'enqueue' function implicitly.
    await queue.join()


@click.command()
@click.option(
    "--username",
    help="Your Github username.",
    required=True,
)
@click.option(
    "--token",
    help="Your Github access token with delete permission.",
    required=True,
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="See full traceback in case of HTTP error.",
)
@click.option(
    "--delete",
    is_flag=True,
    default=False,
    help="Delete the forked repos.",
)
def _cli(username, token, debug, delete):
    if debug is False:
        sys.tracebacklimit = 0

    if not delete:
        click.echo("These forks will be deleted:")
        click.echo("=============================\n")

    elif delete:
        click.echo("Deleting forked repos:")
        click.echo("=======================\n")

    asyncio.run(orchestrator(username, token, delete))


def cli():
    greet_text = textwrap.dedent(
        """
            +-+-+-+-+ +-+-+-+-+-+-+
            |F|o|r|k| |P|u|r|g|e|r|
            +-+-+-+-+ +-+-+-+-+-+-+
        """
    )
    click.echo(greet_text)
    _cli()


if __name__ == "__main__":
    cli()
