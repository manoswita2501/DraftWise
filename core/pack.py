import json
from datetime import datetime, timezone
from typing import Any, Dict


PACK_VERSION = 1


def build_pack(config: Dict[str, Any], artifacts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a JSON-serializable project pack.
    Assumes artifacts only contain JSON-safe types (dict/list/str/int/float/bool/None).
    """
    return {
        "pack_version": PACK_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "app": "DraftWise",
        "config": config,
        "artifacts": artifacts,
    }


def dumps_pack(pack: Dict[str, Any]) -> str:
    return json.dumps(pack, ensure_ascii=False, indent=2)


def loads_pack(s: str) -> Dict[str, Any]:
    return json.loads(s)


def validate_pack(pack: Dict[str, Any]) -> None:
    if not isinstance(pack, dict):
        raise ValueError("Pack is not a JSON object.")
    if pack.get("app") != "DraftWise":
        raise ValueError("Not a DraftWise pack.")
    if "config" not in pack or "artifacts" not in pack:
        raise ValueError("Pack missing required keys: config/artifacts.")
    if not isinstance(pack["config"], dict) or not isinstance(pack["artifacts"], dict):
        raise ValueError("Pack config/artifacts must be objects.")
    # Version check (for future migrations)
    v = pack.get("pack_version")
    if v is None or not isinstance(v, int) or v < 1:
        raise ValueError("Invalid pack_version.")