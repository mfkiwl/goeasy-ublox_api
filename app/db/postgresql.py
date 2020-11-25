#!/usr/bin/env python3
"""
Database utility functions

:author: Angelo Cutaia
:copyright: Copyright 2020, Angelo Cutaia
:version: 1.0.0

..

    Copyright 2020 Angelo Cutaia

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
# Standard library
from datetime import datetime
from typing import List, Optional
# Third party
from asyncpg import Connection, create_pool
from asyncpg.pool import Pool
from asyncpg.exceptions import UndefinedTableError
# Internal
from ..models.satellite import RawData, Satellite
from ..config import get_database_settings

# -------------------------------------------


class DataBase:
    pool: Pool = None
    nation: str = None

    @classmethod
    async def connect(cls) -> None:
        settings = get_database_settings()
        cls.pool = await create_pool(
            user=settings.postgres_user,
            password=settings.postgres_pwd,
            database=settings.postgres_db,
            host=settings.postgres_host,
            port=settings.postgres_port
        )
        cls.nation = settings.nation

    @classmethod
    async def disconnect(cls):
        await cls.pool.terminate()

    @classmethod
    async def extract_satellites_info(
            cls,
            satellites: List[Satellite]
    ) -> List[Satellite]:
        """
        Extract all the raw data of the satellites list

        :param satellites: List of satellites and timestamp
        :return: A list containing all the satellites raw data in specific timestamp
        """
        async with cls.pool.acquire() as conn:
            for satellite in satellites:
                for raw_data in satellite.info:
                    raw_data.raw_data = await cls._extract_data(conn, satellite.satellite_id, raw_data.timestamp)
        return satellites

    @classmethod
    async def extract_raw_data(
            cls,
            satellite_id: int,
            timestamp: int
    ) -> RawData:
        """
         Extract Raw data of the Satellite in a specific timestamp

        :param satellite_id: Satellite id
        :param timestamp: Timestamp of the raw data to retrieve
        :return: Raw Data of the satellite in the required timestamp
        """
        async with cls.pool.acquire() as conn:
            return RawData(
                timestamp=timestamp,
                raw_data=await cls._extract_data(conn, satellite_id, timestamp)
            )

    @classmethod
    async def _extract_data(
            cls,
            conn: Connection,
            satellite_id: int,
            timestamp: int
    ) -> Optional[str]:
        """
        Utility function to extract data from the database

        :param conn: A connection to the database
        :param satellite_id: Id of the satellite
        :param timestamp: Of the data to retrieve
        :return: The Raw Data of the Satellite in the specified timestamp
        """
        try:
            return await conn.fetchval(
                f'SELECT raw_data '
                f'FROM "{datetime.fromtimestamp(timestamp).year}_{cls.nation}_{satellite_id}" '
                f'WHERE timestampmessage_unix '
                f'BETWEEN {timestamp - 1} AND {timestamp + 1};'
            )

        except UndefinedTableError:
            # No raw_data found
            return None

