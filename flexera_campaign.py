import argparse
import logging
import sys

from json import loads, dumps
from typing import Optional

import http.client

from requests import HTTPError, Session, Response
from requests_ntlm import HttpNtlmAuth
from zeep import Client, Transport, xsd

http.client.HTTPConnection.debuglevel = 0  # 0 for off, >0 for on

log_level: int = logging.INFO
logging.basicConfig()
logger = logging.getLogger("requests.packages.urllib3")
logger.setLevel(log_level)
logger.propagate = True


def modify_retire_campaign_rest(
        session: Session,
        domain: str,
        flexera_id: str = '',
        group_id: str = '',
) -> str:
    try:
        url: str = f'{domain}/esd/api/Campaigns'
        data: list = [
            {
                'campaignType': 3,
                'flexeraId': flexera_id,
                'propertyType': 'Group',
                'propertyName': 'memberOf',
                'propertyValue': group_id,
                'visible': True,
                'applyChildOU': False,
                'propertyDisplayName': group_id,
            },
        ]
        resp_campaign: Response = session.post(
            url=url,
            params={
                'flexeraid': flexera_id,
                'CampaignType': 3,
            },
            json=data,
        )
        return resp_campaign.text

    except HTTPError as http_error:
        # msg: str = f'''REST RESPONSE: {http_error}:
        # STATUS: {http_error.response.status_code}
        # HEADERS: {http_error.request.headers}
        # BODY: {http_error.request.body}'''
        # print(msg, file=sys.stderr)
        logger.exception(http_error)
    except Exception as exc_campaign_rest:
        logger.exception(exc_campaign_rest)


def create_retire_campaign_soap(
        session: Session,
        domain: str,
        flexera_id: str = '',
) -> xsd.CompoundValue:
    url: str = f'{domain}/esd/ws/integration.asmx'
    wsdl: Optional[str] = None
    try:
        resp_wsdl: Response = session.get(url=f'{url}?WSDL')
        resp_wsdl.raise_for_status()
        wsdl: str = resp_wsdl.text
        logger.debug(f'WSDL: {wsdl}')
    except HTTPError as http_error_wsdl:
        msg: str = f'''WSDL RESPONSE: {http_error_wsdl}:
        STATUS: {http_error_wsdl.response.status_code}
        HEADERS: {http_error_wsdl.request.headers}
        BODY: {http_error_wsdl.request.body}'''
        print(msg, file=sys.stderr)
        logger.exception(http_error_wsdl)
    except Exception as exc_wsdl:
        logger.exception(f'Error getting WSDL: {exc_wsdl}')
        raise exc_wsdl

    client = Client(wsdl, transport=Transport(session=session))
    resp_campaign: xsd.CompoundValue = client.service.AddFlexeraIdForRetireCampaign(flexera_id)
    logger.debug(f'\n\n\n\nCAMPAIGN RESPONSE: {resp_campaign}\n\n\n\n')

    return resp_campaign


def main(
        domain: str,
        username: str,
        password: str,
        flexera_id: str,
        group_id: str,
        proxies: Optional[dict] = None,
) -> list:
    session = Session()
    session.auth = HttpNtlmAuth(username, password)

    headers: dict = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    session.headers = headers
    session.proxies = proxies
    session.verify = False

    resp_campaign = create_retire_campaign_soap(session=session, domain=domain, flexera_id=flexera_id)
    resp_modify = modify_retire_campaign_rest(session=session, domain=domain, flexera_id=flexera_id, group_id=group_id)

    return [resp_campaign, resp_modify]


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
        '--group_id',
        default=None,
        type=str,
        required=True,
        help='The AD Group ID for the software campaign policy',
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
        group_id=args.group_id,
        proxies=proxies,
    ):
        print(result)
