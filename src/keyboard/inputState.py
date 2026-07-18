
from enum import Enum, auto

class InputState(Enum):
    """输入状态枚举"""
    IDLE = auto()           # 空闲状态
    RECORDING = auto()      # 正在录音
    RECORDING_TERMINAL = auto()  # 正在录音（终端模式）
    RECORDING_AGENT = auto()  # 正在录音（知识库 Agent 模式）
    RECORDING_SMART = auto()  # 正在录音（智能纠错模式）
    RECORDING_TRANSLATE = auto()  # 正在录音(翻译模式)
    RECORDING_KIMI = auto()     # 正在录音(Kimi润色模式)
    DOUBAO_STREAMING = auto()   # 豆包流式识别中（边说边转）
    PROCESSING = auto()     # 正在处理
    PROCESSING_AGENT = auto()  # 正在处理（知识库 Agent）
    PROCESSING_SMART = auto()  # 正在处理（智能纠错模式）
    PROCESSING_KIMI = auto()    # 正在处理(Kimi润色模式)
    TRANSLATING = auto()    # 正在翻译
    ERROR = auto()          # 错误状态
    WARNING = auto()        # 警告状态（用于录音时长不足等提示）

    @property
    def is_recording(self):
        """检查是否处于录音状态"""
        return self in (
            InputState.RECORDING,
            InputState.RECORDING_TERMINAL,
            InputState.RECORDING_AGENT,
            InputState.RECORDING_SMART,
            InputState.RECORDING_TRANSLATE,
            InputState.RECORDING_KIMI,
            InputState.DOUBAO_STREAMING,
        )
    
    @property
    def can_start_recording(self):
        """检查是否可以开始新的录音（只有 IDLE 状态才能开始）"""
        return self == InputState.IDLE
