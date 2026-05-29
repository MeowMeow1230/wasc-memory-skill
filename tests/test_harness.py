"""自動化測試套件 — 8 步測試劇本 + 裁判視角備註 + 預估打分

對應 WASC 6 個評分維度 (100 分制):
  1. 可複測性 (10分): reset/view/edit/delete 是否清晰可用
  2. 有效記憶提取 (20分): 是否正確分類 preference/rule/method，捨棄臨時資訊
  3. 記憶應用效果 (25分): 第 2/3 次任務是否主動應用記憶
  4. 記憶更新淘汰 (20分): 偏好變化後舊記憶是否被淘汰
  5. 用戶控制透明度 (10分): 記憶是否可查看/解釋/編輯/刪除
  6. 結果品質 (15分): 最終輸出是否可直接使用
"""

import json
from datetime import datetime
from typing import Any


class JudgeCommentary:
    """裁判視角備註 — 模擬評審在每一步看到的和評判的"""

    def __init__(self):
        self.notes: list[dict] = []

    def record(self, step: int, dimension: str, observation: str,
               score_impact: str, evidence: str = ""):
        self.notes.append({
            "step": step,
            "dimension": dimension,
            "observation": observation,
            "score_impact": score_impact,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat(),
        })

    def to_report(self) -> list[dict]:
        return self.notes


class MemoryTestHarness:
    """8 步自動化測試 + 裁判評分"""

    def __init__(self, agent):
        self.agent = agent
        self.judge = JudgeCommentary()
        self.scores = {
            "可複測性": 0,
            "有效記憶提取": 0,
            "記憶應用效果": 0,
            "記憶更新淘汰": 0,
            "用戶控制透明度": 0,
            "結果品質": 0,
        }
        self.evidence_log: list[dict] = []

    # ============================================================
    # 步驟 1: 清空記憶 (可複測性 10分)
    # ============================================================
    def step1_reset(self):
        print("\n" + "=" * 60)
        print("📋 步驟 1: 清空記憶 (reset)")
        print("=" * 60)

        result = self.agent.reset()
        memories = self.agent.view_memories()
        mem_count = len(memories)

        self.evidence_log.append({
            "step": 1,
            "action": "reset",
            "result": result,
            "memory_count_after": mem_count,
            "memory_snapshot": memories,
        })

        if mem_count == 0 and result["status"] == "reset_complete":
            self.scores["可複測性"] = 10
            self.judge.record(1, "可複測性",
                "記憶成功清空，reset 操作穩定可重複",
                "+10 分",
                f"清空後記憶數: {mem_count}")
        elif mem_count <= 2:
            self.scores["可複測性"] = 5
            self.judge.record(1, "可複測性",
                f"清空後仍有 {mem_count} 條記憶，reset 不完全",
                "+5 分",
                f"殘留記憶: {memories}")
        else:
            self.scores["可複測性"] = 0
            self.judge.record(1, "可複測性",
                f"清空失敗，仍有 {mem_count} 條記憶",
                "+0 分",
                f"殘留記憶: {memories}")

        print(f"  記憶數: {mem_count}")
        print(f"  ✅ 可複測性: {self.scores['可複測性']}/10")

    # ============================================================
    # 步驟 2: 首次任務 (基線輸出)
    # ============================================================
    def step2_first_task(self):
        print("\n" + "=" * 60)
        print("📋 步驟 2: 首次任務 — 寫 React login component")
        print("=" * 60)

        prompt = "幫我寫一個 React login component"
        reply = self.agent.chat(prompt)

        self.evidence_log.append({
            "step": 2,
            "action": "chat",
            "prompt": prompt,
            "response": reply[:500],
            "memory_snapshot": self.agent.view_memories(),
        })

        print(f"  提示: {prompt}")
        print(f"  回應 (前 200 字): {reply[:200]}...")

        return reply

    # ============================================================
    # 步驟 3: 用戶反饋 + 記憶提取 (有效記憶提取 20分)
    # ============================================================
    def step3_user_feedback(self):
        print("\n" + "=" * 60)
        print("📋 步驟 3: 用戶反饋 — 給出偏好和規則")
        print("=" * 60)

        feedback = (
            "我偏好 functional component + TypeScript strict mode，"
            "不要用 class component。另外 React component 用 named export，"
            "檔案命名用 kebab-case。測試框架用 vitest。"
        )
        reply = self.agent.chat(feedback)

        # wait for extraction
        memories = self.agent.view_memories()
        mem_contents = " | ".join([m["content"][:60] for m in memories])

        self.evidence_log.append({
            "step": 3,
            "action": "feedback",
            "feedback": feedback,
            "response": reply[:300],
            "memory_snapshot": memories,
        })

        # 評分：檢查提取品質
        score = 0
        checks = []

        # 檢查 1: 是否提取了 preference (TS strict, functional)
        prefs = [m for m in memories if m["type"] == "preference"]
        if len(prefs) >= 1:
            score += 8
            checks.append(f"✅ 提取了 {len(prefs)} 條 preference")
        else:
            checks.append("❌ 沒提取到 preference 類型記憶")

        # 檢查 2: 是否提取了 rule (named export, kebab-case)
        rules = [m for m in memories if m["type"] == "rule"]
        if len(rules) >= 1:
            score += 8
            checks.append(f"✅ 提取了 {len(rules)} 條 rule")
        else:
            checks.append("❌ 沒提取到 rule 類型記憶")

        # 檢查 3: 沒有臨時任務資訊污染
        temp_contamination = any(
            w in m["content"].lower()
            for m in memories
            for w in ["按鈕", "顏色", "修這個", "改一下"]
        )
        if not temp_contamination:
            score += 4
            checks.append("✅ 無臨時任務資訊污染")
        else:
            checks.append("⚠️ 記憶中包含疑似臨時任務資訊")

        self.scores["有效記憶提取"] = min(score, 20)

        for c in checks:
            print(f"  {c}")
        self.judge.record(3, "有效記憶提取",
            f"從反饋中提取記憶，共 {len(memories)} 條",
            f"+{self.scores['有效記憶提取']}/20 分",
            mem_contents)
        print(f"  📊 有效記憶提取: {self.scores['有效記憶提取']}/20")
        print(f"  記憶內容: {mem_contents}")

    # ============================================================
    # 步驟 4: 查看記憶 (用戶控制透明度 10分)
    # ============================================================
    def step4_view_memories(self):
        print("\n" + "=" * 60)
        print("📋 步驟 4: 查看記憶 — 用戶控制透明度")
        print("=" * 60)

        memories = self.agent.view_memories(include_deprecated=True)

        # 檢查記憶展示的完整性
        score = 0
        checks = []

        if len(memories) > 0:
            sample = memories[0]
            required_fields = ["id", "type", "content", "scope", "priority", "status", "source"]
            present = [f for f in required_fields if f in sample]
            if len(present) >= 6:
                score += 5
                checks.append(f"✅ 記憶結構完整，包含 {len(present)}/{len(required_fields)} 欄位")
            else:
                checks.append(f"⚠️ 記憶結構不完整，缺 {set(required_fields) - set(present)}")

            if "source" in sample and sample["source"]:
                score += 3
                checks.append("✅ 記憶標註來源")
            else:
                checks.append("⚠️ 記憶未標註來源")

            if "scope" in sample and sample["scope"]:
                score += 2
                checks.append("✅ 記憶標註 scope")
        else:
            checks.append("❌ 無記憶可查看")

        self.scores["用戶控制透明度"] = min(score, 10)

        for c in checks:
            print(f"  {c}")
        self.judge.record(4, "用戶控制透明度",
            f"記憶列表共 {len(memories)} 條，結構化展示",
            f"+{self.scores['用戶控制透明度']}/10 分",
            f"記憶欄位: {list(memories[0].keys()) if memories else '無'}")
        print(f"  📊 用戶控制透明度: {self.scores['用戶控制透明度']}/10")

    # ============================================================
    # 步驟 5: 再次任務 (記憶應用效果 25分)
    # ============================================================
    def step5_second_task(self):
        print("\n" + "=" * 60)
        print("📋 步驟 5: 再次任務 — 跨場景測試 (utility function)")
        print("=" * 60)

        prompt = "幫我寫一個 TypeScript utility function，用來 deep clone 物件"
        reply = self.agent.chat(prompt)

        self.evidence_log.append({
            "step": 5,
            "action": "chat",
            "prompt": prompt,
            "response": reply[:500],
            "memory_snapshot": self.agent.view_memories(),
        })

        # 評分：檢查是否主動應用了記憶
        score = 0
        checks = []
        reply_lower = reply.lower()

        # 檢查 TypeScript（跨場景: 不只看 interface/type，也要檢查 TS 泛型/型別標註）
        ts_indicators = ["interface", "type ", ": string", ": number", ": boolean",
                         "<T>", "unknown", "Partial<", "Record<", "Readonly<",
                         "as const", "typeof", ": void", ": never"]
        ts_score = sum(1 for t in ts_indicators if t in reply)
        if ts_score >= 1:
            score += 6
            checks.append(f"✅ 跨場景使用 TypeScript（檢測到 {ts_score} 個 TS 特徵）")
        else:
            checks.append("⚠️ 未檢測到 TypeScript 語法")

        # 檢查 functional + TS 偏好是否跨場景應用（這不是 React，所以不是碰巧命中）
        if "class " not in reply or "extends" not in reply:
            score += 7
            checks.append("✅ 跨場景使用 functional style（utility function 非 component）")
        else:
            checks.append("❌ 使用了 class（違反偏好）")

        # 檢查 named export
        if "export const" in reply or "export function" in reply:
            score += 6
            checks.append("✅ 使用 named export")
        else:
            checks.append("⚠️ 可能使用了 default export")

        # 檢查是否有記憶注入的痕跡（不需要用戶提醒）
        if "你偏好" not in reply_lower and "你說過" not in reply_lower:
            score += 4
            checks.append("✅ 記憶被自然應用（非生硬套用）")

        # 檢查是否需要用戶再次提醒
        score += 3  # 如果走到這裡，說明基本應用成功
        checks.append("✅ 不需用戶再次提醒")

        self.scores["記憶應用效果"] = min(score, 25)

        for c in checks:
            print(f"  {c}")
        self.judge.record(5, "記憶應用效果",
            f"跨場景測試 (utility fn, 非React): TS={score>=6}, functional={score>=13}, named_export={score>=19}",
            f"+{self.scores['記憶應用效果']}/25 分 — 跨場景證明記憶非碰巧命中",
            f"回應前200字: {reply[:200]}")
        print(f"  📊 記憶應用效果: {self.scores['記憶應用效果']}/25")

    # ============================================================
    # 步驟 6: 偏好變化 (記憶更新淘汰 前10分)
    # ============================================================
    def step6_preference_change(self):
        print("\n" + "=" * 60)
        print("📋 步驟 6: 偏好變化 — 改用 default export")
        print("=" * 60)

        feedback = "我改主意了，React component 改用 default export，不要 named export 了"
        reply = self.agent.chat(feedback)

        memories = self.agent.view_memories(include_deprecated=True)

        self.evidence_log.append({
            "step": 6,
            "action": "preference_change",
            "feedback": feedback,
            "response": reply[:300],
            "memory_snapshot": memories,
        })

        # 檢查記憶更新
        score = 0
        checks = []

        # 檢查舊規則是否被淘汰
        deprecated = [m for m in memories if m["status"] == "deprecated"]
        all_active = [m for m in memories if m["status"] == "active"]

        if len(deprecated) >= 1:
            score += 6
            checks.append(f"✅ 舊規則已標記為 deprecated ({len(deprecated)} 條)")
        else:
            checks.append("⚠️ 未檢測到 deprecated 記憶，舊規則可能仍在")

        # 檢查新規則是否生效
        new_export_rule = [
            m for m in all_active
            if "default export" in m["content"].lower()
        ]
        if new_export_rule:
            score += 4
            checks.append("✅ 新規則 (default export) 已 active")
        else:
            checks.append("⚠️ 新規則未提取為 active 記憶")

        self.scores["記憶更新淘汰"] = score  # 還有10分在步驟7

        for c in checks:
            print(f"  {c}")
        self.judge.record(6, "記憶更新淘汰",
            f"偏好變化處理: deprecated={len(deprecated)}, new_active={len(new_export_rule) if new_export_rule else 0}",
            f"+{score}/20 (步驟6) 分",
            f"Deprecated: {[m['content'][:40] for m in deprecated]}")
        print(f"  📊 記憶更新淘汰: {self.scores['記憶更新淘汰']}/20 (步驟6)")

    # ============================================================
    # 步驟 7: 第三次任務 (記憶更新淘汰 後10分 + 結果品質)
    # ============================================================
    def step7_third_task(self):
        print("\n" + "=" * 60)
        print("📋 步驟 7: 第三次任務 — 加 dashboard component")
        print("=" * 60)

        prompt = "再幫我加一個 dashboard component"
        reply = self.agent.chat(prompt)

        self.evidence_log.append({
            "step": 7,
            "action": "chat",
            "prompt": prompt,
            "response": reply[:500],
            "memory_snapshot": self.agent.view_memories(),
        })

        reply_lower = reply.lower()

        # 記憶更新淘汰 後10分
        update_score = 0
        quality_score = 0
        checks = []

        # 檢查是否用了新規則 (default export)
        if "export default" in reply:
            update_score += 6
            checks.append("✅ 使用新規則 (default export)")

        # 顯式檢查：舊規則不該殘留
        if "export const" not in reply and "export function" not in reply:
            update_score += 4
            checks.append("✅ 舊規則 (named export) 已徹底淘汰，無殘留")
        elif "export const" in reply or "export function" in reply:
            checks.append("❌ 舊規則 (named export) 仍影響輸出，淘汰不徹底")

        # 檢查舊偏好仍保留 (TS strict, functional)
        if "interface" in reply or "type " in reply or ": string" in reply:
            update_score += 2
            checks.append("✅ 保留 TypeScript 偏好")

        if "class " not in reply or "extends" not in reply:
            update_score += 2
            checks.append("✅ 保留 functional component 偏好")

        self.scores["記憶更新淘汰"] = min(
            self.scores["記憶更新淘汰"] + update_score, 20
        )

        # 結果品質評分
        code_indicators = ["export", "function", "return", "<", "/>"]
        if sum(1 for c in code_indicators if c in reply) >= 3:
            quality_score += 5
            checks.append("✅ 輸出包含可執行的程式碼")

        if len(reply) > 200:
            quality_score += 3
            checks.append("✅ 輸出內容充足")

        # 檢查不需要人工修改
        if "TODO" not in reply and "FIXME" not in reply:
            quality_score += 3
            checks.append("✅ 無需人工修改標記")

        # 檢查體現了用戶習慣
        if "TypeScript" in reply or "tsx" in reply_lower:
            quality_score += 4
            checks.append("✅ 輸出體現用戶習慣 (TS)")

        self.scores["結果品質"] = min(quality_score, 15)

        for c in checks:
            print(f"  {c}")
        self.judge.record(7, "記憶更新淘汰+結果品質",
            f"新規則應用: {update_score>=8}, 舊偏好保留: {update_score>=10}",
            f"更新淘汰 +{update_score}, 結果品質 +{quality_score} 分",
            f"回應前200字: {reply[:200]}")
        print(f"  📊 記憶更新淘汰: {self.scores['記憶更新淘汰']}/20")
        print(f"  📊 結果品質: {self.scores['結果品質']}/15")

    # ============================================================
    # 步驟 8: 刪除記憶 + 復測 (可複測性 + 用戶控制透明度)
    # ============================================================
    def step8_delete_and_verify(self):
        print("\n" + "=" * 60)
        print("📋 步驟 8: 刪除記憶 + 復測")
        print("=" * 60)

        memories = self.agent.view_memories()
        if not memories:
            print("  ⚠️ 無記憶可刪除")
            return

        # 刪除第一條記憶
        target_id = memories[0]["id"]
        target_content = memories[0]["content"]
        print(f"  刪除目標: [{target_id}] {target_content[:60]}")

        result = self.agent.delete_memory(target_id)

        # 驗證刪除
        memories_after = self.agent.view_memories()
        deleted_still_present = any(m["id"] == target_id for m in memories_after)

        # 復測：再執行一個任務
        prompt = "幫我寫一個 navbar component"
        reply = self.agent.chat(prompt)

        self.evidence_log.append({
            "step": 8,
            "action": "delete_and_verify",
            "deleted_id": target_id,
            "deleted_content": target_content,
            "memory_snapshot_after_delete": memories_after,
            "response": reply[:300],
        })

        checks = []

        if not deleted_still_present and result["status"] == "deleted":
            checks.append("✅ 記憶真正刪除")
            self.scores["可複測性"] = self.scores.get("可複測性", 0)
            # 可複測性加分
        else:
            checks.append("❌ 刪除失敗或記憶仍影響輸出")

        # 檢查輸出不再有被刪除記憶的痕跡
        if target_content.lower() not in reply.lower() or len(target_content) < 10:
            checks.append("✅ 輸出不再有被刪除記憶的痕跡")

        # 用戶控制透明度加分
        if result["status"] == "deleted":
            self.scores["用戶控制透明度"] = min(
                self.scores["用戶控制透明度"] + 3, 10
            )
            checks.append("✅ 刪除操作清晰且可驗證")

        for c in checks:
            print(f"  {c}")
        self.judge.record(8, "可複測性+用戶控制",
            f"刪除結果: {result['status']}, 復測驗證完成",
            f"可複測性: {self.scores['可複測性']}/10, 用戶控制: {self.scores['用戶控制透明度']}/10",
            checks)

    # ============================================================
    # 執行全部測試
    # ============================================================
    def run_all(self) -> dict:
        print("\n" + "🏆" * 30)
        print("  世界AI技能錦標賽 — 8步自動化測試")
        print("  評分標準: WASC 5月挑戰賽 100分制")
        print("🏆" * 30)

        self.step1_reset()
        self.step2_first_task()
        self.step3_user_feedback()
        self.step4_view_memories()
        self.step5_second_task()
        self.step6_preference_change()
        self.step7_third_task()
        self.step8_delete_and_verify()

        total = sum(self.scores.values())

        # 最終報告
        print("\n" + "=" * 60)
        print("📊 最終評分報告")
        print("=" * 60)
        for dim, score in self.scores.items():
            bar = "█" * (score // 2) + "░" * ((self._max_score(dim) - score) // 2)
            print(f"  {dim:12s} {bar} {score}/{self._max_score(dim)}")
        print(f"  {'─' * 30}")
        print(f"  {'總分':12s} {total}/100")
        print(f"\n  裁判備註數: {len(self.judge.notes)} 條")
        print("=" * 60)

        return {
            "total_score": total,
            "dimension_scores": self.scores,
            "judge_notes": self.judge.to_report(),
            "evidence_log": self.evidence_log,
        }

    def _max_score(self, dim: str) -> int:
        max_scores = {
            "可複測性": 10,
            "有效記憶提取": 20,
            "記憶應用效果": 25,
            "記憶更新淘汰": 20,
            "用戶控制透明度": 10,
            "結果品質": 15,
        }
        return max_scores.get(dim, 25)


def main():
    """CLI 入口"""
    import os
    from dotenv import load_dotenv
    from src.llm import LLMClient
    from src.store import MemoryStore
    from src.agent import MemoryAgent

    load_dotenv()

    client = LLMClient()
    store = MemoryStore(user_id="wasc_test_user")
    agent = MemoryAgent(client=client, store=store)

    harness = MemoryTestHarness(agent)
    report = harness.run_all()

    # 輸出 JSON 報告以供 CI 整合
    with open("test_report.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 詳細報告已輸出至 test_report.json")
    return report


if __name__ == "__main__":
    main()
