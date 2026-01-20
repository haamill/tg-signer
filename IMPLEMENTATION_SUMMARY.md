# Monitor Enhancements - Implementation Summary

## 问题描述 (Problem Statement)

根据用户反馈，monitor功能存在以下三个问题：

1. **每日签到功能未生效**: 启动monitor时，签到消息没有发送到群组
2. **消息限制应该按群组独立**: 每日200条消息的限制应该对每个群组分别计算，而不是全局限制
3. **达到限制后应停止监控**: 当群组达到200条消息限制后，应停止监控该群组以节省大模型资源

## 解决方案 (Solutions Implemented)

### 1. 修复每日签到功能 (Fix Daily Check-in)

**问题分析**:
- 原来的 `perform_daily_checkin()` 函数内部调用了 `check_and_reset_daily_count()`，这会导致签到逻辑混乱
- 在 `run()` 方法中也调用了 `check_and_reset_daily_count()`，造成重复检查

**解决方案**:
- 移除 `perform_daily_checkin()` 内部的 `check_and_reset_daily_count()` 调用
- 只在 `run()` 启动时和 `on_message()` 处理消息时检查日期变更
- 当检测到新的一天时，自动执行签到

**代码变更**:
```python
# 在 run() 方法中
async def run(self, num_of_dialogs=20):
    # ... 其他代码 ...
    async with self.app:
        self.log("开始监控...")
        # 启动时执行一次每日签到检查
        if self.check_and_reset_daily_count():
            await self.perform_daily_checkin()
        await idle()

# 在 on_message() 方法中
async def on_message(self, client, message: Message):
    # 检查并重置每日计数，如果是新的一天则执行签到
    if self.check_and_reset_daily_count():
        await self.perform_daily_checkin()
    # ... 处理消息 ...
```

### 2. 实现按群组独立的消息限制 (Per-Chat Message Limits)

**数据结构变更**:

原来的结构:
```python
daily_message_count: int = 0  # 全局计数
```

新的结构:
```python
daily_message_count: defaultdict[Union[int, str], int]  # 每个聊天独立计数
stopped_chats: set[Union[int, str]]  # 已停止监控的聊天集合
```

**方法签名变更**:

```python
# 原来
def can_send_today(self) -> bool:
    return self.context.daily_message_count < self.config.daily_message_limit

def increment_daily_count(self):
    self.context.daily_message_count += 1

# 现在
def can_send_today(self, chat_id: Union[int, str]) -> bool:
    return self.context.daily_message_count[chat_id] < self.config.daily_message_limit

def increment_daily_count(self, chat_id: Union[int, str]):
    self.context.daily_message_count[chat_id] += 1
    # 检查是否达到限制
    if (self.config.daily_message_limit > 0 and
        self.context.daily_message_count[chat_id] >= self.config.daily_message_limit):
        self.context.stopped_chats.add(chat_id)
        self.log(f"聊天 {chat_id} 已达到每日消息限制，停止监控以节省资源")
```

### 3. 自动停止监控达到限制的群组 (Stop Monitoring Chats at Limit)

**实现方式**:

1. 在 `increment_daily_count()` 中自动将达到限制的群组添加到 `stopped_chats` 集合
2. 在 `on_message()` 开始处检查消息是否来自已停止的群组：

```python
async def on_message(self, client, message: Message):
    # 检查该聊天是否已停止监控
    if message.chat.id in self.context.stopped_chats:
        return  # 直接返回，不处理该消息
    
    # ... 继续处理消息 ...
```

3. 每日重置时，清空 `stopped_chats` 集合，恢复所有群组的监控

## 测试覆盖 (Test Coverage)

### 新增和更新的测试

1. **test_can_send_today_per_chat**: 测试每个聊天独立计数
2. **test_increment_daily_count_stops_at_limit**: 测试达到限制时添加到停止列表
3. **test_increment_daily_count_multiple_chats**: 测试多个聊天独立计数
4. **test_message_limit_enforced_per_chat**: 测试每个聊天的消息限制被独立强制执行
5. **test_monitor_context_initialization**: 测试新字段的初始化

所有63个测试全部通过 ✅

## 向后兼容性 (Backward Compatibility)

⚠️ **重要提示**: 此更改修改了 `UserMonitorContext` 的数据结构，可能影响正在运行的monitor实例。

建议用户：
1. 重启所有正在运行的monitor任务
2. 清空旧的会话数据（如果使用持久化存储）

## 使用示例 (Usage Example)

配置monitor时，功能会自动生效：

```bash
# 启动monitor
tg-signer monitor run my_monitor

# 输出示例：
# [INFO] 执行每日签到，发送文本: 签到
# [INFO] 已向 123456 发送签到消息
# [INFO] 已向 789012 发送签到消息
# ... 处理消息 ...
# [INFO] 今日已向 123456 发送 199 条消息
# [INFO] 今日已向 123456 发送 200 条消息
# [INFO] 聊天 123456 已达到每日消息限制 (200)，停止监控以节省资源
# [INFO] 今日已向 789012 发送 50 条消息  # 群组789012继续监控
```

## 性能影响 (Performance Impact)

- 使用 `defaultdict` 进行按群组计数，性能影响极小
- 使用 `set` 存储已停止的群组，查询时间复杂度为 O(1)
- 每日重置操作只在日期变更时执行一次，不影响运行时性能

## 总结 (Summary)

✅ **问题1**: 每日签到现在会在monitor启动时和每日首次收到消息时自动执行
✅ **问题2**: 每个群组的消息限制完全独立，互不影响
✅ **问题3**: 达到限制的群组会自动停止监控，节省LLM资源

所有改动均通过了单元测试和linting检查。
