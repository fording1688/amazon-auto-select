SYSTEM_PROMPT = """你是一名资深亚马逊美国站选品和广告运营顾问，专门分析五金工具、工业耗材、金刚石工具、CBN磨轮、玻璃工具、替换件类产品。"""

ANALYSIS_PROMPT_TEMPLATE = """
请根据以下竞品数据，判断这个产品是否适合测款。

我的选品偏好：
1. 优先轻小件，不要抛重产品。
2. 优先工业耗材、替换件、复购型产品。
3. 优先可以做 3-pack、5-pack、10-pack 批量组合销售的产品。
4. 优先中国供应链有成本优势的产品。
5. 优先原厂配件贵、非原厂替代件有机会的产品。
6. 避开认证风险高、安全风险高、侵权风险高的产品。
7. 前期使用 FBM 小批量测款，后期表现好再考虑 FBA。
8. 不追求大众爆品，更看重小众、高利润、稳定复购。

竞品数据：
{product_json}

规则评分参考：
{score_json}

请输出结构化 JSON，格式如下：

{{
  "decision": "重点测款 / 小批量测试 / 观察 / 放弃",
  "opportunity_score": 0-100,
  "summary": "一句话总结这个产品机会",
  "reasons": [
    "推荐原因1",
    "推荐原因2",
    "推荐原因3"
  ],
  "risks": [
    "风险1",
    "风险2"
  ],
  "bundle_strategy": {{
    "suitable_for_bundle": true,
    "recommended_packs": ["3-pack", "5-pack", "10-pack"],
    "reason": "为什么适合或不适合做组合装"
  }},
  "pricing_suggestion": {{
    "single_pack_price": "",
    "three_pack_price": "",
    "five_pack_price": "",
    "ten_pack_price": ""
  }},
  "listing_suggestion": {{
    "title": "",
    "bullet_points": [
      "",
      "",
      "",
      "",
      ""
    ],
    "description": ""
  }},
  "image_selling_points": [
    "主图建议",
    "第二张图建议",
    "第三张图建议",
    "第四张图建议",
    "第五张图建议"
  ],
  "ad_keywords": [
    "",
    "",
    ""
  ],
  "negative_keywords": [
    "",
    "",
    ""
  ],
  "fbm_test_plan_14_days": {{
    "day_1_to_3": "",
    "day_4_to_7": "",
    "day_8_to_14": "",
    "success_criteria": "",
    "stop_loss_criteria": ""
  }},
  "next_action": "我下一步应该做什么"
}}

要求：
- 不要泛泛而谈，要给出具体建议。
- 如果产品不适合测款，要明确说明为什么。
- 如果适合测款，要重点说明如何通过多件装、组合装、批量价格做差异化。
- 输出必须是合法 JSON，方便系统解析。
"""
