from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.tag_registry"


# v0.1: governance-first, minimal schema.
# - tags: central registry (key -> record)
# - assignments: subject -> list[tag_key]
# - ha_label_map: tag_key -> ha_label_id (for materialized, confirmed tags)
# - user_aliases: user.* tag_key -> ha_label_id (read-only import of existing HA labels)


@dataclass
class SyncReport:
    imported_user_aliases: int = 0
    created_labels: int = 0
    updated_subjects: int = 0
    skipped_pending: int = 0
    errors: list[str] | None = None


def _get_store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    store = global_data.get("tag_registry_store")
    if store is None:
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        global_data["tag_registry_store"] = store
    return store


async def _load(hass: HomeAssistant) -> dict[str, Any]:
    data = await _get_store(hass).async_load() or {}
    data.setdefault("tags", {})
    data.setdefault("assignments", {})
    data.setdefault("ha_label_map", {})
    data.setdefault("user_aliases", {})
    return data


async def _save(hass: HomeAssistant, data: dict[str, Any]) -> None:
    await _get_store(hass).async_save(data)


def _tag_status(tag: dict[str, Any]) -> str:
    # statuses: confirmed|pending
    status = str(tag.get("status") or "pending")
    return status


def _is_user_tag(tag_key: str) -> bool:
    return tag_key.startswith("user.")


def _is_pending_materialization(tag_key: str, tag: dict[str, Any]) -> bool:
    # learned.* and candidate.* MUST NOT materialize unless confirmed.
    if _tag_status(tag) == "confirmed":
        return False
    return tag_key.startswith("learned.") or tag_key.startswith("candidate.")


async def async_upsert_tag(
    hass: HomeAssistant,
    tag_key: str,
    *,
    title: str | None = None,
    icon: str | None = None,
    color: str | None = None,
    status: str | None = None,
) -> None:
    data = await _load(hass)
    tags = data["tags"]
    rec = tags.get(tag_key) if isinstance(tags.get(tag_key), dict) else {}
    rec = dict(rec)
    if title is not None:
        rec["title"] = title
    if icon is not None:
        rec["icon"] = icon
    if color is not None:
        rec["color"] = color
    if status is not None:
        rec["status"] = status
    tags[tag_key] = rec
    await _save(hass, data)


async def async_confirm_tag(hass: HomeAssistant, tag_key: str) -> None:
    data = await _load(hass)
    tags = data["tags"]
    rec = tags.get(tag_key)
    if not isinstance(rec, dict):
        rec = {}
    rec = dict(rec)
    rec["status"] = "confirmed"
    tags[tag_key] = rec
    await _save(hass, data)


async def async_set_assignment(
    hass: HomeAssistant,
    subject: str,
    tag_keys: list[str],
) -> None:
    data = await _load(hass)
    data["assignments"][subject] = list(dict.fromkeys(tag_keys))
    await _save(hass, data)


def _label_id_from_obj(label: Any) -> Optional[str]:
    return (
        getattr(label, "label_id", None)
        or getattr(label, "id", None)
        or (label.get("label_id") if isinstance(label, dict) else None)
        or (label.get("id") if isinstance(label, dict) else None)
    )


def _label_name_from_obj(label: Any) -> Optional[str]:
    return (
        getattr(label, "name", None)
        or (label.get("name") if isinstance(label, dict) else None)
    )


async def _get_label_registry(hass: HomeAssistant) -> Any:
    try:
        from homeassistant.helpers import label_registry as lr  # type: ignore

        return lr.async_get(hass)
    except Exception:  # noqa: BLE001
        return None


async def _list_labels(reg: Any) -> list[Any]:
    if reg is None:
        return []

    # HA has shifted registry APIs over time; be defensive.
    for attr in ("async_list_labels", "async_list", "labels"):
        fn = getattr(reg, attr, None)
        if fn is None:
            continue
        try:
            res = fn() if callable(fn) else fn
            if isinstance(res, list):
                return res
            if isinstance(res, dict):
                return list(res.values())
        except Exception:  # noqa: BLE001
            continue
    return []


def _best_effort_apply_label_style_kwargs(tag: dict[str, Any]) -> dict[str, Any]:
    # If HA supports icon/color on labels, try to set them; otherwise ignored.
    out: dict[str, Any] = {}
    icon = tag.get("icon")
    color = tag.get("color")
    if isinstance(icon, str) and icon:
        out["icon"] = icon
    if isinstance(color, str) and color:
        out["color"] = color
    return out


async def _ensure_label(
    hass: HomeAssistant,
    reg: Any,
    *,
    name: str,
    icon: str | None,
    color: str | None,
) -> Optional[str]:
    if reg is None:
        return None

    # First try to find by name.
    existing = None
    for lbl in await _list_labels(reg):
        if _label_name_from_obj(lbl) == name:
            existing = lbl
            break

    if existing is not None:
        return _label_id_from_obj(existing)

    kwargs: dict[str, Any] = {}
    if icon:
        kwargs["icon"] = icon
    if color:
        kwargs["color"] = color

    # Create with best-effort signature compatibility.
    create = getattr(reg, "async_create", None)
    if not callable(create):
        return None

    try:
        lbl = create(name=name, **kwargs)
    except TypeError:
        try:
            lbl = create(name=name)
        except Exception:  # noqa: BLE001
            return None
    except Exception:  # noqa: BLE001
        return None

    return _label_id_from_obj(lbl)


async def _update_subject_labels(hass: HomeAssistant, subject: str, label_ids: set[str]) -> bool:
    """Apply label_ids to a subject. Returns True if update attempted/succeeded."""

    # Subject formats:
    # - entity:<entity_id>
    # - device:<device_id>
    # - area:<area_id>
    kind, _, ident = subject.partition(":")
    if not kind or not ident:
        return False

    try:
        if kind == "entity":
            from homeassistant.helpers import entity_registry as er  # type: ignore

            reg = er.async_get(hass)
            update = getattr(reg, "async_update_entity", None)
            if not callable(update):
                return False
            try:
                update(ident, labels=label_ids)
            except TypeError:
                # older HA might not support labels
                return False
            return True

        if kind == "device":
            from homeassistant.helpers import device_registry as dr  # type: ignore

            reg = dr.async_get(hass)
            update = getattr(reg, "async_update_device", None)
            if not callable(update):
                return False
            try:
                update(ident, labels=label_ids)
            except TypeError:
                return False
            return True

        if kind == "area":
            from homeassistant.helpers import area_registry as ar  # type: ignore

            reg = ar.async_get(hass)
            update = getattr(reg, "async_update_area", None)
            if not callable(update):
                return False
            try:
                update(ident, labels=label_ids)
            except TypeError:
                return False
            return True

    except Exception:  # noqa: BLE001
        return False

    return False


async def async_sync_labels_now(hass: HomeAssistant) -> SyncReport:
    """Sync Tag Registry -> HA labels + apply label assignments.

    Minimal v0.1 behavior:
    - Import existing HA labels as read-only user.* aliases.
    - Materialize *confirmed* non-user tags as HA labels (name == tag_key).
    - Apply labels to supported subjects via registries (entity/device/area).
    """

    report = SyncReport(errors=[])
    data = await _load(hass)

    reg = await _get_label_registry(hass)

    # 1) Import existing HA labels as read-only user.* aliases.
    try:
        labels = await _list_labels(reg)
        for lbl in labels:
            lid = _label_id_from_obj(lbl)
            name = _label_name_from_obj(lbl)
            if not lid or not name:
                continue
            user_key = f"user.{lid}"
            if user_key not in data["user_aliases"]:
                data["user_aliases"][user_key] = lid
                # store minimal mirror tag for UI/consistency
                data["tags"].setdefault(user_key, {"title": name, "status": "confirmed"})
                report.imported_user_aliases += 1
    except Exception as err:  # noqa: BLE001
        report.errors.append(f"label import failed: {err}")

    # 2) Ensure labels exist for confirmed tags (excluding user.*).
    for tag_key, tag in list(data["tags"].items()):
        if not isinstance(tag, dict):
            continue
        if _is_user_tag(tag_key):
            continue
        if _is_pending_materialization(tag_key, tag):
            report.skipped_pending += 1
            continue
        if _tag_status(tag) != "confirmed":
            # other pending tags are also not materialized
            report.skipped_pending += 1
            continue

        if tag_key in data["ha_label_map"]:
            continue

        icon = tag.get("icon") if isinstance(tag.get("icon"), str) else None
        color = tag.get("color") if isinstance(tag.get("color"), str) else None

        lid = await _ensure_label(hass, reg, name=tag_key, icon=icon, color=color)
        if lid:
            data["ha_label_map"][tag_key] = lid
            report.created_labels += 1

    # 3) Apply assignments to supported subjects.
    for subject, tag_keys in list(data["assignments"].items()):
        if not isinstance(subject, str):
            continue
        if not isinstance(tag_keys, list):
            continue

        label_ids: set[str] = set()
        for tk in tag_keys:
            if not isinstance(tk, str):
                continue
            # user.* are aliases and may be assigned, but read-only (we won't create them)
            if tk.startswith("user."):
                lid = data["user_aliases"].get(tk)
                if isinstance(lid, str) and lid:
                    label_ids.add(lid)
                continue

            # non-user tags: only apply if confirmed and materialized
            tag = data["tags"].get(tk)
            if not isinstance(tag, dict) or _tag_status(tag) != "confirmed":
                continue
            lid = data["ha_label_map"].get(tk)
            if isinstance(lid, str) and lid:
                label_ids.add(lid)

        if not label_ids:
            continue

        ok = await _update_subject_labels(hass, subject, label_ids)
        if ok:
            report.updated_subjects += 1

    await _save(hass, data)

    if report.errors == []:
        report.errors = None
    return report
