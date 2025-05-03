import pytest
from aiogram import Bot
from aiogram import Dispatcher

@pytest.fixture
def bot():
    return Bot(token="123:TEST_TOKEN")

@pytest.fixture
def dp(bot):
    return Dispatcher()
