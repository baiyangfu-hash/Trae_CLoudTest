"""
间隔重复算法引擎 (FSRS-4.5)
按 FSRS-4.5 标准公式实现，不依赖外部库
"""
import json
import math
from datetime import datetime, timedelta

class FSRSState:
    """FSRS 单词状态"""
    def __init__(self):
        self.due = datetime.now().isoformat()
        self.stability = 0.0      # 记忆稳定性（天）
        self.difficulty = 0.0     # 难度 1~10
        self.elapsed_days = 0     # 距上次复习的天数
        self.scheduled_days = 0   # 计划间隔天数
        self.reps = 0             # 重复次数
        self.lapses = 0           # 遗忘次数
        self.state = 0            # 0=新词, 1=学习中, 2=复习, 3=重新学习
        self.last_review = None   # 上次复习时间 (ISO)

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        if not json_str:
            return cls()
        obj = cls()
        data = json.loads(json_str)
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        return obj

class FSRSEngine:
    """FSRS 间隔重复引擎"""

    # FSRS-4.5 默认参数
    PARAMS = {
        'w': [0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031, 1.6474,
              0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755],
        'request_retention': 0.9,  # 目标保留率 90%
        'maximum_interval': 365,    # 最大间隔 365 天
    }
    DECAY = -0.5
    FACTOR = 19 / 81

    # 评分: 1=重来, 2=困难, 3=一般, 4=简单
    RATING_MAP = {
        'again': 1,
        'hard': 2,
        'good': 3,
        'easy': 4
    }

    def __init__(self):
        self.w = self.PARAMS['w']
        self.request_retention = self.PARAMS['request_retention']
        self.maximum_interval = self.PARAMS['maximum_interval']

    @staticmethod
    def _clamp_difficulty(d):
        return min(10.0, max(1.0, d))

    def init_difficulty(self, rating):
        """初始化难度"""
        return self._clamp_difficulty(self.w[4] - (rating - 3) * self.w[5])

    def init_stability(self, rating):
        """初始化稳定性：again < hard < good < easy"""
        return self.w[rating - 1]

    def next_difficulty(self, difficulty, rating):
        """计算下一个难度（向初始难度均值回归）"""
        d = difficulty - self.w[6] * (rating - 3)
        return self._clamp_difficulty(self.w[7] * self.init_difficulty(3) + (1 - self.w[7]) * d)

    def retrievability(self, elapsed_days, stability):
        """经过 elapsed_days 天后的回忆概率"""
        return math.pow(1 + self.FACTOR * elapsed_days / stability, self.DECAY)

    def next_recall_stability(self, stability, difficulty, retrievability, rating):
        """记得（hard/good/easy）后的新稳定性"""
        hard_penalty = self.w[15] if rating == 2 else 1
        easy_bonus = self.w[16] if rating == 4 else 1
        return stability * (1 + math.exp(self.w[8]) * (11 - difficulty) *
                            math.pow(stability, -self.w[9]) *
                            (math.exp(self.w[10] * (1 - retrievability)) - 1) *
                            hard_penalty * easy_bonus)

    def next_forget_stability(self, stability, difficulty, retrievability):
        """忘记（again）后的新稳定性"""
        s = (self.w[11] * math.pow(difficulty, -self.w[12]) *
             (math.pow(stability + 1, self.w[13]) - 1) *
             math.exp(self.w[14] * (1 - retrievability)))
        return min(s, stability)

    def next_interval(self, stability):
        """计算下一个间隔天数"""
        interval = stability / self.FACTOR * (math.pow(self.request_retention, 1 / self.DECAY) - 1)
        return max(1, min(round(interval), self.maximum_interval))

    def _elapsed_days(self, state, now):
        """距上次复习的天数；旧数据没有 last_review 时用 due - scheduled_days 推算"""
        try:
            if state.last_review:
                last = datetime.fromisoformat(state.last_review)
            else:
                last = datetime.fromisoformat(state.due) - timedelta(days=state.scheduled_days or 0)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, (now - last).total_seconds() / 86400)

    def review(self, state, rating):
        """
        执行一次复习评分
        state: FSRSState 对象
        rating: 'again'|'hard'|'good'|'easy'
        返回: (new_state, due_date)
        """
        rating_val = self.RATING_MAP.get(rating, 3)
        now = datetime.now()

        new_state = FSRSState()
        new_state.reps = state.reps + 1
        new_state.lapses = state.lapses
        new_state.last_review = now.isoformat()

        if state.state == 0:  # 新词
            new_state.elapsed_days = 0
            new_state.stability = self.init_stability(rating_val)
            new_state.difficulty = self.init_difficulty(rating_val)
            if rating_val == 1:
                new_state.state = 0
                new_state.scheduled_days = 0
            else:
                new_state.state = 1
                new_state.scheduled_days = self.next_interval(new_state.stability)
        else:  # 学习中 / 复习 / 重新学习
            # 兼容旧版本算出的异常值（负稳定性、越界难度）
            stability = state.stability if state.stability and state.stability > 0 else max(1.0, float(state.scheduled_days or 1))
            difficulty = self._clamp_difficulty(state.difficulty or self.init_difficulty(3))
            elapsed = self._elapsed_days(state, now)
            r = self.retrievability(elapsed, stability)
            new_state.elapsed_days = round(elapsed)
            new_state.difficulty = self.next_difficulty(difficulty, rating_val)

            if rating_val == 1:  # 重来
                new_state.stability = self.next_forget_stability(stability, difficulty, r)
                new_state.state = 3
                new_state.lapses += 1
                new_state.scheduled_days = 1
            else:
                new_state.stability = self.next_recall_stability(stability, difficulty, r, rating_val)
                new_state.state = 2
                new_state.scheduled_days = self.next_interval(new_state.stability)

        # 计算到期时间
        due = now + timedelta(days=new_state.scheduled_days)
        new_state.due = due.isoformat()

        return new_state, due

    def get_rating_intervals(self, state):
        """
        获取各个评分对应的预计间隔天数
        用于显示在按钮上
        """
        intervals = {}
        for rating_name in self.RATING_MAP:
            new_state, _ = self.review(state, rating_name)
            intervals[rating_name] = new_state.scheduled_days
        return intervals
