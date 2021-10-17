import asyncio
from http import HTTPStatus

import httpx
from rich.pretty import pprint
from rich.traceback import install

install()

MAX_CONCURRENCY = 5


async def get_forked_repos(
    username: str,
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
        "Authorization": "Token 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",
    }

    forked_urls = []  # type: list[str]
    async with httpx.AsyncClient(http2=True) as client:
        res = await client.get(url, headers=headers)

        if not res.status_code == HTTPStatus.OK:
            raise httpx.HTTPError(f"{res.json()}")

        results = res.json()

        if not results:
            return forked_urls

        for result in results:
            if result["fork"] is True:
                forked_urls.append(result["url"])

    return forked_urls


async def delete_forked_repo(url: str) -> None:
    pprint(f"deleted!{url}")


async def enqueue(queue: asyncio.Queue[str], event: asyncio.Event) -> None:
    """
    Collects the URLs of all the forked repos and inject them into an
    async queue.

    Parameters
    ----------
    queue : asyncio.Queue[str]
        Async queue where the forked repo URLs are injected.
    event : asyncio.Event
        Async event for coroutine synchronization.
    """

    page = 1
    while True:
        forked_urls = await get_forked_repos(username="rednafi", page=page)

        for forked_url in forked_urls:
            await queue.put(forked_url)

        page += 1
        event.set()
        await asyncio.sleep(0)


async def dequeue(queue: asyncio.Queue[str], event: asyncio.Event) -> None:
    """
    Collects forked repo URLs from the async queue and deletes
    them concurrently.

    Parameters
    ----------
    queue : asyncio.Queue[str]
        Async queue where the forked repo URLs are popped off.
    event : asyncio.Event
        Async event for coroutine synchronization.
    """

    while True:
        await event.wait()

        if not queue.empty():
            forked_url = await queue.get()
        else:
            break

        await delete_forked_repo(forked_url)

        # Yields control to the event loop.
        await asyncio.sleep(0)

        queue.task_done()


async def orchestrator() -> None:
    """
    Coordinates the enqueue and dequeue functions in a
    producer-consumer setup.
    """

    queue = asyncio.Queue()
    event = asyncio.Event()

    _ = asyncio.create_task(enqueue(queue, event))

    dequeue_tasks = [
        asyncio.create_task(dequeue(queue, event)) for _ in range(MAX_CONCURRENCY)
    ]

    await asyncio.gather(*dequeue_tasks)

    for t in dequeue_tasks:
        t.cancel()

    # This runs the 'enqueue' function implicitly.
    await queue.join()


asyncio.run(orchestrator())
