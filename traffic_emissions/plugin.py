import logging.config
from typing import NoReturn

from climatoology.app.plugin import start_plugin

from traffic_emissions.core.operator_worker import Operator
from traffic_emissions.core.settings import Settings

log = logging.getLogger(__name__)


def start() -> NoReturn:
    settings = Settings()
    operator = Operator(settings)

    log.info('Starting Plugin')
    start_plugin(operator=operator)


if __name__ == '__main__':
    start()
