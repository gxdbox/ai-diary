"""
深度洞察分析服务

核心职责：从日记数据中提取洞察，帮助用户认识自己

四大分类分析：
1. 自我认知 - 天赋、写作人格、价值观
2. 生活状态 - 情绪健康、生活平衡、人际关系
3. 风险预警 - 危机信号、方向偏差、能量黑洞
4. 成长激励 - 积极变化、希望方向、盲点提示
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re
import json

from app.models.insight import (
    InsightCategory, InsightSubType, SeverityLevel,
    DeepInsight, InsightCategoryResult, DeepInsightResponse,
    WritingTimeDistribution, EmotionAnalysis, KeywordFrequency, TopicDistribution
)


class InsightAnalyzer:
    """深度洞察分析器"""

    # ==================== 配置常量 ====================

    # 危机信号关键词（负面健康/心理）
    CRISIS_KEYWORDS = [
        "失眠", "焦虑", "抑郁", "孤独", "压力", "崩溃", "绝望",
        "疲惫", "透不过气", "窒息", "头痛", "心悸", "失眠",
        "不想起床", "没有意义", "想放弃", "活着没意思"
    ]

    # 价值观关键词
    VALUE_KEYWORDS = [
        "自由", "成长", "家庭", "健康", "友谊", "事业",
        "爱情", "金钱", "稳定", "冒险", "创造", "贡献"
    ]

    # 生活领域分类
    LIFE_DOMAINS = {
        "工作": ["工作", "会议", "项目", " deadline", "加班", "任务", "汇报", "绩效"],
        "健康": ["健康", "运动", "健身", "跑步", "饮食", "睡眠", "身体", "医院"],
        "社交": ["朋友", "聚会", "社交", "聊天", "约会", "见面", "聚餐"],
        "学习": ["学习", "读书", "课程", "技能", "成长", "进步", "知识"],
        "家庭": ["家人", "父母", "孩子", "伴侣", "老公", "老婆", "爸妈"],
        "娱乐": ["娱乐", "游戏", "电影", "旅游", "放松", "休息", "爱好"]
    }

    # 基础需求词（用于盲点检测）
    BASIC_NEED_KEYWORDS = [
        "休息", "睡眠", "运动", "喝水", "吃饭", "社交",
        "放松", "娱乐", "健康", "体检"
    ]

    # 积极变化关键词映射（负面→正面）
    POSITIVE_TRANSITIONS = {
        "焦虑": "平静",
        "迷茫": "清晰",
        "疲惫": "有活力",
        "孤独": "温暖",
        "压力": "放松",
        "担忧": "安心",
        "烦躁": "平静"
    }

    # 写作人格命名
    WRITING_PERSONAS = {
        "morning": ("晨间规划者", "清晨是你的清醒时刻，习惯早起梳理思绪"),
        "afternoon": ("午后记录者", "午间时光让你放松，适合整理心情"),
        "evening": ("晚间反思者", "晚餐后是你的反思时间，习惯回顾一天"),
        "night": ("深夜反思者", "夜晚让你更诚实，深夜是你的内心对话时间"),
        "late_night": ("凌晨独行者", "凌晨时分你独自面对内心，这是最真实的时刻")
    }

    # 天赋识别模式
    TALENT_PATTERNS = {
        "写作": {
            "markers": ["比喻", "细节", "描写", "画面", "仿佛", "好像"],
            "desc": "擅长用文字表达复杂情感"
        },
        "内省": {
            "markers": ["反思", "思考", "觉察", "意识到", "发现", "明白", "理解"],
            "desc": "具有深度自我反思能力"
        },
        "同理心": {
            "markers": ["理解他", "感受", "心疼", "担心", "关心", "在乎"],
            "desc": "善于感知他人的情绪"
        },
        "专注": {
            "markers": ["投入", "沉浸", "专注", "研究", "深入"],
            "desc": "能够长时间专注某领域"
        }
    }

    # ==================== 主分析方法 ====================

    def analyze(self, diaries: List[Dict], days: int = 90) -> DeepInsightResponse:
        """
        主分析方法 - 从日记列表生成深度洞察

        Args:
            diaries: 日记列表，每条包含 created_at, emotion, emotion_score, topics, cleaned_text 等
            days: 分析周期天数

        Returns:
            DeepInsightResponse: 完整的深度洞察响应
        """
        if not diaries:
            return self._empty_response(days)

        # 预处理：提取中间数据
        time_dist = self._analyze_writing_time(diaries)
        emotion_analysis = self._analyze_emotion(diaries)
        keyword_freq = self._analyze_keywords(diaries)
        topic_dist = self._analyze_topics(diaries)

        # 四分类分析
        self_knowledge = self._analyze_self_knowledge(diaries, time_dist, keyword_freq)
        life_state = self._analyze_life_state(diaries, emotion_analysis, topic_dist)
        risk_alert = self._analyze_risk_alert(diaries, keyword_freq, emotion_analysis)
        growth = self._analyze_growth(diaries, keyword_freq, emotion_analysis)

        # 组装结果
        categories = [
            self_knowledge,
            life_state,
            risk_alert,
            growth
        ]

        # 生成整体摘要
        overall_summary = self._generate_overall_summary(categories)

        return DeepInsightResponse(
            categories=categories,
            overall_summary=overall_summary,
            stats_context={
                "total_diaries": len(diaries),
                "analysis_period_days": days,
                "avg_emotion_score": emotion_analysis.average_score,
                "dominant_writing_time": time_dist.dominant_period
            },
            generated_at=datetime.now().isoformat(),
            analysis_period_days=days
        )

    # ==================== 1. 自我认知分析 ====================

    def _analyze_self_knowledge(
        self,
        diaries: List[Dict],
        time_dist: WritingTimeDistribution,
        keyword_freq: Dict[str, KeywordFrequency]
    ) -> InsightCategoryResult:
        """分析自我认知：天赋、写作人格、价值观"""
        insights = []

        # 写作人格分析
        if time_dist.total >= 10:  # 至少10篇日记才分析
            persona_insight = self._generate_writing_persona_insight(time_dist)
            if persona_insight:
                insights.append(persona_insight)

        # 天赋识别
        talent_insights = self._detect_talents(diaries)
        insights.extend(talent_insights)

        # 价值观识别
        value_insight = self._detect_core_value(keyword_freq)
        if value_insight:
            insights.append(value_insight)

        # 生成 highlight
        highlight = None
        if insights:
            highlight = insights[0].insight[:50] + "..." if len(insights[0].insight) > 50 else insights[0].insight

        return InsightCategoryResult(
            category=InsightCategory.SELF_KNOWLEDGE,
            category_name="自我认知",
            category_icon="🪞",
            insights=insights,
            highlight=highlight
        )

    def _generate_writing_persona_insight(self, time_dist: WritingTimeDistribution) -> Optional[DeepInsight]:
        """生成写作人格洞察"""
        if not time_dist.dominant_period or time_dist.total < 10:
            return None

        persona_name, persona_desc = self.WRITING_PERSONAS.get(
            time_dist.dominant_period,
            ("记录者", "你习惯用日记记录生活")
        )

        # 计算占比
        dominant_count = getattr(time_dist, time_dist.dominant_period, 0)
        percentage = round(dominant_count / time_dist.total * 100) if time_dist.total > 0 else 0

        return DeepInsight(
            category=InsightCategory.SELF_KNOWLEDGE,
            sub_type=InsightSubType.WRITING_PERSONA,
            title="写作人格",
            insight=f"你是「{persona_name}」——{percentage}%的日记在{self._period_name(time_dist.dominant_period)}，{persona_desc}",
            evidence=[f"共{time_dist.total}篇日记，{self._period_name(time_dist.dominant_period)}{dominant_count}篇"],
            severity=SeverityLevel.INFO,
            icon="🌙",
            confidence=0.8
        )

    def _detect_talents(self, diaries: List[Dict]) -> List[DeepInsight]:
        """检测天赋"""
        talents = []
        all_text = " ".join([d.get("cleaned_text", "") or d.get("raw_text", "") for d in diaries])

        for talent_name, pattern in self.TALENT_PATTERNS.items():
            count = sum(1 for marker in pattern["markers"] if marker in all_text)
            if count >= 5:  # 至少5次出现
                talents.append(DeepInsight(
                    category=InsightCategory.SELF_KNOWLEDGE,
                    sub_type=InsightSubType.TALENT,
                    title=f"{talent_name}天赋",
                    insight=f"你有{pattern['desc']}的信号——相关表达出现{count}次以上",
                    evidence=[f"{talent_name}相关词汇出现{count}次"],
                    severity=SeverityLevel.INFO,
                    icon="✨",
                    confidence=0.75
                ))

        return talents[:2]  #最多返回2个天赋

    def _detect_core_value(self, keyword_freq: Dict[str, KeywordFrequency]) -> Optional[DeepInsight]:
        """检测核心价值观"""
        value_counts = {}
        for value in self.VALUE_KEYWORDS:
            if value in keyword_freq:
                value_counts[value] = keyword_freq[value].count

        if not value_counts:
            return None

        top_value = max(value_counts.items(), key=lambda x: x[1])
        if top_value[1] >= 3:  # 至少3次提及
            return DeepInsight(
                category=InsightCategory.SELF_KNOWLEDGE,
                sub_type=InsightSubType.VALUE,
                title="核心价值观",
                insight=f"你最常提及「{top_value[0]}」，共{top_value[1]}次——这可能是你的核心价值观",
                evidence=[f"{top_value[0]}出现{top_value[1]}次"],
                severity=SeverityLevel.INFO,
                icon="💎",
                confidence=0.7
            )
        return None

    # ==================== 2. 生活状态分析 ====================

    def _analyze_life_state(
        self,
        diaries: List[Dict],
        emotion_analysis: EmotionAnalysis,
        topic_dist: Dict[str, TopicDistribution]
    ) -> InsightCategoryResult:
        """分析生活状态：情绪健康、生活平衡、人际关系"""
        insights = []

        # 情绪健康分析
        emotion_insight = self._analyze_emotion_health(emotion_analysis)
        if emotion_insight:
            insights.append(emotion_insight)

        # 生活平衡分析
        balance_insight = self._analyze_life_balance(topic_dist)
        if balance_insight:
            insights.append(balance_insight)

        # 人际关系分析
        relationship_insight = self._analyze_relationships(diaries)
        if relationship_insight:
            insights.append(relationship_insight)

        # 生成 highlight
        highlight = None
        if insights:
            # 优先显示warning级别的
            warning_insights = [i for i in insights if i.severity == SeverityLevel.WARNING]
            if warning_insights:
                highlight = warning_insights[0].insight[:50] + "..."
            else:
                highlight = insights[0].insight[:50] + "..."

        return InsightCategoryResult(
            category=InsightCategory.LIFE_STATE,
            category_name="生活状态",
            category_icon="🌿",
            insights=insights,
            highlight=highlight
        )

    def _analyze_emotion_health(self, emotion_analysis: EmotionAnalysis) -> Optional[DeepInsight]:
        """分析情绪健康状态"""
        deviation = emotion_analysis.deviation
        volatility = emotion_analysis.volatility

        # 判断状态
        if deviation < -1:  # 比baseline低1分以上
            severity = SeverityLevel.WARNING
            status_desc = "近期情绪低于你的常态"
            trend_icon = "📉"
        elif deviation > 0.5:  # 比baseline高
            severity = SeverityLevel.INFO
            status_desc = "近期情绪高于你的常态，状态良好"
            trend_icon = "📈"
        else:
            severity = SeverityLevel.INFO
            status_desc = "情绪状态稳定"
            trend_icon = "📊"

        # 波动性描述
        volatility_desc = ""
        if volatility > 2:
            volatility_desc = "，但波动较大"
        elif volatility < 1:
            volatility_desc = "，情绪平稳"

        return DeepInsight(
            category=InsightCategory.LIFE_STATE,
            sub_type=InsightSubType.EMOTION_HEALTH,
            title="情绪健康",
            insight=f"{status_desc}{volatility_desc}。近期平均{emotion_analysis.average_score:.1f}分，历史平均{emotion_analysis.baseline_score:.1f}分",
            evidence=[
                f"近期平均情绪{emotion_analysis.average_score:.1f}",
                f"历史baseline{emotion_analysis.baseline_score:.1f}",
                f"偏离{deviation:.1f}分"
            ],
            severity=severity,
            icon=trend_icon,
            trend=emotion_analysis.trend,
            confidence=0.85
        )

    def _analyze_life_balance(self, topic_dist: Dict[str, TopicDistribution]) -> Optional[DeepInsight]:
        """分析生活平衡"""
        # 检查是否有领域占比过高或过低
        total_count = sum(t.count for t in topic_dist.values())
        if total_count < 10:
            return None

        percentages = {}
        for domain, markers in self.LIFE_DOMAINS.items():
            count = sum(
                topic_dist.get(m, TopicDistribution(topic=m, count=0)).count
                for m in markers
            )
            percentages[domain] = round(count / total_count * 100, 1) if total_count > 0 else 0

        # 找出失衡领域
        imbalanced = []
        for domain, pct in percentages.items():
            if pct > 60:
                imbalanced.append(("高", domain, pct))
            elif pct < 5 and domain in ["健康", "休息", "社交"]:
                imbalanced.append(("低", domain, pct))

        if not imbalanced:
            return DeepInsight(
                category=InsightCategory.LIFE_STATE,
                sub_type=InsightSubType.LIFE_BALANCE,
                title="生活平衡",
                insight="各生活领域分布相对均衡",
                evidence=[f"工作{percentages.get('工作', 0)}%, 生活{percentages.get('娱乐', 0)}%"],
                severity=SeverityLevel.INFO,
                icon="⚖️",
                confidence=0.6
            )

        # 有失衡
        high_items = [i for i in imbalanced if i[0] == "高"]
        low_items = [i for i in imbalanced if i[0] == "低"]

        desc_parts = []
        if high_items:
            desc_parts.append(f"{high_items[0][1]}占{high_items[0][2]}%")
        if low_items:
            desc_parts.append(f"{low_items[0][1]}仅{low_items[0][2]}%")

        return DeepInsight(
            category=InsightCategory.LIFE_STATE,
            sub_type=InsightSubType.LIFE_BALANCE,
            title="生活平衡",
            insight=f"生活可能失衡：{desc_parts[0]}{'，' + desc_parts[1] if len(desc_parts) > 1 else ''}",
            evidence=[f"{i[1]}占比{i[2]}%" for i in imbalanced[:3]],
            severity=SeverityLevel.WARNING,
            icon="⚖️",
            confidence=0.75
        )

    def _analyze_relationships(self, diaries: List[Dict]) -> Optional[DeepInsight]:
        """分析人际关系"""
        # 提取人物提及和关联情绪
        person_emotions = defaultdict(list)
        person_keywords = ["家人", "朋友", "同事", "伴侣", "父母", "孩子", "老板"]

        for diary in diaries:
            text = diary.get("cleaned_text", "") or diary.get("raw_text", "")
            emotion_score = diary.get("emotion_score", 5)

            for person in person_keywords:
                if person in text:
                    person_emotions[person].append(emotion_score)

        if not person_emotions:
            return None

        # 计算各人物的平均情绪
        person_avg = {}
        for person, scores in person_emotions.items():
            if len(scores) >= 2:  # 至少2次提及
                person_avg[person] = sum(scores) / len(scores)

        if not person_avg:
            return None

        # 找出最高和最低
        sorted_persons = sorted(person_avg.items(), key=lambda x: x[1], reverse=True)
        highest = sorted_persons[0]
        lowest = sorted_persons[-1]

        if highest[1] - lowest[1] > 1.5:  # 差异大于1.5分
            return DeepInsight(
                category=InsightCategory.LIFE_STATE,
                sub_type=InsightSubType.RELATIONSHIP,
                title="人际关系",
                insight=f"提到「{highest[0]}」时情绪{highest[1]:.1f}分最高，提到「{lowest[0]}」时{lowest[1]:.1f}分最低——{highest[0]}是你的能量源",
                evidence=[
                    f"{highest[0]}关联情绪{highest[1]:.1f}",
                    f"{lowest[0]}关联情绪{lowest[1]:.1f}"
                ],
                severity=SeverityLevel.INFO,
                icon="👥",
                confidence=0.7
            )

        return None

    # ==================== 3. 风险预警分析 ====================

    def _analyze_risk_alert(
        self,
        diaries: List[Dict],
        keyword_freq: Dict[str, KeywordFrequency],
        emotion_analysis: EmotionAnalysis
    ) -> InsightCategoryResult:
        """分析风险预警：危机信号、方向偏差、能量黑洞"""
        insights = []

        # 危机信号检测
        crisis_insights = self._detect_crisis_signals(diaries, keyword_freq)
        insights.extend(crisis_insights)

        # 方向偏差检测（需要用户有目标记录）
        direction_insight = self._detect_direction偏差(diaries)
        if direction_insight:
            insights.append(direction_insight)

        # 能量黑洞检测
        energy_insight = self._detect_energy黑洞(diaries)
        if energy_insight:
            insights.append(energy_insight)

        # 情绪持续低迷预警
        if emotion_analysis.average_score < 4 and emotion_analysis.deviation < -1:
            insights.append(DeepInsight(
                category=InsightCategory.RISK_ALERT,
                sub_type=InsightSubType.CRISIS_SIGNAL,
                title="情绪持续低迷",
                insight=f"近期情绪持续低迷（平均{emotion_analysis.average_score:.1f}分），需要关注心理状态",
                evidence=[f"近{len(diaries)}篇日记平均情绪{emotion_analysis.average_score:.1f}"],
                severity=SeverityLevel.ALERT,
                suggestion="建议：尝试做一些让你放松的事，或与信任的人聊聊",
                icon="⚠️",
                confidence=0.85
            ))

        # 生成 highlight（预警类优先显示最严重的）
        highlight = None
        if insights:
            alert_insights = [i for i in insights if i.severity == SeverityLevel.ALERT]
            if alert_insights:
                highlight = alert_insights[0].insight[:50] + "..."
            else:
                highlight = insights[0].insight[:50] + "..."

        return InsightCategoryResult(
            category=InsightCategory.RISK_ALERT,
            category_name="风险预警",
            category_icon="⚠️",
            insights=insights,
            highlight=highlight
        )

    def _detect_crisis_signals(
        self,
        diaries: List[Dict],
        keyword_freq: Dict[str, KeywordFrequency]
    ) -> List[DeepInsight]:
        """检测危机信号"""
        signals = []

        # 按时间分段分析（前半段 vs 后半段）
        mid_point = len(diaries) // 2
        early_diaries = diaries[:mid_point]
        late_diaries = diaries[mid_point:]

        for keyword in self.CRISIS_KEYWORDS[:8]:  # 检查前8个关键词
            early_count = sum(
                1 for d in early_diaries
                if keyword in (d.get("cleaned_text", "") or d.get("raw_text", ""))
            )
            late_count = sum(
                1 for d in late_diaries
                if keyword in (d.get("cleaned_text", "") or d.get("raw_text", ""))
            )

            # 频率上升
            if late_count > early_count and late_count >= 3:
                increase_pct = round((late_count - early_count) / max(early_count, 1) * 100)
                severity = SeverityLevel.ALERT if late_count >= 10 else SeverityLevel.WARNING

                signals.append(DeepInsight(
                    category=InsightCategory.RISK_ALERT,
                    sub_type=InsightSubType.CRISIS_SIGNAL,
                    title=f"「{keyword}」频率上升",
                    insight=f"「{keyword}」近期出现{late_count}次，频率上升{increase_pct}%——可能需要关注",
                    evidence=[
                        f"前半段{early_count}次，后半段{late_count}次",
                        f"频率上升{increase_pct}%"
                    ],
                    severity=severity,
                    suggestion="建议：如果持续困扰，考虑寻求专业帮助",
                    icon="🚨",
                    confidence=0.8
                ))

        return signals[:2]  #最多返回2个危机信号

    def _detect_direction偏差(self, diaries: List[Dict]) -> Optional[DeepInsight]:
        """检测方向偏差（年初/月初目标遗忘）"""
        # 查找日记中是否有目标相关词汇
        goal_keywords = ["目标", "计划", "今年", "今年要", "希望", "想学", "想做的"]

        # 分段：前30%的日记找目标，后70%检查是否遗忘
        goal_section = diaries[:max(3, len(diaries) // 3)]
        check_section = diaries[len(diaries) // 3:]

        # 找出早期设定的目标
        goals_found = {}
        for diary in goal_section:
            text = diary.get("cleaned_text", "") or diary.get("raw_text", "")
            for goal in ["学习", "健康", "运动", "读书", "写作", "旅行", "创业"]:
                if goal in text and any(gk in text for gk in goal_keywords):
                    goals_found[goal] = diary.get("created_at")

        # 检查后期是否还在提
        forgotten_goals = []
        for goal, first_date in goals_found.items():
            recent_mentions = sum(
                1 for d in check_section
                if goal in (d.get("cleaned_text", "") or d.get("raw_text", ""))
            )
            if recent_mentions == 0:
                forgotten_goals.append(goal)

        if forgotten_goals:
            return DeepInsight(
                category=InsightCategory.RISK_ALERT,
                sub_type=InsightSubType.DIRECTION偏差,
                title="目标偏离",
                insight=f"早期设定的「{forgotten_goals[0]}」目标，近{len(check_section)}篇日记未再提及——可能偏离初心",
                evidence=[f"目标「{forgotten_goals[0]}」在{first_date}设定，之后未再提及"],
                severity=SeverityLevel.WARNING,
                suggestion="建议：回顾当初设定的目标，问问自己是否还想继续",
                icon="🧭",
                confidence=0.65
            )

        return None

    def _detect_energy黑洞(self, diaries: List[Dict]) -> Optional[DeepInsight]:
        """检测能量黑洞（某些事件导致情绪下降）"""
        # 分析事件关联情绪
        event_emotions = defaultdict(list)

        energy_keywords = ["会议", "加班", "deadline", "考试", "争吵", "堵车", "通勤"]

        for diary in diaries:
            text = diary.get("cleaned_text", "") or diary.get("raw_text", "")
            emotion_score = diary.get("emotion_score", 5)

            for event in energy_keywords:
                if event in text.lower():
                    event_emotions[event].append(emotion_score)

        # 找出情绪下降最多的事件
        blackholes = []
        overall_avg = sum(d.get("emotion_score", 5) for d in diaries) / len(diaries) if diaries else 5

        for event, scores in event_emotions.items():
            if len(scores) >= 3:  # 至少3次
                avg = sum(scores) / len(scores)
                drop = overall_avg - avg
                if drop > 1:  # 情绪下降超过1分
                    blackholes.append((event, avg, drop, len(scores)))

        if blackholes:
            worst = max(blackholes, key=lambda x: x[2])
            return DeepInsight(
                category=InsightCategory.RISK_ALERT,
                sub_type=InsightSubType.ENERGY黑洞,
                title="能量消耗源",
                insight=f"每次提及「{worst[0]}」，情绪平均下降{worst[2]:.1f}分——这是你的能量黑洞",
                evidence=[
                    f"{worst[0]}关联情绪{worst[1]:.1f}分",
                    f"出现{worst[3]}次",
                    f"比平均低{worst[2]:.1f}分"
                ],
                severity=SeverityLevel.WARNING,
                suggestion="建议：思考如何减少或改变这件事的影响",
                icon="🔋",
                confidence=0.75
            )

        return None

    # ==================== 4. 成长激励分析 ====================

    def _analyze_growth(
        self,
        diaries: List[Dict],
        keyword_freq: Dict[str, KeywordFrequency],
        emotion_analysis: EmotionAnalysis
    ) -> InsightCategoryResult:
        """分析成长激励：积极变化、希望方向、盲点提示"""
        insights = []

        # 积极变化检测
        change_insight = self._detect_positive_change(diaries)
        if change_insight:
            insights.append(change_insight)

        # 希望方向检测（新兴趣萌芽）
        hope_insight = self._detect_hope_direction(keyword_freq)
        if hope_insight:
            insights.append(hope_insight)

        # 盲点提示
        blindspot_insight = self._detect_blind_spot(diaries)
        if blindspot_insight:
            insights.append(blindspot_insight)

        # 如果没有负面洞察，给一个鼓励
        if not insights:
            insights.append(DeepInsight(
                category=InsightCategory.GROWTH,
                sub_type=InsightSubType.POSITIVE_CHANGE,
                title="持续记录",
                insight=f"你已坚持记录{len(diaries)}篇日记，持续的自我觉察本身就是成长",
                evidence=[f"共{len(diaries)}篇日记"],
                severity=SeverityLevel.INFO,
                icon="🌱",
                confidence=0.9
            ))

        # 生成 highlight
        highlight = None
        if insights:
            highlight = insights[0].insight[:50] + "..." if len(insights[0].insight) > 50 else insights[0].insight

        return InsightCategoryResult(
            category=InsightCategory.GROWTH,
            category_name="成长激励",
            category_icon="🌱",
            insights=insights,
            highlight=highlight
        )

    def _detect_positive_change(self, diaries: List[Dict]) -> Optional[DeepInsight]:
        """检测积极变化"""
        if len(diaries) < 20:
            return None

        # 分段：前半 vs 后半
        mid = len(diaries) // 2
        early_diaries = diaries[:mid]
        late_diaries = diaries[mid:]

        # 检查负面→正面的关键词变化
        for negative, positive in self.POSITIVE_TRANSITIONS.items():
            early_negative = sum(
                1 for d in early_diaries
                if negative in (d.get("cleaned_text", "") or d.get("raw_text", ""))
            )
            late_negative = sum(
                1 for d in late_diaries
                if negative in (d.get("cleaned_text", "") or d.get("raw_text", ""))
            )
            late_positive = sum(
                1 for d in late_diaries
                if positive in (d.get("cleaned_text", "") or d.get("raw_text", ""))
            )

            # 负面减少，正面增加
            if late_negative < early_negative and late_positive > 0:
                return DeepInsight(
                    category=InsightCategory.GROWTH,
                    sub_type=InsightSubType.POSITIVE_CHANGE,
                    title="情绪转变",
                    insight=f"早期常写「{negative}」，近期开始写「{positive}」——你在成长",
                    evidence=[
                        f"前半段「{negative}」{early_negative}次，后半段{late_negative}次",
                        f"「{positive}」出现{late_positive}次"
                    ],
                    severity=SeverityLevel.INFO,
                    icon="📈",
                    confidence=0.75
                )

        # 情绪分数变化
        early_avg = sum(d.get("emotion_score", 5) for d in early_diaries) / len(early_diaries)
        late_avg = sum(d.get("emotion_score", 5) for d in late_diaries) / len(late_diaries)

        if late_avg > early_avg + 0.5:
            return DeepInsight(
                category=InsightCategory.GROWTH,
                sub_type=InsightSubType.POSITIVE_CHANGE,
                title="情绪提升",
                insight=f"近期情绪平均{late_avg:.1f}分，比早期{early_avg:.1f}分提升{(late_avg-early_avg):.1f}——状态在好转",
                evidence=[f"前半段平均{early_avg:.1f}", f"后半段平均{late_avg:.1f}"],
                severity=SeverityLevel.INFO,
                icon="📈",
                confidence=0.8
            )

        return None

    def _detect_hope_direction(self, keyword_freq: Dict[str, KeywordFrequency]) -> Optional[DeepInsight]:
        """检测希望方向（新兴趣萌芽）"""
        # 找出最近首次出现的关键词
        new_keywords = []
        for kw, freq in keyword_freq.items():
            if freq.count >= 2 and freq.first_seen:
                # 检查是否是近期出现（简单的判断）
                new_keywords.append((kw, freq.count, freq.avg_emotion))

        # 按情绪关联排序，找正面情绪的新兴趣
        positive_new = [
            (kw, count, emotion)
            for kw, count, emotion in new_keywords
            if emotion > 6  # 高情绪关联
        ]

        if positive_new:
            kw, count, emotion = positive_new[0]
            return DeepInsight(
                category=InsightCategory.GROWTH,
                sub_type=InsightSubType.HOPE_DIRECTION,
                title="新兴趣萌芽",
                insight=f"近期开始提及「{kw}」，关联情绪{emotion:.1f}分——新的兴趣正在萌芽",
                evidence=[f"{kw}出现{count}次", f"平均情绪{emotion:.1f}"],
                severity=SeverityLevel.INFO,
                icon="🌟",
                confidence=0.7
            )

        return None

    def _detect_blind_spot(self, diaries: List[Dict]) -> Optional[DeepInsight]:
        """检测盲点（完全未提及的基础需求）"""
        all_text = " ".join([
            d.get("cleaned_text", "") or d.get("raw_text", "")
            for d in diaries
        ])

        missing_needs = []
        for need in self.BASIC_NEED_KEYWORDS:
            if need not in all_text:
                missing_needs.append(need)

        if missing_needs:
            return DeepInsight(
                category=InsightCategory.GROWTH,
                sub_type=InsightSubType.BLIND_SPOT,
                title="关注盲点",
                insight=f"近{len(diaries)}篇日记从未提及「{missing_needs[0]}」——也许你忽视了自我关怀",
                evidence=[f"{missing_needs[0]}未提及"],
                severity=SeverityLevel.INFO,
                suggestion="建议：关注这个领域，写一写相关的内容",
                icon="💡",
                confidence=0.65
            )

        return None

    # ==================== 辅助分析方法 ====================

    def _analyze_writing_time(self, diaries: List[Dict]) -> WritingTimeDistribution:
        """分析写作时间分布"""
        dist = WritingTimeDistribution()

        for diary in diaries:
            created_at = diary.get("created_at")
            if not created_at:
                continue

            # 处理时间格式
            if isinstance(created_at, str):
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except:
                    continue
            elif isinstance(created_at, datetime):
                dt = created_at
            else:
                continue

            hour = dt.hour

            if 6 <= hour < 12:
                dist.morning += 1
            elif 12 <= hour < 18:
                dist.afternoon += 1
            elif 18 <= hour < 21:
                dist.evening += 1
            elif 21 <= hour < 24:
                dist.night += 1
            else:
                dist.late_night += 1

        dist.total = dist.morning + dist.afternoon + dist.evening + dist.night + dist.late_night

        # 找出主导时间段
        periods = {
            "morning": dist.morning,
            "afternoon": dist.afternoon,
            "evening": dist.evening,
            "night": dist.night,
            "late_night": dist.late_night
        }

        if dist.total >= 10:
            dominant = max(periods.items(), key=lambda x: x[1])
            if dominant[1] > dist.total * 0.4:  # 超过40%
                dist.dominant_period = dominant[0]
                persona_name, _ = self.WRITING_PERSONAS.get(dominant[0], ("记录者", ""))
                dist.persona_name = persona_name

        return dist

    def _analyze_emotion(self, diaries: List[Dict]) -> EmotionAnalysis:
        """分析情绪"""
        scores = [d.get("emotion_score", 5) for d in diaries if d.get("emotion_score")]

        if not scores:
            return EmotionAnalysis()

        avg = sum(scores) / len(scores)

        # 计算 baseline（假设用全部数据的历史平均作为baseline）
        baseline = avg  # 简化处理，实际应该用更长时间段的历史数据

        # 计算波动性（标准差）
        if len(scores) > 1:
            variance = sum((s - avg) ** 2 for s in scores) / len(scores)
            volatility = variance ** 0.5
        else:
            volatility = 0

        # 计算偏离
        deviation = avg - baseline

        # 获取主导情绪
        emotions = [d.get("emotion", "") for d in diaries if d.get("emotion")]
        if emotions:
            emotion_counter = Counter(emotions)
            dominant = emotion_counter.most_common(1)[0][0]
        else:
            dominant = None

        # 判断趋势（简单：后半段 vs 前半段）
        mid = len(scores) // 2
        early_avg = sum(scores[:mid]) / mid if mid > 0 else avg
        late_avg = sum(scores[mid:]) / (len(scores) - mid) if len(scores) > mid else avg

        if late_avg > early_avg + 0.3:
            trend = "improving"
        elif late_avg < early_avg - 0.3:
            trend = "declining"
        else:
            trend = "stable"

        return EmotionAnalysis(
            average_score=round(avg, 2),
            baseline_score=round(baseline, 2),
            deviation=round(deviation, 2),
            volatility=round(volatility, 2),
            dominant_emotion=dominant,
            trend=trend
        )

    def _analyze_keywords(self, diaries: List[Dict]) -> Dict[str, KeywordFrequency]:
        """分析关键词频率"""
        keyword_data = defaultdict(lambda: KeywordFrequency(keyword="", count=0))

        for diary in diaries:
            text = diary.get("cleaned_text", "") or diary.get("raw_text", "")
            emotion_score = diary.get("emotion_score", 5)
            created_at = diary.get("created_at")

            # 提取关键词（简单分词，实际可以用更好的NLP）
            words = re.findall(r'\w+', text)
            for word in words:
                if len(word) >= 2:  # 至少2个字
                    kf = keyword_data[word]
                    kf.keyword = word
                    kf.count += 1
                    kf.avg_emotion = (kf.avg_emotion * (kf.count - 1) + emotion_score) / kf.count

                    if created_at:
                        date_str = str(created_at)[:10]
                        if not kf.first_seen:
                            kf.first_seen = date_str
                        kf.last_seen = date_str

        # 只返回出现>=3次的关键词
        return {
            k: v for k, v in keyword_data.items()
            if v.count >= 3
        }

    def _analyze_topics(self, diaries: List[Dict]) -> Dict[str, TopicDistribution]:
        """分析话题分布"""
        topic_data = defaultdict(lambda: TopicDistribution(topic="", count=0))

        for diary in diaries:
            topics = diary.get("topics", [])
            if isinstance(topics, str):
                try:
                    topics = json.loads(topics)
                except:
                    topics = []

            emotion_score = diary.get("emotion_score", 5)

            for topic in topics:
                if topic:
                    td = topic_data[topic]
                    td.topic = topic
                    td.count += 1
                    td.avg_emotion = (td.avg_emotion * (td.count - 1) + emotion_score) / td.count

        # 计算占比
        total = sum(td.count for td in topic_data.values())
        for td in topic_data.values():
            td.percentage = round(td.count / total * 100, 1) if total > 0 else 0

        return topic_data

    # ==================== 其他辅助方法 ====================

    def _period_name(self, period: str) -> str:
        """时间段中文名称"""
        names = {
            "morning": "早晨",
            "afternoon": "午后",
            "evening": "晚间",
            "night": "深夜",
            "late_night": "凌晨"
        }
        return names.get(period, period)

    def _generate_overall_summary(self, categories: List[InsightCategoryResult]) -> str:
        """生成整体摘要"""
        # 检查是否有风险预警
        risk_category = next(
            (c for c in categories if c.category == InsightCategory.RISK_ALERT),
            None
        )

        if risk_category and risk_category.insights:
            alert_count = sum(1 for i in risk_category.insights if i.severity == SeverityLevel.ALERT)
            if alert_count > 0:
                return "近期有些需要关注的地方，建议查看风险预警"

        # 检查成长
        growth_category = next(
            (c for c in categories if c.category == InsightCategory.GROWTH),
            None
        )

        if growth_category and growth_category.insights:
            return "总体来看，你在成长，继续记录会让你更好地认识自己"

        return "持续记录日记，你会发现更多关于自己的洞察"

    def _empty_response(self, days: int) -> DeepInsightResponse:
        """返回空响应"""
        return DeepInsightResponse(
            categories=[
                InsightCategoryResult(
                    category=InsightCategory.SELF_KNOWLEDGE,
                    category_name="自我认知",
                    category_icon="🪞",
                    insights=[],
                    highlight="日记数量不足，无法分析"
                ),
                InsightCategoryResult(
                    category=InsightCategory.LIFE_STATE,
                    category_name="生活状态",
                    category_icon="🌿",
                    insights=[]
                ),
                InsightCategoryResult(
                    category=InsightCategory.RISK_ALERT,
                    category_name="风险预警",
                    category_icon="⚠️",
                    insights=[]
                ),
                InsightCategoryResult(
                    category=InsightCategory.GROWTH,
                    category_name="成长激励",
                    category_icon="🌱",
                    insights=[]
                )
            ],
            overall_summary="日记数量不足，需要更多记录才能生成深度洞察",
            stats_context={"total_diaries": 0, "analysis_period_days": days},
            generated_at=datetime.now().isoformat(),
            analysis_period_days=days
        )


# 单例实例
insight_analyzer = InsightAnalyzer()