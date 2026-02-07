from __future__ import annotations

import logging
from pathlib import Path
import shutil

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


_BLUEPRINTS = [
    (
        Path(__file__).resolve().parent
        / "blueprints"
        / "automation"
        / "ai_home_copilot"
        / "a_to_b_safe.yaml",
        Path("blueprints") / "automation" / "ai_home_copilot" / "a_to_b_safe.yaml",
    )
]


async def async_install_blueprints(hass: HomeAssistant) -> None:
    """Ensure shipped blueprints are installed into the user's blueprint directory.

    This does NOT create automations. It only makes the blueprint available in the UI.
    """

    def _install_one(src: Path, dst_rel: Path) -> None:
        dst = Path(hass.config.path(str(dst_rel)))
        if dst.exists():
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    for src, dst_rel in _BLUEPRINTS:
        try:
            await hass.async_add_executor_job(_install_one, src, dst_rel)
        except FileNotFoundError:
            _LOGGER.warning("Blueprint source missing: %s", src)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to install blueprint %s", dst_rel)
        else:
            _LOGGER.info("Installed blueprint: %s", dst_rel)
