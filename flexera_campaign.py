import http.client
from argparse import ArgumentParser, Namespace
from json import dumps, loads
from logging import getLogger, WARNING
from logging.config import dictConfig
from typing import Optional

from requests import HTTPError, Response, Session
from requests_ntlm import HttpNtlmAuth
from zeep import Client, Transport, xsd

global logger


def configure_logging(log_level: int = WARNING) -> None:
    global logger
    http.client.HTTPConnection.debuglevel = log_level or 0  # 0 for off, >0 for on
    dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'default': {
                    'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                },
            },
            'handlers': {
                'default': {
                    'level': log_level,
                    'formatter': 'default',
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout',  # Default is stderr
                },
            },
            'loggers': {
                '': {  # root logger
                    'level': log_level,
                    'propagate': True,
                    'handlers': [
                        'default',
                    ],
                },
            }
        }
    )
    logger = getLogger(__name__)


def modify_retire_campaign_rest(
        session: Session,
        domain: str,
        flexera_id: str = '',
        group_id: str = '',
) -> str:
    global logger
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
        logger.exception(f'HTTP ERROR: {http_error}')
    except Exception as exc_campaign_rest:
        logger.exception(f'Exception: {exc_campaign_rest}')


def create_retire_campaign_soap(
        session: Session,
        domain: str,
        flexera_id: str = '',
) -> xsd.CompoundValue:
    global logger
    url: str = f'{domain}/esd/ws/integration.asmx'
    wsdl: Optional[str] = None
    try:
        resp_wsdl: Response = session.get(url=f'{url}?WSDL')
        resp_wsdl.raise_for_status()
        wsdl: str = resp_wsdl.text
        logger.debug(f'WSDL: {wsdl}')
    except HTTPError as http_error_wsdl:
        msg: str = f'''WSDL ERROR: {http_error_wsdl}:
        STATUS: {http_error_wsdl.response.status_code}
        HEADERS: {http_error_wsdl.request.headers}
        BODY: {http_error_wsdl.request.body}'''
        logger.debug(msg=msg)
        logger.exception(http_error_wsdl)
    except Exception as exc_wsdl:
        logger.exception(f'Error getting WSDL: type: {type(exc_wsdl)}: message: {exc_wsdl}')
        raise exc_wsdl

    try:
        client = Client(wsdl, transport=Transport(session=session))
        resp_campaign: xsd.CompoundValue = client.service.AddFlexeraIdForRetireCampaign(flexera_id)
        logger.debug(f'\n\nCAMPAIGN RESPONSE: {resp_campaign}\n\n')
        return resp_campaign
    except Exception as exc_campaign_rest:
        logger.exception(exc_campaign_rest)
        logger.error(f'{type(exc_campaign_rest)}')


def main(
        domain: str,
        username: str,
        password: str,
        flexera_id: str,
        group_id: str,
        proxies: Optional[dict] = None,
) -> list:
    global logger
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


def get_cli_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        '--proxies',
        type=str,
        required=False,
        help="JSON structure specifying 'http' and 'https' proxy URLs",
    )
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
        '--log_level',
        default=50,
        type=int,
        help='Log level: default is 50. Greater than 0 enables some logging.  10 or more is DEBUG.',
    )

    return parser.parse_args()


if __name__ == '__main__':
    global logger
    msg: str = '\n    EXECUTION: {stage} ******************************************************************************\n'
    args: Namespace = get_cli_args()
    configure_logging(args.log_level)

    proxies: Optional[dict] = None
    if proxies:
        try:
            proxies: dict = loads(args.proxies)
        except Exception as exc_json:
            logger.warning(f'    FAILURE PARSING PROXIES: {exc_json}: proxies provided: {proxies}')

    logger.critical(msg.format(stage='begin'))
    try:
        for result in main(
            domain=args.domain,
            username=args.username,
            password=args.password,
            flexera_id=args.flexera_id,
            group_id=args.group_id,
            proxies=proxies,
        ):
            try:
                logger.info(f'    RESULT: {result}')
            except Exception as exc:
                logger.error(f'    RESULT EXCEPTION: {exc}')
    except Exception as exc_loop:
        logger.error(f'    MAIN ERROR: {exc_loop}')
    logger.critical(msg.format(stage='end'))
