"""Configuración de pytest. Mock de dependencias pesadas (playwright)."""
import sys
from unittest.mock import MagicMock

# Mock playwright antes de que main.py lo importe
playwright_mock = MagicMock()
sys.modules["playwright"] = playwright_mock
sys.modules["playwright.async_api"] = playwright_mock

# Mock captcha_solver
captcha_mock = MagicMock()
captcha_mock.get_balance = MagicMock(return_value=-1)
sys.modules["captcha_solver"] = captcha_mock
