from collections import defaultdict
from datetime import datetime

import pytest

from tg_signer.config import MatchConfig, MonitorConfig
from tg_signer.core import UserMonitor, UserMonitorContext


class TestMonitorEnhancements:
    """测试监控增强功能"""

    @pytest.fixture
    def monitor(self, tmp_path):
        """创建一个UserMonitor实例用于测试"""
        monitor = UserMonitor(
            task_name="test_monitor",
            workdir=tmp_path / "test_monitor_enhancements"
        )
        monitor.config = MonitorConfig(
            match_cfgs=[],
            daily_checkin_enabled=True,
            daily_checkin_text="签到",
            daily_message_limit=200,
        )
        monitor.context = UserMonitorContext(
            last_message_times=defaultdict(float),
            global_last_message_time=None,
            daily_message_count=defaultdict(int),
            last_checkin_date=None,
            stopped_chats=set(),
        )
        return monitor

    def test_check_and_reset_daily_count_new_day(self, monitor):
        """测试新的一天时重置计数"""
        monitor.context.daily_message_count[123] = 50
        monitor.context.daily_message_count[456] = 30
        monitor.context.last_checkin_date = "2024-01-01"
        monitor.context.stopped_chats.add(123)

        is_new_day = monitor.check_and_reset_daily_count()

        assert is_new_day is True
        assert len(monitor.context.daily_message_count) == 0
        assert len(monitor.context.stopped_chats) == 0
        assert monitor.context.last_checkin_date == datetime.now().strftime("%Y-%m-%d")

    def test_check_and_reset_daily_count_same_day(self, monitor):
        """测试同一天不重置计数"""
        today = datetime.now().strftime("%Y-%m-%d")
        monitor.context.daily_message_count[123] = 50
        monitor.context.last_checkin_date = today

        is_new_day = monitor.check_and_reset_daily_count()

        assert is_new_day is False
        assert monitor.context.daily_message_count[123] == 50
        assert monitor.context.last_checkin_date == today

    def test_can_send_today_below_limit(self, monitor):
        """测试在限制以下可以发送"""
        chat_id = 123
        monitor.context.daily_message_count[chat_id] = 50
        monitor.config.daily_message_limit = 200

        assert monitor.can_send_today(chat_id) is True

    def test_can_send_today_at_limit(self, monitor):
        """测试达到限制时不能发送"""
        chat_id = 123
        monitor.context.daily_message_count[chat_id] = 200
        monitor.config.daily_message_limit = 200

        assert monitor.can_send_today(chat_id) is False

    def test_can_send_today_above_limit(self, monitor):
        """测试超过限制时不能发送"""
        chat_id = 123
        monitor.context.daily_message_count[chat_id] = 250
        monitor.config.daily_message_limit = 200

        assert monitor.can_send_today(chat_id) is False

    def test_can_send_today_no_limit(self, monitor):
        """测试没有限制时总是可以发送"""
        chat_id = 123
        monitor.context.daily_message_count[chat_id] = 1000
        monitor.config.daily_message_limit = 0  # 0表示不限制

        assert monitor.can_send_today(chat_id) is True

    def test_can_send_today_per_chat(self, monitor):
        """测试每个聊天独立计数"""
        chat_id_1 = 123
        chat_id_2 = 456
        monitor.context.daily_message_count[chat_id_1] = 200
        monitor.context.daily_message_count[chat_id_2] = 50
        monitor.config.daily_message_limit = 200

        # chat_id_1 已达限制
        assert monitor.can_send_today(chat_id_1) is False
        # chat_id_2 未达限制
        assert monitor.can_send_today(chat_id_2) is True

    def test_increment_daily_count(self, monitor):
        """测试增加每日计数"""
        chat_id = 123
        monitor.context.daily_message_count[chat_id] = 10
        monitor.config.daily_message_limit = 0  # 不限制

        monitor.increment_daily_count(chat_id)

        assert monitor.context.daily_message_count[chat_id] == 11

        monitor.increment_daily_count(chat_id)
        monitor.increment_daily_count(chat_id)

        assert monitor.context.daily_message_count[chat_id] == 13

    def test_increment_daily_count_stops_at_limit(self, monitor):
        """测试达到限制时添加到停止列表"""
        chat_id = 123
        monitor.context.daily_message_count[chat_id] = 199
        monitor.config.daily_message_limit = 200

        monitor.increment_daily_count(chat_id)

        assert monitor.context.daily_message_count[chat_id] == 200
        assert chat_id in monitor.context.stopped_chats

    def test_increment_daily_count_multiple_chats(self, monitor):
        """测试多个聊天独立计数"""
        chat_id_1 = 123
        chat_id_2 = 456
        monitor.config.daily_message_limit = 200

        monitor.increment_daily_count(chat_id_1)
        monitor.increment_daily_count(chat_id_1)
        monitor.increment_daily_count(chat_id_2)

        assert monitor.context.daily_message_count[chat_id_1] == 2
        assert monitor.context.daily_message_count[chat_id_2] == 1

    def test_match_config_send_delay_default(self):
        """测试发送延迟默认值"""
        match_cfg = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test",
        )

        # 默认应该是1秒
        assert match_cfg.send_delay_seconds == 1

    def test_match_config_send_delay_custom(self):
        """测试自定义发送延迟"""
        match_cfg = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test",
            send_delay_seconds=5,
        )

        assert match_cfg.send_delay_seconds == 5

    def test_match_config_context_messages_count_default(self):
        """测试上下文消息数量默认值"""
        match_cfg = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test",
        )

        # 默认应该是5条
        assert match_cfg.context_messages_count == 5

    def test_match_config_context_messages_count_custom(self):
        """测试自定义上下文消息数量"""
        match_cfg = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test",
            context_messages_count=10,
        )

        assert match_cfg.context_messages_count == 10

    def test_monitor_config_daily_checkin_enabled_default(self):
        """测试每日签到功能默认关闭"""
        config = MonitorConfig(match_cfgs=[])

        assert config.daily_checkin_enabled is False

    def test_monitor_config_daily_checkin_text_default(self):
        """测试每日签到文本默认值"""
        config = MonitorConfig(
            match_cfgs=[],
            daily_checkin_enabled=True,
        )

        assert config.daily_checkin_text == "签到"

    def test_monitor_config_daily_message_limit_default(self):
        """测试每日消息限制默认值"""
        config = MonitorConfig(match_cfgs=[])

        assert config.daily_message_limit == 200

    def test_monitor_config_custom_values(self):
        """测试自定义配置值"""
        config = MonitorConfig(
            match_cfgs=[],
            daily_checkin_enabled=True,
            daily_checkin_text="每日打卡",
            daily_message_limit=100,
        )

        assert config.daily_checkin_enabled is True
        assert config.daily_checkin_text == "每日打卡"
        assert config.daily_message_limit == 100

    def test_daily_count_reset_on_new_day(self, monitor):
        """测试跨天时计数重置"""
        # 设置为昨天
        monitor.context.last_checkin_date = "2024-01-01"
        monitor.context.daily_message_count[123] = 150
        monitor.context.daily_message_count[456] = 100

        # 触发检查
        monitor.check_and_reset_daily_count()

        # 验证计数已重置
        assert len(monitor.context.daily_message_count) == 0
        assert monitor.context.last_checkin_date == datetime.now().strftime("%Y-%m-%d")

    def test_daily_count_persists_same_day(self, monitor):
        """测试同一天内计数持续"""
        today = datetime.now().strftime("%Y-%m-%d")
        chat_id = 123
        monitor.context.last_checkin_date = today
        monitor.context.daily_message_count[chat_id] = 50

        # 增加计数
        for _ in range(10):
            monitor.increment_daily_count(chat_id)

        # 验证计数累加
        assert monitor.context.daily_message_count[chat_id] == 60

        # 再次检查不应重置
        monitor.check_and_reset_daily_count()
        assert monitor.context.daily_message_count[chat_id] == 60

    def test_message_limit_enforced_per_chat(self, monitor):
        """测试每个聊天的消息限制被独立强制执行"""
        chat_id_1 = 123
        chat_id_2 = 456
        monitor.config.daily_message_limit = 5
        monitor.context.daily_message_count[chat_id_1] = 0
        monitor.context.daily_message_count[chat_id_2] = 0

        # chat_id_1 发送5条消息
        for _ in range(5):
            assert monitor.can_send_today(chat_id_1) is True
            monitor.increment_daily_count(chat_id_1)

        # chat_id_1 第6条应该被拒绝
        assert monitor.can_send_today(chat_id_1) is False
        assert chat_id_1 in monitor.context.stopped_chats

        # chat_id_2 仍然可以发送
        assert monitor.can_send_today(chat_id_2) is True
        monitor.increment_daily_count(chat_id_2)
        assert monitor.context.daily_message_count[chat_id_2] == 1

    def test_monitor_context_initialization(self, monitor):
        """测试监控上下文初始化"""
        ctx = monitor.ensure_ctx()

        assert isinstance(ctx, UserMonitorContext)
        assert isinstance(ctx.daily_message_count, defaultdict)
        assert ctx.last_checkin_date is None
        assert isinstance(ctx.last_message_times, defaultdict)
        assert ctx.global_last_message_time is None
        assert isinstance(ctx.stopped_chats, set)
