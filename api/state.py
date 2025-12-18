"""
Conversation State Management

核心原则：上下文是系统的一等公民，不依赖 LangChain Memory
参考: docs/memory.md
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading
import uuid


@dataclass
class Turn:
    """单轮对话 - 冷数据，用于 Debug/回放"""
    role: str  # "user" | "assistant" | "tool"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    cape_id: Optional[str] = None


@dataclass
class Summary:
    """语义摘要 - 热数据，LLM 主要上下文来源"""
    content: str
    covers_turns: List[int]  # 覆盖的 turn 索引
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Fact:
    """稳定事实 - 长期记忆"""
    key: str
    value: str
    source: str = "extracted"  # "extracted" | "user_stated" | "inferred"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Task:
    """当前任务 - 对齐 Agent 行为"""
    id: str
    goal: str
    status: str = "active"  # "active" | "done" | "paused"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationState:
    """完整对话状态"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    turns: List[Turn] = field(default_factory=list)
    summaries: List[Summary] = field(default_factory=list)
    facts: List[Fact] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)

    def add_turn(self, role: str, content: str, cape_id: Optional[str] = None) -> Turn:
        """添加一轮对话"""
        turn = Turn(role=role, content=content, cape_id=cape_id)
        self.turns.append(turn)
        self.last_active = datetime.now()
        return turn

    def add_tool_turn(self, tool_name: str, result: str) -> Turn:
        """添加工具调用结果"""
        return self.add_turn("tool", f"[{tool_name}] {result}")

    def get_recent_turns(self, n: int = 5) -> List[Turn]:
        """获取最近 N 轮对话"""
        return self.turns[-n:] if self.turns else []

    def get_latest_summary(self) -> Optional[str]:
        """获取最新摘要"""
        return self.summaries[-1].content if self.summaries else None

    def get_all_summaries(self, limit: int = 3) -> List[str]:
        """获取多条摘要"""
        return [s.content for s in self.summaries[-limit:]]

    def add_summary(self, content: str, covers_turns: List[int]) -> Summary:
        """添加摘要"""
        summary = Summary(content=content, covers_turns=covers_turns)
        self.summaries.append(summary)
        return summary

    def add_fact(self, key: str, value: str, source: str = "extracted") -> Fact:
        """添加或更新事实"""
        # 更新已存在的 fact
        for fact in self.facts:
            if fact.key == key:
                fact.value = value
                fact.source = source
                return fact
        # 添加新 fact
        fact = Fact(key=key, value=value, source=source)
        self.facts.append(fact)
        return fact

    def get_fact(self, key: str) -> Optional[str]:
        """获取事实值"""
        for fact in self.facts:
            if fact.key == key:
                return fact.value
        return None

    def add_task(self, goal: str) -> Task:
        """添加任务"""
        task = Task(id=str(uuid.uuid4())[:8], goal=goal)
        self.tasks.append(task)
        return task

    def complete_task(self, task_id: str) -> bool:
        """完成任务"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = "done"
                return True
        return False

    def get_active_tasks(self) -> List[Task]:
        """获取活跃任务"""
        return [t for t in self.tasks if t.status == "active"]

    def get_unsummarized_turn_count(self) -> int:
        """获取未被摘要覆盖的轮次数"""
        if not self.summaries:
            return len(self.turns)
        covered = set()
        for s in self.summaries:
            covered.update(s.covers_turns)
        return len(self.turns) - len(covered)

    def to_dict(self) -> dict:
        """转换为字典（用于 Debug/序列化）"""
        return {
            "session_id": self.session_id,
            "turn_count": len(self.turns),
            "summary_count": len(self.summaries),
            "facts": {f.key: f.value for f in self.facts},
            "active_tasks": [t.goal for t in self.get_active_tasks()],
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
        }


class StateManager:
    """会话状态管理器 - 线程安全的内存存储"""

    def __init__(self, max_sessions: int = 1000, ttl_hours: int = 24):
        self._states: Dict[str, ConversationState] = {}
        self._lock = threading.Lock()
        self.max_sessions = max_sessions
        self.ttl = timedelta(hours=ttl_hours)

    def get_or_create(self, session_id: Optional[str] = None) -> ConversationState:
        """获取或创建会话状态"""
        with self._lock:
            # 尝试获取已存在的会话
            if session_id and session_id in self._states:
                state = self._states[session_id]
                state.last_active = datetime.now()
                return state

            # 清理过期会话
            self._cleanup_expired()

            # 创建新会话
            new_session_id = session_id or str(uuid.uuid4())
            state = ConversationState(session_id=new_session_id)
            self._states[new_session_id] = state
            return state

    def get(self, session_id: str) -> Optional[ConversationState]:
        """获取会话状态（不创建）"""
        with self._lock:
            state = self._states.get(session_id)
            if state:
                state.last_active = datetime.now()
            return state

    def update(self, state: ConversationState):
        """更新会话状态"""
        with self._lock:
            state.last_active = datetime.now()
            self._states[state.session_id] = state

    def delete(self, session_id: str) -> bool:
        """删除会话"""
        with self._lock:
            if session_id in self._states:
                del self._states[session_id]
                return True
            return False

    def list_sessions(self) -> List[dict]:
        """列出所有会话"""
        with self._lock:
            return [state.to_dict() for state in self._states.values()]

    def get_session_count(self) -> int:
        """获取会话数量"""
        with self._lock:
            return len(self._states)

    def _cleanup_expired(self):
        """清理过期会话"""
        now = datetime.now()
        expired = [
            sid for sid, state in self._states.items()
            if now - state.last_active > self.ttl
        ]
        for sid in expired:
            del self._states[sid]

        # LRU: 超过限制时删除最老的
        while len(self._states) >= self.max_sessions:
            oldest = min(
                self._states.items(),
                key=lambda x: x[1].last_active
            )
            del self._states[oldest[0]]

    def clear_all(self):
        """清除所有会话（用于测试）"""
        with self._lock:
            self._states.clear()


# 全局单例
state_manager = StateManager()
