from main import create_app
from tests.unit.test_logging_middleware import FakeLogger


def test_create_app_configures_logger():
    logger = FakeLogger()

    app = create_app(logger=logger)

    assert app.state.logger is logger
