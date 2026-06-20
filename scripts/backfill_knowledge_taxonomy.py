from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.services.knowledge_taxonomy_backfill import KnowledgeTaxonomyBackfillService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="补全历史知识文档的类别和结构化标签")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan-file", help="生成补全计划 JSON，不修改数据库")
    group.add_argument("--apply-plan", help="应用已有计划 JSON，不再次调用 AI")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 条文档，用于小范围验证")
    parser.add_argument("--batch-size", type=int, default=5, help="每次提交给 DeepSeek 的文档数量")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        service = KnowledgeTaxonomyBackfillService(db)
        if args.apply_plan:
            plan_path = Path(args.apply_plan)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            result = service.apply_plan(plan)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        plan = service.build_plan(limit=args.limit, batch_size=args.batch_size)
        plan_path = Path(args.plan_file)
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"补全计划已生成：{plan_path.resolve()}")
        print(json.dumps({"document_count": plan["document_count"], "candidate_count": plan["candidate_count"]}, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
