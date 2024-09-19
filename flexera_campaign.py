import argparse
import logging

from json import loads, dumps
from typing import Optional, Generator

import http.client

from requests import HTTPError, Session, Response

http.client.HTTPConnection.debuglevel = 0  # 0 for off, >0 for on

log_level: int = logging.ERROR
logging.basicConfig()
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(log_level)
requests_log.propagate = True


def create_campaign(
        session: Session,
        domain: str,
        flexera_id: str,
) -> Generator[dict, None, None]:
    params: dict = {
        'flexera_id': flexera_id,
    }
    try:
        resp_campaign: Response = session.get(
            url=domain,
            params=params,
        )
        resp_campaign.raise_for_status()
        data: dict = resp_campaign.json()
        devices: list = data.get('data')
        yield from devices
    except HTTPError as exc_http:
        requests_log.error(f'{exc_http}: {exc_http.response.request.headers}')
    except Exception as exc_dev:
        requests_log.error(exc_dev)


def main(
        domain: str,
        username: str,
        password: str,
        flexera_id: str,
        proxies: Optional[dict] = None,
) -> Generator[dict, None, None]:
    session = Session()
    session.auth = (username, password)

    headers: dict = {
        'Accept': 'application/json',
    }
    session.headers = headers
    session.proxies = proxies

    yield from create_campaign(session=session, domain=domain, flexera_id=flexera_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--domain',
        default=None,
        type=str,
        required=True,
        help='The URL for your Flexera server',
    )
    parser.add_argument(
        '--username',
        default=None,
        type=str,
        required=True,
        help='The user name for your Flexera account',
    )
    parser.add_argument(
        '--password',
        default=None,
        type=str,
        required=True,
        help='The password for your Flexera account',
    )
    parser.add_argument(
        '--flexera_id',
        default=None,
        type=str,
        required=True,
        help='The Flexera ID for the software package',
    )
    parser.add_argument(
        '--proxies',
        type=str,
        required=False,
        help="JSON structure specifying 'http' and 'https' proxy URLs",
    )

    args = parser.parse_args()

    proxies: Optional[dict] = None
    if proxies:
        try:
            proxies: dict = loads(args.proxies)
        except Exception as exc_json:
            print(f'WARNING: failure parsing proxies: {exc_json}: proxies provided: {proxies}')

    for result in main(
        domain=args.domain,
        username=args.username,
        password=args.password,
        flexera_id=args.flexera_id,
        proxies=proxies,
    ):
        print(dumps(result, indent=4))
    else:
        print('End of results')
