import urllib.parse as urlparse
from io import StringIO
from typing import Any, Dict, List, Union

import aiohttp
import pandas as pd
import stringcase
from loguru import logger

from config import config as app_config


class AlphaVantageClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        api_endpoint: str = app_config.API_ENDPOINT,
    ):
        self._query_params = {"datatype": "json", "apikey": api_key}
        self._api_endpoint = api_endpoint
        self._session = session

    @logger.catch
    def _format_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make all keys snake_case."""
        formatted_data = {}

        for field, item in data.items():
            formatted_data[stringcase.snakecase(field)] = item

        return formatted_data

    @logger.catch
    async def _construct_query(
        self, function: str, to_json: bool = True, **kwargs
    ) -> Union[Dict[str, Any], str]:
        """Construct query with given parameters."""
        path = "query/"

        async with self._session.get(
            urlparse.urljoin(self._api_endpoint, path),
            params={"function": function, **kwargs, **self._query_params},
        ) as response:
            data = (
                await response.json() if to_json else await response.text()
            )

            if to_json:
                data = self._format_fields(data)

        return data

    @logger.catch
    async def get_securities(
        self,
        state: str = "active",
    ) -> List[Dict[str, str]]:
        """Get a list of securities."""
        data = await self._construct_query(
            "LISTING_STATUS",
            state=state,
            to_json=False,
        )

        data = pd.read_csv(StringIO(data))

        securities = data.to_dict("records")

        for index, security in enumerate(securities):
            security = self._format_fields(security)
            security["_type"] = "physical"

            securities[index] = security

        return securities

    @logger.catch
    async def get_security_overview(self, symbol: str) -> Dict[str, str]:
        return await self._construct_query("OVERVIEW", symbol=symbol)

    @logger.catch
    async def get_historical_data(self, symbol: str) -> Dict[str, Any]:
        return await self._construct_query(
            "TIME_SERIES_DAILY_ADJUSTED", symbol=symbol, outputsize="full"
        )

    @logger.catch
    async def get_last_price_data(self, symbol: str) -> Dict[str, Any]:
        return await self._construct_query("GLOBAL_QUOTE", symbol=symbol)

    @logger.catch
    async def get_indicator_data(
        self, symbol: str, indicator: str, **indicator_options
    ) -> Dict[str, Any]:
        return await self._construct_query(
            indicator, symbol=symbol, **indicator_options
        )
