import re
from nonebot import on_command, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp import MessageSegment, Message
from omega_miya.utils.Omega_plugin_utils import init_export, init_permission_state
from omega_miya.utils.pixiv_utils import PixivIllust

# Custom plugin usage text
__plugin_name__ = 'Pixiv'
__plugin_usage__ = r'''【Pixiv助手】
查看Pixiv插画, 以及日榜、周榜、月榜

**Permission**
Command & Lv.50
or AuthNode

**AuthNode**
basic

**Usage**
/pixiv [PID]
/pixiv 日榜
/pixiv 周榜
/pixiv 月榜'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
pixiv = on_command(
    'pixiv',
    aliases={'Pixiv'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_permission_state(
        name='pixiv',
        command=True,
        level=50,
        auth_node='basic'),
    permission=GROUP,
    priority=20,
    block=True)


# 修改默认参数处理
@pixiv.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await pixiv.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await pixiv.finish('操作已取消')


@pixiv.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['mode'] = args[0]
    else:
        await pixiv.finish('参数错误QAQ')


@pixiv.got('mode', prompt='你是想看日榜, 周榜, 月榜, 还是作品呢? 想看特定作品的话请输入PixivID~')
async def handle_pixiv(bot: Bot, event: GroupMessageEvent, state: T_State):
    mode = state['mode']
    if mode == '日榜':
        await pixiv.send('稍等, 正在下载图片~')
        rank_result = await PixivIllust.daily_ranking()
        if rank_result.error:
            logger.warning(f"User: {event.user_id} 获取Pixiv Rank失败, {rank_result.info}")
            await pixiv.finish('加载失败, 网络超时QAQ')

        for rank, illust_data in dict(rank_result.result).items():
            rank += 1
            illust_id = illust_data.get('illust_id')
            illust_title = illust_data.get('title')
            illust_uname = illust_data.get('user_name')

            image_result = await PixivIllust(pid=illust_id).pic_2_base64()
            if image_result.success():
                msg = f'【{rank}】「{illust_title}」/「{illust_uname}」'
                img_seg = MessageSegment.image(image_result.result)
                await pixiv.send(Message(img_seg).append(msg))
            else:
                logger.warning(f"下载图片失败, pid: {illust_id}, {image_result.info}")
            if rank >= 10:
                break
    elif mode == '周榜':
        await pixiv.send('稍等, 正在下载图片~')
        rank_result = await PixivIllust.weekly_ranking()
        if rank_result.error:
            logger.warning(f"User: {event.user_id} 获取Pixiv Rank失败, {rank_result.info}")
            await pixiv.finish('加载失败, 网络超时QAQ')

        for rank, illust_data in dict(rank_result.result).items():
            rank += 1
            illust_id = illust_data.get('illust_id')
            illust_title = illust_data.get('title')
            illust_uname = illust_data.get('user_name')

            image_result = await PixivIllust(pid=illust_id).pic_2_base64()
            if image_result.success():
                msg = f'【{rank}】「{illust_title}」/「{illust_uname}」'
                img_seg = MessageSegment.image(image_result.result)
                await pixiv.send(Message(img_seg).append(msg))
            else:
                logger.warning(f"下载图片失败, pid: {illust_id}, {image_result.info}")
            if rank >= 10:
                break
    elif mode == '月榜':
        await pixiv.send('稍等, 正在下载图片~')
        rank_result = await PixivIllust.monthly_ranking()
        if rank_result.error:
            logger.warning(f"User: {event.user_id} 获取Pixiv Rank失败, {rank_result.info}")
            await pixiv.finish('加载失败, 网络超时QAQ')

        for rank, illust_data in dict(rank_result.result).items():
            rank += 1
            illust_id = illust_data.get('illust_id')
            illust_title = illust_data.get('title')
            illust_uname = illust_data.get('user_name')

            image_result = await PixivIllust(pid=illust_id).pic_2_base64()
            if image_result.success():
                msg = f'【{rank}】「{illust_title}」/「{illust_uname}」'
                img_seg = MessageSegment.image(image_result.result)
                await pixiv.send(Message(img_seg).append(msg))
            else:
                logger.warning(f"下载图片失败, pid: {illust_id}, {image_result.info}")
            if rank >= 10:
                break
    elif re.match(r'^\d+$', mode):
        pid = mode
        logger.debug(f'获取Pixiv资源: {pid}.')
        await pixiv.send('稍等, 正在下载图片~')
        # 获取illust
        illust_result = await PixivIllust(pid=pid).pic_2_base64()
        if illust_result.success():
            msg = illust_result.info
            img_seg = MessageSegment.image(illust_result.result)
            # 发送图片和图片信息
            await pixiv.send(Message(img_seg).append(msg))
        else:
            logger.warning(f"User: {event.user_id} 获取Pixiv资源失败, 网络超时或 {pid} 不存在, {illust_result.info}")
            await pixiv.send('加载失败, 网络超时或没有这张图QAQ')
    else:
        await pixiv.reject('你输入的命令好像不对呢……请输入"月榜"、"周榜"、"日榜"或者PixivID, 取消命令请发送【取消】:')
