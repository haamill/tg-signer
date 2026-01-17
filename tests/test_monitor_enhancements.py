from collections import defaultdict
from datetime import datetime

import pytest

from tg_signer.config import MatchConfig, MonitorConfig
from tg_signer.core import UserMonitor, UserMonitorContext


class TestMonitorEnhancements:
    """测试监控增强功能"""

    @pytest.fixture
    def monitor(self):
        """创建一个UserMonitor实例用于测试"""
        monitor = UserMonitor(
            task_name="test_monitor",
            workdir="/tmp/test_monitor_enhancements"
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
            daily_message_count=0,
            last_checkin_date=None,
        )
        return monitor

    def test_check_and_reset_daily_count_new_day(self, monitor):
        """测试新的一天时重置计数"""
        monitor.context.daily_message_count = 50
        monitor.context.last_checkin_date = "2024-01-01"

        is_new_day = monitor.check_and_reset_daily_count()

        assert is_new_day is True
        assert monitor.context.daily_message_count == 0
        assert monitor.context.last_checkin_date == datetime.now().strftime("%Y-%m-%d")

    def test_check_and_reset_daily_count_same_day(self, monitor):
        """测试同一天不重置计数"""
        today = datetime.now().strftime("%Y-%m-%d")
        monitor.context.daily_message_count = 50
        monitor.context.last_checkin_date = today

        is_new_day = monitor.check_and_reset_daily_count()

        assert is_new_day is False
        assert monitor.context.daily_message_count == 50
        assert monitor.context.last_checkin_date == today

    def test_can_send_today_below_limit(self, monitor):
        """测试在限制以下可以发送"""
        monitor.context.daily_message_count = 50
        monitor.config.daily_message_limit = 200

        assert monitor.can_send_today() is True

    def test_can_send_today_at_limit(self, monitor):
        """测试达到限制时不能发送"""
        monitor.context.daily_message_count = 200
        monitor.config.daily_message_limit = 200

        assert monitor.can_send_today() is False

    def test_can_send_today_above_limit(self, monitor):
        """测试超过限制时不能发送"""
        monitor.context.daily_message_count = 250
        monitor.config.daily_message_limit = 200

        assert monitor.can_send_today() is False

    def test_can_send_today_no_limit(self, monitor):
        """测试没有限制时总是可以发送"""
        monitor.context.daily_message_count = 1000
        monitor.config.daily_message_limit = 0  # 0表示不限制

        assert monitor.can_send_today() is True

    def test_increment_daily_count(self, monitor):
        """测试增加每日计数"""
        monitor.context.daily_message_count = 10

        monitor.increment_daily_count()

        assert monitor.context.daily_message_count == 11

        monitor.increment_daily_count()
        monitor.increment_daily_count()

        assert monitor.context.daily_message_count == 13

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
        monitor.context.daily_message_count = 150

        # 触发检查
        monitor.check_and_reset_daily_count()

        # 验证计数已重置
        assert monitor.context.daily_message_count == 0
        assert monitor.context.last_checkin_date == datetime.now().strftime("%Y-%m-%d")

    def test_daily_count_persists_same_day(self, monitor):
        """测试同一天内计数持续"""
        today = datetime.now().strftime("%Y-%m-%d")
        monitor.context.last_checkin_date = today
        monitor.context.daily_message_count = 50

        # 增加计数
        for _ in range(10):
            monitor.increment_daily_count()

        # 验证计数累加
        assert monitor.context.daily_message_count == 60

        # 再次检查不应重置
        monitor.check_and_reset_daily_count()
        assert monitor.context.daily_message_count == 60

    def test_message_limit_enforced(self, monitor):
        """测试消息限制被强制执行"""
        monitor.config.daily_message_limit = 5
        monitor.context.daily_message_count = 0

        # 发送5条消息
        for _ in range(5):
            assert monitor.can_send_today() is True
            monitor.increment_daily_count()

        # 第6条应该被拒绝
        assert monitor.can_send_today() is False

    def test_monitor_context_initialization(self, monitor):
        """测试监控上下文初始化"""
        ctx = monitor.ensure_ctx()

        assert isinstance(ctx, UserMonitorContext)
        assert ctx.daily_message_count == 0
        assert ctx.last_checkin_date is None
        assert isinstance(ctx.last_message_times, defaultdict)
        assert ctx.global_last_message_time is None
