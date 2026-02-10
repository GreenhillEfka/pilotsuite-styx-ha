"""API v1 blueprint for the Tag System registry and assignments stubs."""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, jsonify, request

from copilot_core.api.security import require_token
from copilot_core.tagging.registry import TagRegistry, TagRegistryError

bp = Blueprint("tag_system", __name__, url_prefix="/api/v1/tag-system")

DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "tagging"
_REGISTRY: TagRegistry | None = None


def _load_registry() -> TagRegistry:
    global _REGISTRY  # noqa: PLW0603 - module-level cache is intentional
    if _REGISTRY is not None:
        return _REGISTRY

    tags_file = DATA_ROOT / "tags.yaml"
    try:
        _REGISTRY = TagRegistry.from_file(tags_file)
    except FileNotFoundError as err:  # pragma: no cover - catastrophic misconfig
        raise RuntimeError(f"Tag registry file missing: {tags_file}") from err
    except TagRegistryError as err:
        raise RuntimeError(f"Invalid tag registry payload: {err}") from err

    return _REGISTRY


def _preferred(value_getter, fallbacks: list[str]) -> str | None:
    for lang in fallbacks:
        value = value_getter(lang)
        if value:
            return value
    return None


def _serialize_tag(tag, lang: str, include_translations: bool) -> dict:
    name = _preferred(tag.display.get_name, [lang, "de", "en"])
    description = _preferred(tag.display.get_description, [lang, "de", "en"])

    display_payload: dict[str, object] = {
        "lang": lang,
        "name": name,
        "description": description,
    }

    if include_translations:
        display_payload["names"] = dict(tag.display.names)
        display_payload["descriptions"] = dict(tag.display.descriptions)

    return {
        "id": tag.id,
        "namespace": tag.namespace,
        "facet": tag.facet,
        "key": tag.key,
        "type": tag.type,
        "icon": tag.icon,
        "color": tag.color,
        "display": display_payload,
        "governance": {
            "visibility": tag.governance.visibility,
            "source": tag.governance.source,
            "confidence": tag.governance.confidence,
            "pii_risk": tag.governance.pii_risk,
            "retention": tag.governance.retention,
        },
        "ha": {
            "materialize_as_label": tag.ha.materialize_as_label,
            "label_slug": tag.ha.label_slug,
            "materializes_in_ha": tag.materializes_in_ha,
        },
    }


@bp.route("/tags", methods=["GET"])
def list_tags():
    if not require_token(request):
        return jsonify({"error": "unauthorized"}), 401

    registry = _load_registry()
    lang = (request.args.get("lang") or "de").lower()
    include_translations = (request.args.get("translations") or "").lower() in {
        "true",
        "1",
        "yes",
    }

    tags = [_serialize_tag(tag, lang, include_translations) for tag in registry.all()]

    return jsonify(
        {
            "ok": True,
            "schema_version": registry.schema_version,
            "count": len(tags),
            "reserved_namespaces": registry.reserved_namespaces(),
            "tags": tags,
        }
    )


@bp.route("/tags/<path:tag_id>", methods=["GET"])
def get_tag(tag_id: str):
    if not require_token(request):
        return jsonify({"error": "unauthorized"}), 401

    registry = _load_registry()
    tag = registry.get(tag_id)
    if not tag:
        return jsonify({"error": "tag_not_found", "tag_id": tag_id}), 404

    lang = (request.args.get("lang") or "de").lower()
    include_translations = (request.args.get("translations") or "").lower() in {
        "true",
        "1",
        "yes",
    }

    return jsonify(
        {
            "ok": True,
            "schema_version": registry.schema_version,
            "tag": _serialize_tag(tag, lang, include_translations),
        }
    )


@bp.route("/assignments", methods=["GET", "POST"])
def assignments_stub():
    if not require_token(request):
        return jsonify({"error": "unauthorized"}), 401

    if request.method == "GET":
        return jsonify(
            {
                "ok": True,
                "status": "stub",
                "assignments": [],
                "count": 0,
                "message": "Assignments API will sync HA label materialization soon.",
            }
        )

    return jsonify(
        {
            "error": "not_implemented",
            "status": "stub",
            "detail": "Assignments create/update flow is not available yet.",
        }
    ), 501
