import logging.config
from pathlib import Path

from climatoology.app.plugin import start_plugin

from traffic_emissions.core.operator_worker import Operator
from traffic_emissions.core.settings import Settings

log = logging.getLogger(__name__)


def init_plugin() -> int:
    settings = Settings()

    key_path = Path(__file__).parent.parent / '.earth_engine_key.json'
    with open(key_path, 'w') as file:
        file.write(settings.google_earth_engine_key)

    settings.google_earth_engine_key = str(key_path)

    operator = Operator(settings)

    log.info('Starting Plugin')
    return start_plugin(operator=operator)


if __name__ == '__main__':
    exit_code = init_plugin()
    log.info(f'Plugin exited with code {exit_code}')
