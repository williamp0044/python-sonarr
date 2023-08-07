"""Asynchronous Python client for Sonarr."""
from typing import List, Optional

from aiohttp.client import ClientSession

from .client import Client
from .exceptions import SonarrError
from .models import (
    Application,
    CommandItem,
    Episode,
    QueueItem,
    SeriesItem,
    WantedResults,
)


class Sonarr(Client):
    """Main class for Python API."""

    _application: Optional[Application] = None

    def __init__(
        self,
        host: str,
        api_key: str,
        base_path: str = "/api/",
        port: int = 8989,
        request_timeout: int = 30,
        session: ClientSession = None,
        tls: bool = False,
        verify_ssl: bool = True,
        user_agent: str = None,
    ) -> None:
        """Initialize connection with Sonarr."""
        super().__init__(
            host=host,
            api_key=api_key,
            base_path=base_path,
            port=port,
            request_timeout=request_timeout,
            session=session,
            tls=tls,
            verify_ssl=verify_ssl,
            user_agent=user_agent,
        )

    @property
    def app(self) -> Optional[Application]:
        """Return the cached Application object."""
        return self._application

    async def update(self, full_update: bool = False) -> Application:
        """Get all information about the application in a single call."""
        if self._application is None or full_update:
            status = await self._request("system/status")
            if status is None:
                raise SonarrError("Sonarr returned an empty API status response")

            diskspace = await self._request("diskspace")

            self._application = Application({"info": status, "diskspace": diskspace})
            return self._application

        diskspace = await self._request("diskspace")
        self._application.update_from_dict({"diskspace": diskspace})
        return self._application

    async def calendar(self, start: str = None, end: str = None) -> List[Episode]:
        """Get upcoming episodes.

        If start/end are not supplied, episodes airing
        today and tomorrow will be returned.
        """
        params = {}

        if start is not None:
            params["start"] = str(start)

        if end is not None:
            params["end"] = str(end)

        results = await self._request("calendar", params=params)

        return [Episode.from_dict(result) for result in results]

    async def commands(self) -> List[CommandItem]:
        """Query the status of all currently started commands."""
        results = await self._request("command")

        return [CommandItem.from_dict(result) for result in results]

    async def command_status(self, command_id: int) -> CommandItem:
        """Query the status of a previously started command."""
        result = await self._request(f"command/{command_id}")

        return CommandItem.from_dict(result)

    async def queue(self) -> List[QueueItem]:
        """Get currently downloading info."""
        results = await self._request("queue")

        return [QueueItem.from_dict(result) for result in results]

    async def series(self) -> List[SeriesItem]:
        """Return all series."""
        results = await self._request("series")

        return [SeriesItem.from_dict(result) for result in results]

    async def wanted(
        self,
        sort_key: str = "airDateUtc",
        page: int = 1,
        page_size: int = 10,
        sort_dir: str = "desc",
    ) -> WantedResults:
        """Get wanted missing episodes."""
        params = {
            "sortKey": sort_key,
            "page": str(page),
            "pageSize": str(page_size),
            "sortDir": sort_dir,
        }

        results = await self._request("wanted/missing", params=params)

        return WantedResults.from_dict(results)

    async def __aenter__(self) -> "Sonarr":
        """Async enter."""
        return self

    async def __aexit__(self, *exc_info) -> None:
        """Async exit."""
        await self.close_session()


    async def get_series(self, title: str) -> List[SeriesItem]:
        """Search for a series by title."""
        results = await self._request(f"series/lookup?term={title}")

        # If you want to return all matching series.
        return [SeriesItem.from_dict(result) for result in results]

        # If you want to return only the first matching series.
        # Uncomment below:
        # if results:
        #     return SeriesItem.from_dict(results[0])
    
    async def add_series(self, series_item: SeriesItem):
        """Add a series to the Sonarr collection."""
        series = {
            'title': series_item.series.title,
            'qualityProfileId': 1,  # Specify quality profile
            'titleSlug': series_item.series.slug,  
            'images': [{'coverType': 'poster', 'url': series_item.series.poster}],  
            'tvdbId': series_item.series.tvdb_id,  
            'path': f"/tv/{series_item.series.title}",  # specify the path to save series
            'seasons': [season.to_dict() for season in series_item.seasons],
            'rootFolderPath': "/tv",  # specify your root folder path
            'monitored': True,
            'addOptions': {
                'searchForMissingEpisodes': True,
            }
        }
        response = await self._request("series", method='POST', data=series)
        return response  # You might want to handle/inspect the response


if __name__ == "__main__":
    async def main():
        async with Sonarr("192.168.1.222", "3da4c80e94e24e45b0e6491fff4d91c0") as sonarr:
            # Search for the series
            series_list = await sonarr.get_series('Friends')

            # Print out the list of matched series
            for series in series_list:
                print(series)

            # Add the first series from the search result to your Sonarr collection
            if series_list:
                response = await sonarr.add_series(series_list[0])
                print(response)  # Print the response after adding, you can handle this however you want.

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
