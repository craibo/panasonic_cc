"""Platform for the Panasonic Comfort Cloud."""
import logging
from typing import Dict

import asyncio

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_USERNAME, CONF_PASSWORD)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_FORCE_OUTSIDE_SENSOR,
    DEFAULT_FORCE_OUTSIDE_SENSOR,
    CONF_ENABLE_DAILY_ENERGY_SENSOR,
    DEFAULT_ENABLE_DAILY_ENERGY_SENSOR,
    PANASONIC_DEVICES,
    COMPONENT_TYPES)

from .panasonic import PanasonicApiDevice

_LOGGER = logging.getLogger(__name__)

DOMAIN = "panasonic_cc"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_FORCE_OUTSIDE_SENSOR, default=DEFAULT_FORCE_OUTSIDE_SENSOR): cv.boolean,  # noqa: E501
                vol.Optional(CONF_ENABLE_DAILY_ENERGY_SENSOR, default=DEFAULT_ENABLE_DAILY_ENERGY_SENSOR): cv.boolean,
                # noqa: E501
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    pass


async def async_setup(hass: HomeAssistant, config: Dict) -> bool:
    """Set up the Garo Wallbox component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Establish connection with Comfort Cloud."""
    from . import pcomfortcloud

    conf = entry.data
    if PANASONIC_DEVICES not in hass.data:
        hass.data[PANASONIC_DEVICES] = []

    username = conf[CONF_USERNAME]
    password = conf[CONF_PASSWORD]
    force_outside_sensor = entry.options.get(CONF_FORCE_OUTSIDE_SENSOR, DEFAULT_FORCE_OUTSIDE_SENSOR)
    if CONF_FORCE_OUTSIDE_SENSOR in conf:
        force_outside_sensor = conf[CONF_FORCE_OUTSIDE_SENSOR]
    enable_daily_energy_sensor = entry.options.get(CONF_ENABLE_DAILY_ENERGY_SENSOR, DEFAULT_ENABLE_DAILY_ENERGY_SENSOR)

    client = async_get_clientsession(hass)
    api = pcomfortcloud.ApiClient(username, password, client)
    await api.start_session()

    devices = api.get_devices()

    for device in devices:
        try:
            api_device = PanasonicApiDevice(hass, api, device, force_outside_sensor, enable_daily_energy_sensor)
            await api_device.update()
            if enable_daily_energy_sensor:
                await api_device.update_energy()
            hass.data[PANASONIC_DEVICES].append(api_device)
        except Exception as e:
            _LOGGER.warning(f"Failed to setup device: {device['name']} ({e})")

    if hass.data[PANASONIC_DEVICES]:
        for component in COMPONENT_TYPES:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, component)
            )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    tasks = []
    for component in COMPONENT_TYPES:
        tasks.append(
            hass.async_create_task(
                hass.config_entries.async_forward_entry_unload(config_entry, component)  # noqa: E501
            )
        )

    await asyncio.wait(tasks)
    hass.data.pop(PANASONIC_DEVICES)
    return True
