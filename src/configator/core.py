"""Main module for Configator."""

from functools import partial
from importlib.metadata import version
from typing import Any, TypeVar

from onepassword.client import Client as OnePasswordClient
from onepassword.types import Item, ItemField, ItemOverview, VaultOverview
from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from structlog import get_logger

log = get_logger()

T = TypeVar("T", bound=BaseModel)


async def load_config(*, token: str, vault: str, item: str, schema: type[T]) -> T:
    """Return an initialized schema instance."""
    log.debug("loading configuration into schema '%s'", schema.__name__)

    client = await _get_client(token)

    vault_overview = await _get_vault_overview(client, vault)
    if vault_overview is None:
        raise RuntimeError(f"vault '{vault}' not found")

    item_overview = await _get_item_overview(client, vault_overview.id, item)
    if item_overview is None:
        raise RuntimeError(f"item '{item}' not found in vault {vault}")

    cfg_item = await client.items.get(vault_id=vault_overview.id, item_id=item_overview.id)

    return await _hydrate_model(schema, client, cfg_item)


def _field_matcher(field: ItemField, *, title: str, section_id: str | None = None) -> bool:
    """Return True if the given field matches the title and optional section ID."""
    normalized_title = _op_field_name_to_lower_snake_case(field.title)
    return normalized_title == title and (section_id is None or field.section_id == section_id)


async def _get_client(token: str) -> OnePasswordClient:
    """Initialize 1Password client."""
    pkg_name = __package__ or ""
    pkg_version = version(pkg_name)
    log.debug("instantiating 1Password client (%s-%s)", pkg_name, pkg_version)
    op_client = await OnePasswordClient.authenticate(
        auth=token,
        integration_name=pkg_name,
        integration_version=pkg_version,
    )
    log.debug("1Password client authenticated")
    return op_client


async def _get_item_overview(
    op_client: OnePasswordClient, vault_id: str, item_name: str
) -> ItemOverview | None:
    """Retrieve item overview."""
    log.debug("retrieving item '%s' from vault '%s'", item_name, vault_id)
    available_items = await op_client.items.list(vault_id=vault_id)
    for item in available_items:
        if item.title == item_name:
            return item
    log.warning("item '%s' not found in vault '%s'", item_name, vault_id)
    return None


def _get_sections(item: Item) -> dict[str, str]:
    """Return mapping of section titles to IDs."""
    return {s.title.lower(): s.id for s in item.sections if s.title}


async def _get_vault_overview(
    op_client: OnePasswordClient, vault_name: str
) -> VaultOverview | None:
    """Retrieve vault overview."""
    log.debug("retrieving vault '%s'", vault_name)
    available_vaults = await op_client.vaults.list()
    for vault in available_vaults:
        if vault.title == vault_name:
            return vault
    log.warning("vault '%s' not found", vault_name)
    return None


async def _hydrate_model(
    schema: type[T], op_client: OnePasswordClient, item: Item, section_id: str | None = None
) -> T:
    """Hydrate Pydantic model from 1Password item."""
    log.debug("hydrating model '%s'", schema.__name__)
    dry_model = schema.model_fields
    wet_model: dict[str, Any] = {}
    wet_fields = item.fields
    for key in dry_model:
        log.debug("hydrating field '%s'", key)
        cls = dry_model[key].annotation
        if cls is None:
            log.warning("no annotation for field '%s'; skipping", key)
            continue

        if issubclass(cls, BaseModel):
            sections = _get_sections(item)
            wet_model[key] = await _hydrate_model(cls, op_client, item, sections[key.lower()])
        else:
            matcher = partial(_field_matcher, title=key.lower(), section_id=section_id)
            try:
                str_val = await _resolve_op_link(
                    op_client, next(filter(matcher, wet_fields)).value
                )
                wet_model[key] = _parse_bool(str_val) if issubclass(cls, bool) else cls(str_val)
            except StopIteration as stop:
                # Field not found, use default value if available
                if dry_model[key].default is PydanticUndefined:
                    raise stop
                log.debug("using default value for field '%s'", key)
                wet_model[key] = dry_model[key].default

    return schema(**wet_model)


def _op_field_name_to_lower_snake_case(name: str) -> str:
    """Convert 1Password field name to lower_snake_case."""
    return name.replace("-", "_").lower()


def _parse_bool(str_val: str) -> bool:
    """Parse boolean value from string."""
    truthy = {"true", "1", "yes", "on"}
    trumpy = {"false", "0", "no", "off"}
    val_lower = str_val.strip().lower()
    if val_lower in truthy:
        return True
    elif val_lower in trumpy:
        return False
    else:
        raise ValueError(f"cannot parse '{str_val}' as boolean")


async def _resolve_op_link(op_client: OnePasswordClient, link: str) -> str:
    """Resolve op:// reference to its actual value."""
    # This counter is used to guard against circular op:// references
    moria_level = 0
    while link.startswith("op://"):
        link = await op_client.secrets.resolve(link)
        moria_level += 1
        if moria_level > 9:
            log.error("too many nested op:// references when resolving '%s'", link)
            raise RuntimeError("the dwarves delved too greedily and too deep")
    return link
