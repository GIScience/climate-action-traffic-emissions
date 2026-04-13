import logging.config

from climatoology.app.plugin import start_plugin

from traffic_emissions.core.operator_worker import Operator
from traffic_emissions.core.settings import Settings

log = logging.getLogger(__name__)


def init_plugin() -> int:
    settings = Settings()
    operator = Operator(settings)

    log.info('Starting Plugin')
    return start_plugin(operator=operator)


if __name__ == '__main__':
    exit_code = init_plugin()
    log.info(f'Plugin exited with code {exit_code}')
