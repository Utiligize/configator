"""Integration test for Configator load_config.

Relies on a real token and a properly set up 1Password item.
"""

from os import getenv

from pydantic import BaseModel
from pytest import mark

from configator.core import load_config


@mark.asyncio
async def test_load_config():
    class AppConfig(BaseModel):
        """App configuration schema."""

        a_string: str
        an_integer: int
        a_reference: str


    class EnvConfig(BaseModel):
        """Environment configuration schema."""

        debug: bool


    class TestConfig(BaseModel):
        """Full test configuration schema."""

        APP: AppConfig
        ENV: EnvConfig
        NO_SECTION: str = "overridden_default_value"
        defval: str = "default_value"

    token = getenv("OP_TOKEN")
    vault = "REPO assetlife-api"
    item = "configator-test"

    expected_config = TestConfig(
        APP=AppConfig(
            a_string="foo",
            an_integer=42,
            a_reference="mixpanel",
        ),
        ENV=EnvConfig(
            debug=False,
        ),
        NO_SECTION="no_kings",
        defval="default_value",
    )

    actual_config: TestConfig = await load_config(**{
        "schema": TestConfig,
        "token": token,
        "vault": vault,
        "item": item,
    })

    assert actual_config == expected_config
