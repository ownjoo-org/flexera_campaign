from argparse import ArgumentParser, Namespace
from json import dumps, loads
from logging import DEBUG, NOTSET, WARNING, getLogger, CRITICAL, ERROR, INFO, Logger
from logging.config import dictConfig
from typing import Optional

from requests import HTTPError, Response, Session
from requests_ntlm import HttpNtlmAuth
from urllib3 import disable_warnings
from urllib3.connection import HTTPConnection
from urllib3.exceptions import InsecureRequestWarning
from zeep import Client, Transport, xsd

global logger


disable_warnings(InsecureRequestWarning)


def configure_logger(log_level: int = WARNING) -> None:
    global logger
    HTTPConnection.debuglevel = DEBUG if log_level <= DEBUG else NOTSET  # 0 for off, >0 for on
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
    url: str = f'{domain}/esd/ws/integration.asmx'

    try:
        client = Client(wsdl=f'{url}?WSDL', transport=Transport(session=session))
        resp_campaign: xsd.CompoundValue = client.service.AddFlexeraIdForRetireCampaign(flexera_id)
        logger.debug(f'\n\nCAMPAIGN RESPONSE: {resp_campaign}\n\n')
        return resp_campaign
    except Exception as exc_campaign_rest:
        logger.exception(exc_campaign_rest)


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
        default=50,  # ERROR
        type=int,
        help=f'Log level: default is {ERROR}.\nOptions:\n'
             f'    CRITICAL: {CRITICAL}.\n'
             f'    ERROR: {ERROR}.\n'
             f'    WARNING: {WARNING}.\n'
             f'    INFO: {INFO}.\n'
             f'    DEBUG: {DEBUG}.\n'
             f'    OFF: {NOTSET}.',
    )

    return parser.parse_args()


if __name__ == '__main__':
    args: Namespace = get_cli_args()
    configure_logger(args.log_level)

    proxies: Optional[dict] = args.proxies or None
    if proxies:
        try:
            proxies: dict = loads(args.proxies)
        except Exception as exc_json:
            logger.warning(f'FAILURE PARSING PROXIES: {exc_json}: proxies provided: {proxies}')

    msg: str = '\n    EXECUTION: {stage} ****************************************************************************\n'
    logger.debug(msg.format(stage='begin'))
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
                print(f'    MAIN: RESULT: {result}')
            except Exception as exc:
                logger.error(f'    MAIN: RESULT: ERROR: {exc}')
                raise
    except Exception as exc_loop:
        logger.error(f'    MAIN: ERROR: {exc_loop}')
    logger.debug(msg.format(stage='end'))
