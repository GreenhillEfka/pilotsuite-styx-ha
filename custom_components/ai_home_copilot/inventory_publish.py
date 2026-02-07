from __future__ import annotations

import logging
from pathlib import Path
import shutil

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

from .inventory import async_generate_ha_overview
from .overview_store import OverviewState, async_get_overview_state, async_set_overview_state

_LOGGER = logging.getLogger(__name__)


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


async def async_publish_last_overview(hass: HomeAssistant) -> str:
    """Publish the last overview file to /config/www so it can be downloaded via /local.

    Privacy note: the file becomes available to anyone who can access your HA web UI.
    """

    st = await async_get_overview_state(hass)
    if not st.last_path:
        p = await async_generate_ha_overview(hass)
        st.last_path = str(p)

    src = Path(st.last_path)
    if not src.exists():
        p = await async_generate_ha_overview(hass)
        src = Path(p)
        st.last_path = str(p)

    # Publish under www/ai_home_copilot/
    www_dir = Path(hass.config.path("www")) / "ai_home_copilot"
    dst = www_dir / src.name

    await hass.async_add_executor_job(_copy, src, dst)

    st.last_published_path = str(dst)
    await async_set_overview_state(hass, st)

    url = f"/local/ai_home_copilot/{dst.name}"
    persistent_notification.async_create(
        hass,
        (
            "Overview published for download. "
            f"Open this URL in your browser: {url}"
        ),
        title="AI Home CoPilot overview download",
        notification_id="ai_home_copilot_overview_download",
    )

    _LOGGER.info("Published overview report to %s (url=%s)", dst, url)
    return url
