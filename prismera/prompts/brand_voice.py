"""PrismEra Global Brand Voice & Guidelines."""

BRAND_VOICE_GUIDELINES = """
# PrismEra Global Brand Voice (棱镜纪·全局语调准则)
1. **克制而有温度的智性美**：拒绝传统中介贩卖焦虑的推销话术，也拒绝机械客服的冰冷感。你的语言应当像一位兼具理工科精密思维与人文素养的青年学者——温和、笃定、清澈、一针见血。
2. **微光学隐喻（点睛而不堆砌）**：在阶段转换或总结时，可自然融入轻量级的光学词汇（如：聚焦、切面、折射、光谱、共鸣、校准、暗区），但绝不能因辞藻华丽而牺牲申请数据的绝对精确性。
3. **默认首屏开场白（Onboarding Message）**：
   > “欢迎来到 **PrismEra（棱镜纪）**。
   > 每一段沉默的履历，都是一束尚未被拆解的原光。在这里，我们以全球院校知识图谱为切面，以深度叙事为介质，陪你完成从自我审视到彼岸学府的精准折射。
   > 
   > 告诉我，你目前正处于哪一个阶段？（你可以直接发送你的成绩单/简历，或告诉我你的本科背景与心中的远方。）”
""".strip()

ONBOARDING_MESSAGE = (
    "欢迎来到 **PrismEra（棱镜纪）**。\n"
    "每一段沉默的履历，都是一束尚未被拆解的原光。在这里，我们以全球院校知识图谱为切面，"
    "以深度叙事为介质，陪你完成从自我审视到彼岸学府的精准折射。\n\n"
    "告诉我，你目前正处于哪一个阶段？（你可以直接发送你的成绩单/简历，或告诉我你的本科背景与心中的远方。）"
)

# Anti-AI Lexicon blacklist (PrismEra 禁用词黑名单与后置校验器字典)
ANTI_AI_BANNED_WORDS = [
    "delve into",
    "delves into",
    "delved into",
    "delving into",
    "delve",
    "delves",
    "delved",
    "delving",
    "testament to",
    "testaments to",
    "testament",
    "testaments",
    "rich tapestry",
    "rich tapestries",
    "tapestry",
    "tapestries",
    "beacon of hope",
    "beacons of hope",
    "unwavering passion",
    "embark on a journey",
    "embarks on a journey",
    "embarked on a journey",
    "embarking on a journey",
    "realm",
    "realms",
    "pivotal",
    "underscore",
    "underscores",
    "underscored",
    "underscoring",
    "symphony",
    "symphonies",
    "ignite my interest",
    "ignited my interest",
    "ignites my interest",
    "igniting my interest",
    "transformative journey",
    "a testament",
    "deep dive into",
    "deep dives into",
    "deep dive",
    "deep dives",
]

# 经典 AI 陈词滥调与地道学术动词替换字典（用于确定性重写修复）
ANTI_AI_REPLACEMENTS = {
    "delve into": "examine",
    "delves into": "examines",
    "delved into": "examined",
    "delving into": "examining",
    "delve": "investigate",
    "delves": "investigates",
    "delved": "investigated",
    "delving": "investigating",
    "testament to": "evidence of",
    "testaments to": "evidence of",
    "testament": "evidence",
    "testaments": "indicators",
    "rich tapestry": "architecture",
    "rich tapestries": "architectures",
    "tapestry": "system",
    "tapestries": "systems",
    "beacon of hope": "guiding standard",
    "beacons of hope": "guiding standards",
    "unwavering passion": "focused commitment",
    "embark on a journey": "pursue research",
    "embarks on a journey": "pursues research",
    "embarked on a journey": "pursued research",
    "embarking on a journey": "pursuing research",
    "realm": "field",
    "realms": "fields",
    "pivotal": "critical",
    "underscore": "emphasize",
    "underscores": "emphasizes",
    "underscored": "emphasized",
    "underscoring": "emphasizing",
    "symphony": "coordination",
    "symphonies": "coordinations",
    "ignite my interest": "sparked my inquiry",
    "ignited my interest": "sparked my inquiry",
    "ignites my interest": "sparks my inquiry",
    "igniting my interest": "sparking my inquiry",
    "transformative journey": "iterative exploration",
    "a testament": "an indicator",
    "deep dive into": "analyze",
    "deep dives into": "analyzes",
    "deep dive": "analysis",
    "deep dives": "analyses",
}

