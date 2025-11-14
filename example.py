"""Example Configator usage."""

from asyncio import run
from os import getenv

from pydantic import BaseModel
from sorcery import dict_of

from configator import load_config


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


async def configator_example(token: str, vault: str, item: str) -> None:
    """Example: Access config with Pydantic models."""
    actually_config: TestConfig = await load_config(**{
        "schema": TestConfig,
        "token": token,
        "vault": vault,
        "item": item,
    })
    print(f"{actually_config=}")
    print(f"{expected_config=}")
    assert actually_config == expected_config
    assert actually_config.APP.a_string == "foo"


if __name__ == "__main__":
    token = getenv("OP_TOKEN")
    vault = "REPO assetlife-api"
    item = "configator-test"
    run(configator_example(**dict_of(token, vault, item)))
