# Tag System API v1
"""
REST API Endpoints für Tag System v0.2

Decision Matrix P1 Implementierung:
- HA-Labels materialisieren: nur ausgewählte Facetten (role.*, state.*)
- Learned Tags: NIE automatisch (explizite Bestätigung nötig)
- Alle HA-Label-Typen: entity, device, area, automation, scene, script, helper
"""

from copilot_core.tags import (
    TagRegistry,
    TagFacet,
    SubjectType,
    create_tag_service,
)
from aiohttp import web
import json


def setup_tag_api(app: web.Application, registry: TagRegistry):
    """Registriert die Tag API Endpoints."""
    
    service = create_tag_service(registry)
    
    # === Tag Endpoints ===
    
    async def api_create_tag(request: web.Request) -> web.Response:
        """POST /api/v1/tags — Tag erstellen."""
        data = await request.json()
        result = await service["create_tag"](
            tag_id=data["id"],
            facet=data["facet"],
            display_de=data.get("display_de"),
            display_en=data.get("display_en"),
        )
        return web.json_response(result, status=201)
    
    async def api_suggest_tag(request: web.Request) -> web.Response:
        """POST /api/v1/tags/suggest — Learned Tag vorschlagen."""
        data = await request.json()
        result = await service["suggest_tag"](
            facet=data["facet"],
            key=data["key"],
            namespace=data.get("namespace", "sys"),
            display_de=data.get("display_de"),
        )
        return web.json_response(result, status=201)
    
    async def api_confirm_tag(request: web.Request) -> web.Response:
        """POST /api/v1/tags/{tag_id}/confirm — Learned Tag bestätigen."""
        tag_id = request.match_info["tag_id"]
        result = await service["confirm_tag"](tag_id)
        return web.json_response(result)
    
    async def api_list_tags(request: web.Request) -> web.Response:
        """GET /api/v1/tags — Tags auflisten."""
        facet = request.query.get("facet")
        result = await service["list_tags"](facet=facet)
        return web.json_response(result)
    
    async def api_get_tag(request: web.Request) -> web.Response:
        """GET /api/v1/tags/{tag_id} — Tag details."""
        tag_id = request.match_info["tag_id"]
        tag = registry.get_tag(tag_id)
        if not tag:
            return web.json_response({"error": "Tag not found"}, status=404)
        return web.json_response({
            "id": tag.id,
            "facet": tag.facet.value,
            "display_de": tag.metadata.display_de,
            "display_en": tag.metadata.display_en,
            "is_learned": tag.is_learned,
            "is_materialized": tag.is_materialized,
            "provenance": tag.provenance,
            "should_materialize": tag.should_materialize(),
        })
    
    async def api_delete_tag(request: web.Request) -> web.Response:
        """DELETE /api/v1/tags/{tag_id} — Tag löschen."""
        tag_id = request.match_info["tag_id"]
        if tag_id in registry._tags:
            del registry._tags[tag_id]
            return web.json_response({"status": "deleted", "tag_id": tag_id})
        return web.json_response({"error": "Tag not found"}, status=404)
    
    # === Subject Endpoints ===
    
    async def api_register_subject(request: web.Request) -> web.Response:
        """POST /api/v1/subjects — Subject registrieren."""
        data = await request.json()
        result = await service["register_subject"](
            ha_id=data["ha_id"],
            ha_type=data["ha_type"],
            name=data.get("name"),
            domain=data.get("domain"),
            unique_id=data.get("unique_id"),
            device_id=data.get("device_id"),
            area_id=data.get("area_id"),
        )
        return web.json_response(result, status=201)
    
    async def api_list_subjects(request: web.Request) -> web.Response:
        """GET /api/v1/subjects — Subjects auflisten."""
        ha_type = request.query.get("type")
        subjects = list(registry._subjects.values())
        if ha_type:
            subjects = [s for s in subjects if s.ha_type.value == ha_type]
        return web.json_response({
            "subjects": [
                {
                    "id": s.canonical_id,
                    "ha_id": s.ha_id,
                    "ha_type": s.ha_type.value,
                    "name": s.name,
                    "domain": s.domain,
                }
                for s in subjects
            ]
        })
    
    async def api_get_subject(request: web.Request) -> web.Response:
        """GET /api/v1/subjects/{subject_id} — Subject details."""
        subject_id = request.match_info["subject_id"]
        subject = registry.get_subject(subject_id)
        if not subject:
            return web.json_response({"error": "Subject not found"}, status=404)
        return web.json_response({
            "ha_id": subject.ha_id,
            "ha_type": subject.ha_type.value,
            "canonical_id": subject.canonical_id,
            "unique_id": subject.unique_id,
            "device_id": subject.device_id,
            "area_id": subject.area_id,
            "name": subject.name,
            "domain": subject.domain,
            "tags": [
                t.id for t in registry.get_subject_tags(subject.canonical_id)
            ],
        })
    
    # === Assignment Endpoints ===
    
    async def api_assign_tag(request: web.Request) -> web.Response:
        """POST /api/v1/assignments — Tag zu Subject zuweisen."""
        data = await request.json()
        result = await service["assign_tag"](
            tag_id=data["tag_id"],
            subject_id=data["subject_id"],
        )
        if result.get("status") == "assigned":
            return web.json_response(result, status=201)
        return web.json_response(result, status=400)
    
    async def api_list_assignments(request: web.Request) -> web.Response:
        """GET /api/v1/assignments — Alle Zuweisungen."""
        tag_id = request.query.get("tag_id")
        subject_id = request.query.get("subject_id")
        
        assignments = registry._assignments
        if tag_id:
            assignments = [a for a in assignments if a.tag_id == tag_id]
        if subject_id:
            assignments = [a for a in assignments if a.subject_canonical_id == subject_id]
        
        return web.json_response({
            "assignments": [
                {
                    "tag_id": a.tag_id,
                    "subject_id": a.subject_canonical_id,
                    "assigned_at": a.assigned_at,
                    "assigned_by": a.assigned_by,
                }
                for a in assignments
            ]
        })
    
    async def api_get_subject_tags(request: web.Request) -> web.Response:
        """GET /api/v1/subjects/{subject_id}/tags — Tags für Subject."""
        subject_id = request.match_info["subject_id"]
        tags = registry.get_subject_tags(subject_id)
        return web.json_response({
            "tags": [
                {
                    "id": t.id,
                    "facet": t.facet.value,
                    "is_learned": t.is_learned,
                }
                for t in tags
            ]
        })
    
    async def api_get_tag_subjects(request: web.Request) -> web.Response:
        """GET /api/v1/tags/{tag_id}/subjects — Subjects für Tag."""
        tag_id = request.match_info["tag_id"]
        subjects = registry.get_tag_subjects(tag_id)
        return web.json_response({
            "subjects": [
                {
                    "id": s.canonical_id,
                    "ha_type": s.ha_type.value,
                    "name": s.name,
                }
                for s in subjects
            ]
        })
    
    async def api_delete_assignment(request: web.Request) -> web.Response:
        """DELETE /api/v1/assignments — Zuweisung entfernen."""
        data = await request.json()
        tag_id = data.get("tag_id")
        subject_id = data.get("subject_id")
        
        original_count = len(registry._assignments)
        registry._assignments = [
            a for a in registry._assignments
            if not (a.tag_id == tag_id and a.subject_canonical_id == subject_id)
        ]
        
        if len(registry._assignments) < original_count:
            return web.json_response({
                "status": "deleted",
                "tag_id": tag_id,
                "subject_id": subject_id,
            })
        return web.json_response({"error": "Assignment not found"}, status=404)
    
    # === Habitus Zones ===
    
    async def api_create_zone(request: web.Request) -> web.Response:
        """POST /api/v1/zones — Habitus-Zone erstellen."""
        data = await request.json()
        zone = registry.create_zone(
            zone_id=data["id"],
            name=data["name"],
            policy_ids=data.get("policy_ids", []),
        )
        return web.json_response({
            "status": "created",
            "zone_id": zone.id,
        }, status=201)
    
    async def api_list_zones(request: web.Request) -> web.Response:
        """GET /api/v1/zones — Zonen auflisten."""
        return web.json_response({
            "zones": [
                {
                    "id": z.id,
                    "name": z.name,
                    "policy_ids": z.policy_ids,
                    "member_count": len(z.member_subject_ids),
                    "is_active": z.is_active,
                }
                for z in registry._zones.values()
            ]
        })
    
    async def api_add_to_zone(request: web.Request) -> web.Response:
        """POST /api/v1/zones/{zone_id}/members — Subject zu Zone hinzufügen."""
        zone_id = request.match_info["zone_id"]
        data = await request.json()
        result = registry.add_to_zone(zone_id, data["subject_id"])
        if result:
            return web.json_response({
                "status": "added",
                "zone_id": zone_id,
                "subject_id": data["subject_id"],
            })
        return web.json_response({"error": "Zone or subject not found"}, status=404)
    
    # === HA Label Export ===
    
    async def api_export_labels(request: web.Request) -> web.Response:
        """GET /api/v1/labels/export — Export für HA Labels Sync."""
        result = await service["export_labels"]()
        return web.json_response(result)
    
    # === Registry Routes ===
    
    app.router.add_post("/api/v1/tags", api_create_tag)
    app.router.add_post("/api/v1/tags/suggest", api_suggest_tag)
    app.router.add_post("/api/v1/tags/{tag_id}/confirm", api_confirm_tag)
    app.router.add_get("/api/v1/tags", api_list_tags)
    app.router.add_get("/api/v1/tags/{tag_id}", api_get_tag)
    app.router.add_delete("/api/v1/tags/{tag_id}", api_delete_tag)
    
    app.router.add_post("/api/v1/subjects", api_register_subject)
    app.router.add_get("/api/v1/subjects", api_list_subjects)
    app.router.add_get("/api/v1/subjects/{subject_id}", api_get_subject)
    app.router.add_get("/api/v1/subjects/{subject_id}/tags", api_get_subject_tags)
    
    app.router.add_post("/api/v1/assignments", api_assign_tag)
    app.router.add_get("/api/v1/assignments", api_list_assignments)
    app.router.add_delete("/api/v1/assignments", api_delete_assignment)
    app.router.add_get("/api/v1/tags/{tag_id}/subjects", api_get_tag_subjects)
    
    app.router.add_post("/api/v1/zones", api_create_zone)
    app.router.add_get("/api/v1/zones", api_list_zones)
    app.router.add_post("/api/v1/zones/{zone_id}/members", api_add_to_zone)
    
    app.router.add_get("/api/v1/labels/export", api_export_labels)
