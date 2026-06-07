from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SkillResult:
    skill_id: str
    name: str
    version: str
    output: dict[str, Any]


class KnowledgeCompareSkill:
    skill_id = "knowledge_compare"
    name = "KnowledgeCompareSkill"
    version = "v1"
    description = "Compare two text versions and summarize the differences."

    def execute(self, left_text: str, right_text: str) -> SkillResult:
        left_clean = " ".join(left_text.split())
        right_clean = " ".join(right_text.split())
        left_parts = [item.strip() for item in left_clean.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").splitlines() if item.strip()]
        right_parts = [item.strip() for item in right_clean.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").splitlines() if item.strip()]

        left_set = set(left_parts)
        right_set = set(right_parts)
        added = sorted(right_set - left_set)
        removed = sorted(left_set - right_set)
        common = sorted(left_set & right_set)

        summary = []
        if added:
            summary.append(f"新增 {len(added)} 条内容")
        if removed:
            summary.append(f"删除 {len(removed)} 条内容")
        if common:
            summary.append(f"保留 {len(common)} 条内容")
        if not summary:
            summary.append("两版内容基本一致")

        return SkillResult(
            skill_id=self.skill_id,
            name=self.name,
            version=self.version,
            output={
                "summary": "；".join(summary),
                "added": added[:10],
                "removed": removed[:10],
                "common": common[:10],
                "left_length": len(left_text),
                "right_length": len(right_text),
            },
        )
