"""Command-line entry: query from a shell without starting the API.

    python -m satquery.cli "Is there a water body in this image?" \
        --image data/demo/optical_scene1.tif --scene-id demo_scene_01
    python -m satquery.cli --tools
"""
from __future__ import annotations

import argparse
import json

from .orchestrator import Orchestrator
from .registry import tools_summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="satquery")
    ap.add_argument("query", nargs="?", help="natural-language question")
    ap.add_argument("--image", action="append", default=[], help="raster path (repeatable)")
    ap.add_argument("--scene-id", default=None, help="frozen demo-scene id (kill switch)")
    ap.add_argument("--tools", action="store_true", help="list the tool registry and exit")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                    help="inference device (gpu-first default lives in the tool layer)")
    ap.add_argument("--json", action="store_true", help="emit full JSON response")
    args = ap.parse_args(argv)

    if args.tools:
        print(json.dumps(tools_summary(), indent=2))
        return 0
    if not args.query:
        ap.error("a query is required (or use --tools)")

    orch = Orchestrator()
    params = {"scene_id": args.scene_id} if args.scene_id else {}
    resp = orch.answer(args.query, image_paths=args.image or None, params=params)
    if args.json:
        print(resp.model_dump_json(indent=2))
    else:
        print(f"\nQ: {resp.query}")
        print(f"[{resp.task.value} -> {resp.tool}] status={resp.status} "
              f"trained={resp.trained} fallback={resp.fallback_used}")
        print(f"A: {resp.answer}\n")
        for w in resp.warnings:
            print(f"  ! [{w['severity']}] {w['step']}: {w['message']}")
        print(f"  trace: {len(resp.trace.events)} steps, query_id={resp.query_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
