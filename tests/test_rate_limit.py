import time
from collections import defaultdict

import pytest

from tg_signer.config import MatchConfig
from tg_signer.core import UserMonitor, UserMonitorContext


class TestRateLimit:
    """测试监控发言频率限制功能"""

    @pytest.fixture
    def monitor(self):
        """创建一个UserMonitor实例用于测试"""
        monitor = UserMonitor(
            task_name="test_monitor",
            workdir="/tmp/test_monitor"
        )
        monitor.context = UserMonitorContext(
            last_message_times=defaultdict(float),
            global_last_message_time=None,
        )
        return monitor

    def test_rate_limit_disabled(self, monitor):
        """测试未启用频率限制时应该始终允许发送"""
        match_cfg = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test",
            rate_limit_enabled=False,
        )

        # 应该允许连续发送
        assert monitor.should_send_message(match_cfg, 123) is True
        assert monitor.should_send_message(match_cfg, 123) is True
        assert monitor.should_send_message(match_cfg, 123) is True

    def test_rate_limit_per_chat(self, monitor):
        """测试按聊天分别限制"""
        match_cfg = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test",
            rate_limit_enabled=True,
            rate_limit_seconds=2,
            rate_limit_per_chat=True,
        )

        chat_id_1 = 123
        chat_id_2 = 456

        # 第一次发送应该成功
        assert monitor.should_send_message(match_cfg, chat_id_1) is True

        # 立即再次发送到同一聊天应该被限制
        assert monitor.should_send_message(match_cfg, chat_id_1) is False

        # 发送到不同聊天应该成功
        assert monitor.should_send_message(match_cfg, chat_id_2) is True

        # 等待超过限制时间后应该可以再次发送
        time.sleep(2.1)
        assert monitor.should_send_message(match_cfg, chat_id_1) is True

    def test_rate_limit_global(self, monitor):
        """测试全局频率限制"""
        match_cfg = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test",
            rate_limit_enabled=True,
            rate_limit_seconds=2,
            rate_limit_per_chat=False,  # 全局限制
        )

        chat_id_1 = 123
        chat_id_2 = 456

        # 第一次发送应该成功
        assert monitor.should_send_message(match_cfg, chat_id_1) is True

        # 立即发送到不同聊天也应该被限制（全局限制）
        assert monitor.should_send_message(match_cfg, chat_id_2) is False

        # 等待超过限制时间后应该可以发送到任何聊天
        time.sleep(2.1)
        assert monitor.should_send_message(match_cfg, chat_id_2) is True

    def test_rate_limit_seconds_default(self):
        """测试频率限制默认值"""
        match_cfg = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test",
            rate_limit_enabled=True,
        )

        # 默认应该是60秒
        assert match_cfg.rate_limit_seconds == 60
        assert match_cfg.rate_limit_per_chat is True

    def test_rate_limit_custom_seconds(self, monitor):
        """测试自定义频率限制时间"""
        match_cfg = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test",
            rate_limit_enabled=True,
            rate_limit_seconds=1,
            rate_limit_per_chat=True,
        )

        # 第一次发送应该成功
        assert monitor.should_send_message(match_cfg, 123) is True

        # 立即再次发送应该被限制
        assert monitor.should_send_message(match_cfg, 123) is False

        # 等待1秒后应该可以发送
        time.sleep(1.1)
        assert monitor.should_send_message(match_cfg, 123) is True

    def test_rate_limit_multiple_configs(self, monitor):
        """测试多个配置项的频率限制互不干扰"""
        match_cfg_1 = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="test1",
            rate_limit_enabled=True,
            rate_limit_seconds=2,
            rate_limit_per_chat=True,
        )

        match_cfg_2 = MatchConfig(
            chat_id=456,
            rule="exact",
            rule_value="test2",
            rate_limit_enabled=True,
            rate_limit_seconds=2,
            rate_limit_per_chat=True,
        )

        # 第一个配置发送到chat 123
        assert monitor.should_send_message(match_cfg_1, 123) is True
        assert monitor.should_send_message(match_cfg_1, 123) is False

        # 第二个配置发送到chat 456应该不受影响
        assert monitor.should_send_message(match_cfg_2, 456) is True
        assert monitor.should_send_message(match_cfg_2, 456) is False

    def test_rate_limit_username_chat_id(self, monitor):
        """测试使用用户名作为chat_id的频率限制"""
        match_cfg = MatchConfig(
            chat_id="@testuser",
            rule="exact",
            rule_value="test",
            rate_limit_enabled=True,
            rate_limit_seconds=2,
            rate_limit_per_chat=True,
        )

        chat_username = "@testuser"

        # 第一次发送应该成功
        assert monitor.should_send_message(match_cfg, chat_username) is True

        # 立即再次发送应该被限制
        assert monitor.should_send_message(match_cfg, chat_username) is False

        # 等待后应该可以发送
        time.sleep(2.1)
        assert monitor.should_send_message(match_cfg, chat_username) is True
