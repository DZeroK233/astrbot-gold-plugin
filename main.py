from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Helper to get config values
def get_config(context, key, default=None):
    try:
        cfg = getattr(context, "config", None)
        if isinstance(cfg, dict):
            return cfg.get(key, default)
    except Exception:
        pass
    return default

@register("goldprice", "RC-CHN", "招商银行黄金行情查询插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.scheduler = AsyncIOScheduler()

    async def initialize(self):
        """Initialize plugin and schedule daily gold price sending if enabled."""
        enable = get_config(self.context, "enable_daily_send", False)
        send_time = get_config(self.context, "daily_send_time", "08:00")
        if enable:
            try:
                hour, minute = map(int, send_time.split(":"))
                trigger = CronTrigger(hour=hour, minute=minute)
                self.scheduler.add_job(self._daily_send_job, trigger)
                self.scheduler.start()
                logger.info(f"Scheduled daily gold price send at {send_time}")
            except Exception as e:
                logger.error(f"Failed to schedule daily gold send: {e}")
        else:
            logger.info("Daily gold send not enabled in config.")
    
    async def _daily_send_job(self):
        """Fetch gold price and send to target channel defined in config."""
        import aiohttp
        import os
        url = "https://m.cmbchina.com/api/rate/gold"
        timeout = aiohttp.ClientTimeout(total=10)
        proxy = os.environ.get('http_proxy') or os.environ.get('HTTP_PROXY')
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, proxy=proxy) as response:
                    response.raise_for_status()
                    data = await response.json()
            result = "=== 招商银行黄金行情 ===\n"
            result += f"更新时间: {data['body']['time']}\n\n"
            for item in data['body']['data']:
                if item['curPrice'] != '0':
                    result += f"品种: {item['variety']}\n"
                    result += f"当前价: {item['curPrice']}\n"
                    result += f"涨跌幅: {item['upDown']}\n"
                    result += f"最高价: {item['high']}\n"
                    result += f"最低价: {item['low']}\n\n"
            target = get_config(self.context, "daily_send_target", "#general")
            logger.info(f"[Daily Gold] Sending to {target}:\n{result}")
        except Exception as e:
            logger.error(f"Daily gold fetch failed: {e}")
    
    # 注册指令的装饰器。指令名为 gold。注册成功后，发送 `/gold` 就会触发这个指令
    @filter.command("gold")
    async def gold(self, event: AstrMessageEvent):
        """查询招商银行黄金实时行情"""
        import aiohttp
        
        try:
            import os
            url = "https://m.cmbchina.com/api/rate/gold"
            timeout = aiohttp.ClientTimeout(total=10)
            proxy = os.environ.get('http_proxy') or os.environ.get('HTTP_PROXY')
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, proxy=proxy) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    result = "=== 招商银行黄金行情 ===\n"
                    result += f"更新时间: {data['body']['time']}\n\n"
                    
                    for item in data['body']['data']:
                        if item['curPrice'] != '0':
                            result += f"品种: {item['variety']}\n"
                            result += f"当前价: {item['curPrice']}\n"
                            result += f"涨跌幅: {item['upDown']}\n"
                            result += f"最高价: {item['high']}\n"
                            result += f"最低价: {item['low']}\n\n"
                    
                    yield event.plain_result(result)
                    
        except Exception as e:
            yield event.plain_result(f"查询黄金行情失败: {str(e)}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
