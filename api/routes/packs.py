"""
Packs Routes - Cape Pack listing and management.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.deps import get_registry
from api.schemas import (
    PackResponse,
    PackDetailResponse,
    PacksResponse,
    CapeResponse,
)

router = APIRouter(prefix="/api/packs", tags=["packs"])


@router.get("", response_model=PacksResponse)
def list_packs():
    """
    List all available Cape Packs.

    Returns pack metadata including name, description, and cape count.
    """
    registry = get_registry()
    packs_data = registry.get_packs()

    packs = []
    total_capes = 0

    for pack in packs_data:
        cape_ids = pack.get("capes", [])
        # Get actual capes in this pack
        pack_capes = registry.filter_by_pack(pack["name"])
        cape_count = len(pack_capes)
        total_capes += cape_count

        packs.append(PackResponse(
            name=pack["name"],
            display_name=pack.get("display_name", pack["name"]),
            description=pack.get("description", ""),
            version=pack.get("version", "1.0.0"),
            icon=pack.get("icon"),
            color=pack.get("color"),
            target_users=pack.get("target_users", []),
            scenarios=pack.get("scenarios", []),
            cape_ids=[c.id for c in pack_capes],
            cape_count=cape_count,
        ))

    return PacksResponse(
        packs=packs,
        total_packs=len(packs),
        total_capes_in_packs=total_capes,
    )


@router.get("/{pack_name}", response_model=PackDetailResponse)
def get_pack(pack_name: str):
    """
    Get detailed information about a specific Pack.

    Includes all capes in the pack.
    """
    registry = get_registry()
    pack_data = registry.get_pack(pack_name)

    if not pack_data:
        raise HTTPException(status_code=404, detail=f"Pack not found: {pack_name}")

    metadata = pack_data["metadata"]
    capes = pack_data["capes"]

    return PackDetailResponse(
        name=pack_name,
        display_name=metadata.get("display_name", pack_name),
        description=metadata.get("description", ""),
        version=metadata.get("version", "1.0.0"),
        icon=metadata.get("icon"),
        color=metadata.get("color"),
        target_users=metadata.get("target_users", []),
        scenarios=metadata.get("scenarios", []),
        cape_ids=[c.id for c in capes],
        cape_count=len(capes),
        capes=[CapeResponse.from_cape(c) for c in capes],
    )


@router.get("/{pack_name}/capes", response_model=List[CapeResponse])
def get_pack_capes(pack_name: str):
    """
    Get all capes in a specific Pack.
    """
    registry = get_registry()
    pack_data = registry.get_pack(pack_name)

    if not pack_data:
        raise HTTPException(status_code=404, detail=f"Pack not found: {pack_name}")

    capes = pack_data["capes"]
    return [CapeResponse.from_cape(c) for c in capes]
