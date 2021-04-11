import asyncio
import time
import random
from nonebot import logger, require, get_driver, get_bots
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_Base import DBSubscription, DBHistory, DBTable
from .utils import get_live_info, get_user_info, pic_2_base64, verify_cookies
from .utils import ENABLE_BILI_CHECK_POOL_MODE, ENABLE_PROXY


# 初始化直播间标题, 状态
live_title = {}
live_status = {}
live_up_name = {}

# 检查池模式使用的检查队列
checking_pool = []


async def init_live_info():
    global live_title
    global live_status
    global live_up_name

    # 定义函数用于初始化直播间信息
    async def __init_live_info(room_id: int):
        try:
            # 获取直播间信息
            __res = await get_live_info(room_id=room_id)
            if not __res.success():
                logger.opt(colors=True).error(
                    f'init_live_info: <r>获取直播间信息失败</r>, room_id: {room_id}, error: {__res.info}')
                return
            live_info = __res.result
            up_uid = __res.result.get('uid')
            __res = await get_user_info(user_uid=up_uid)
            if not __res.success():
                logger.opt(colors=True).error(
                    f'init_live_info: <r>获取直播间UP用户信息失败</r>, room_id: {room_id}, error: {__res.info}')
                return
            up_name = __res.result.get('name')

            # 直播状态放入live_status全局变量中
            live_status[room_id] = int(live_info['status'])

            # 直播间标题放入live_title全局变量中
            live_title[room_id] = str(live_info['title'])

            # 直播间up名称放入live_up_name全局变量中
            live_up_name[room_id] = str(up_name)

            logger.opt(colors=True).info(f"init_live_info: <lc>初始化直播间 {room_id}/{up_name} ... </lc>"
                                         f"<g>status: {live_info['status']}</g>")
        except Exception as _e:
            logger.opt(colors=True).error(f'init_live_info: <r>初始化直播间 {room_id} 失败</r>, <y>error: {repr(_e)}</y>')
            return

    if ENABLE_BILI_CHECK_POOL_MODE:
        logger.opt(colors=True).info('<g>Bilibili 检查池模式: </g><ly>已启用!</ly>')
    else:
        logger.opt(colors=True).info('<g>Bilibili 检查池模式: </g><ly>已禁用!</ly>')

    _res = await verify_cookies()
    if _res.success():
        logger.opt(colors=True).info(f'<g>Bilibili 已登录!</g> 当前用户: {_res.result}')
    else:
        logger.opt(colors=True).warning(f'<r>Bilibili 登录状态异常: {_res.info}!</r> 建议在配置中正确设置cookies!')

    logger.opt(colors=True).info('init_live_info: <y>初始化B站直播间监控列表...</y>')
    t = DBTable(table_name='Subscription')

    tasks = []
    sub_res = await t.list_col_with_condition('sub_id', 'sub_type', 1)
    for sub_id in sub_res.result:
        tasks.append(__init_live_info(room_id=sub_id))
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f'bilibili_live_monitor: init live info failed, error: {repr(e)}')
    logger.opt(colors=True).info('init_live_info: <g>B站直播间监控列表初始化完成.</g>')


# 针对添加的直播间单独进行初始化
async def init_add_live_info(room_id: int):
    global live_title
    global live_status
    global live_up_name

    try:
        room_id = int(room_id)
        # 获取直播间信息
        _res = await get_live_info(room_id=room_id)
        if not _res.success():
            logger.opt(colors=True).error(
                f'init_add_live_info: <r>获取直播间信息失败</r>, room_id: {room_id}, error: {_res.info}')
            return
        live_info = _res.result
        up_uid = _res.result.get('uid')
        _res = await get_user_info(user_uid=up_uid)
        if not _res.success():
            logger.opt(colors=True).error(
                f'init_add_live_info: <r>获取直播间UP用户信息失败</r>, room_id: {room_id}, error: {_res.info}')
            return
        up_name = _res.result.get('name')

        # 直播状态放入live_status全局变量中
        live_status[room_id] = int(live_info['status'])

        # 直播间标题放入live_title全局变量中
        live_title[room_id] = str(live_info['title'])

        # 直播间up名称放入live_up_name全局变量中
        live_up_name[room_id] = str(up_name)

        logger.opt(colors=True).info(f'init_add_live_info: <lc>初始化直播间 {room_id}/{up_name} ... </lc>'
                                     f"<g>status: {live_info['status']}</g>")
    except Exception as e:
        logger.opt(colors=True).error(f'init_add_live_info: <r>初始化直播间 {room_id} 失败</r>, <y>error: {repr(e)}</y>')


# 初始化任务加入启动序列
get_driver().on_startup(init_live_info)


# 启用检查直播间状态的定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


# 创建用于更新数据库里面直播间UP名称的定时任务
@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    hour='2',
    minute='2',
    second='33',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='live_db_upgrade',
    coalesce=True,
    misfire_grace_time=60
)
async def live_db_upgrade():
    logger.debug('live_db_upgrade: started upgrade subscription info')
    t = DBTable(table_name='Subscription')
    sub_res = await t.list_col_with_condition('sub_id', 'sub_type', 1)
    for sub_id in sub_res.result:
        sub = DBSubscription(sub_type=1, sub_id=sub_id)
        _res = await get_live_info(room_id=sub_id)
        if not _res.success():
            logger.error(f'live_db_upgrade: 获取直播间信息失败, room_id: {sub_id}, error: {_res.info}')
            continue
        up_uid = _res.result.get('uid')
        _res = await get_user_info(user_uid=up_uid)
        if not _res.success():
            logger.error(f'live_db_upgrade: 获取直播间UP用户信息失败, room_id: {sub_id}, error: {_res.info}')
            continue
        up_name = _res.result.get('name')
        _res = await sub.add(up_name=up_name, live_info='B站直播间')
        if not _res.success():
            logger.error(f'live_db_upgrade: 更新直播间信息失败, room_id: {sub_id}, error: {_res.info}')
            continue
    logger.debug('live_db_upgrade: upgrade subscription info completed')


# 创建直播检查函数
async def bilibili_live_monitor():

    logger.debug(f"bilibili_live_monitor: checking started")
    global live_title
    global live_status
    global live_up_name

    # 获取当前bot列表
    bots = []
    for bot_id, bot in get_bots().items():
        bots.append(bot)

    # 获取所有有通知权限的群组
    t = DBTable(table_name='Group')
    group_res = await t.list_col_with_condition('group_id', 'notice_permissions', 1)
    all_noitce_groups = [int(x) for x in group_res.result]

    # 获取订阅表中的所有直播间订阅
    t = DBTable(table_name='Subscription')
    sub_res = await t.list_col_with_condition('sub_id', 'sub_type', 1)
    check_sub = [int(x) for x in sub_res.result]

    # 注册一个异步函数用于检查直播间状态
    async def check_live(room_id: int):
        # 获取直播间信息
        _res = await get_live_info(room_id=room_id)
        if not _res.success():
            logger.error(f'bilibili_live_monitor: 获取直播间信息失败, room_id: {room_id}, error: {_res.info}')
            return
        live_info = _res.result

        sub = DBSubscription(sub_type=1, sub_id=room_id)

        # 获取订阅了该直播间的所有群
        sub_group_res = await sub.sub_group_list()
        sub_group = sub_group_res.result
        # 需通知的群
        notice_group = list(set(all_noitce_groups) & set(sub_group))

        try:
            up_name = live_up_name[room_id]
            status = live_status[room_id]
            title = live_title[room_id]
        except KeyError:
            await init_add_live_info(room_id=room_id)
            try:
                up_name = live_up_name[room_id]
                status = live_status[room_id]
                title = live_title[room_id]
            except KeyError:
                logger.error(f'直播间: {room_id} 状态失效且获取失败!')
                raise Exception('直播间状态失效且获取失败')

        # 检查是否是已开播状态, 若已开播则监测直播间标题变动
        # 为避免开播时同时出现标题变更通知和开播通知, 在检测到直播状态变化时更新标题, 且仅在直播状态为直播中时发送标题变更通知
        if live_info['status'] != live_status[room_id]\
                and live_info['status'] == 1\
                and live_info['title'] != live_title[room_id]:
            # 更新标题
            live_title[room_id] = live_info['title']
            logger.info(f"直播间: {room_id}/{up_name} 标题变更为: {live_info['title']}")
        elif live_info['status'] == 1 and live_info['title'] != live_title[room_id]:
            # 通知有通知权限且订阅了该直播间的群
            cover_pic = await pic_2_base64(url=live_info.get('cover_img'))
            if cover_pic.success():
                msg = f"{up_name}的直播间换标题啦！\n\n【{live_info['title']}】\n{MessageSegment.image(cover_pic.result)}"
            else:
                # msg = f"{up_name}的直播间换标题啦！\n\n【{live_info['title']}】\n{live_info['url']}"
                msg = f"{up_name}的直播间换标题啦！\n\n【{live_info['title']}】"
            for group_id in notice_group:
                for _bot in bots:
                    try:
                        await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                        logger.info(f"向群组: {group_id} 发送直播间: {room_id} 标题变更通知")
                    except Exception as _e:
                        logger.warning(f"向群组: {group_id} 发送直播间: {room_id} 标题变更通知失败, error: {repr(_e)}")
                        continue
            live_title[room_id] = live_info['title']
            logger.info(f"直播间: {room_id}/{up_name} 标题变更为: {live_info['title']}")

        # 检测开播/下播
        # 检查直播间状态与原状态是否一致
        if live_info['status'] != live_status[room_id]:
            try:
                # 现在状态为未开播
                if live_info['status'] == 0:
                    live_start_info = f"LiveEnd! Room: {room_id}/{up_name}"
                    new_event = DBHistory(time=int(time.time()), self_id=-1, post_type='bilibili', detail_type='live')
                    await new_event.add(sub_type='live_end', user_id=room_id, user_name=up_name,
                                        raw_data=repr(live_info), msg_data=live_start_info)

                    msg = f'{up_name}下播了'
                    # 通知有通知权限且订阅了该直播间的群
                    for group_id in notice_group:
                        for _bot in bots:
                            try:
                                await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                logger.info(f"向群组: {group_id} 发送直播间: {room_id} 下播通知")
                            except Exception as _e:
                                logger.warning(f"向群组: {group_id} 发送直播间: {room_id} 下播通知失败, error: {repr(_e)}")
                                continue
                    # 更新直播间状态
                    live_status[room_id] = live_info['status']
                    logger.info(f"直播间: {room_id}/{up_name} 下播了")
                # 现在状态为直播中
                elif live_info['status'] == 1:
                    # 记录准确开播信息
                    live_start_info = f"LiveStart! Room: {room_id}/{up_name}, Title: {live_info['title']}, " \
                                      f"TrueTime: {live_info['time']}"
                    new_event = DBHistory(time=int(time.time()), self_id=-1, post_type='bilibili', detail_type='live')
                    await new_event.add(sub_type='live_start', user_id=room_id, user_name=up_name,
                                        raw_data=repr(live_info), msg_data=live_start_info)

                    cover_pic = await pic_2_base64(url=live_info.get('cover_img'))
                    if cover_pic.success():
                        msg = f"{live_info['time']}\n{up_name}开播啦！\n\n【{live_info['title']}】" \
                              f"\n{MessageSegment.image(cover_pic.result)}"
                    else:
                        # msg = f"{live_info['time']}\n{up_name}开播啦！\n\n【{live_info['title']}】\n{live_info['url']}"
                        msg = f"{live_info['time']}\n{up_name}开播啦！\n\n【{live_info['title']}】"
                    for group_id in notice_group:
                        for _bot in bots:
                            try:
                                await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                logger.info(f"向群组: {group_id} 发送直播间: {room_id} 开播通知")
                            except Exception as _e:
                                logger.warning(f"向群组: {group_id} 发送直播间: {room_id} 开播通知失败, error: {repr(_e)}")
                                continue
                    live_status[room_id] = live_info['status']
                    logger.info(f"直播间: {room_id}/{up_name} 开播了")
                # 现在状态为未开播（轮播中）
                elif live_info['status'] == 2:
                    live_start_info = f"LiveEnd! Room: {room_id}/{up_name}"
                    new_event = DBHistory(time=int(time.time()), self_id=-1, post_type='bilibili', detail_type='live')
                    await new_event.add(sub_type='live_end_with_playlist', user_id=room_id, user_name=up_name,
                                        raw_data=repr(live_info), msg_data=live_start_info)

                    msg = f'{up_name}下播了（轮播中）'
                    for group_id in notice_group:
                        for _bot in bots:
                            try:
                                await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                                logger.info(f"向群组: {group_id} 发送直播间: {room_id} 下播通知")
                            except Exception as _e:
                                logger.warning(f"向群组: {group_id} 发送直播间: {room_id} 下播通知失败, error: {repr(_e)}")
                                continue
                    live_status[room_id] = live_info['status']
                    logger.info(f"直播间: {room_id}/{up_name} 下播了（轮播中）")
            except Exception as _e:
                logger.warning(f'试图向群组发送直播间: {room_id}/{up_name} 的直播通知时发生了错误: {repr(_e)}')

    # 启用了检查池模式
    if ENABLE_BILI_CHECK_POOL_MODE:
        global checking_pool

        # checking_pool为空则上一轮检查完了, 重新往里面放新一轮的room_id
        if not checking_pool:
            checking_pool.extend(check_sub)

        # 看下checking_pool里面还剩多少
        waiting_num = len(checking_pool)

        # 默认单次检查并发数为2, 默认检查间隔为11s
        logger.debug(f'bili live pool mode debug info, B_checking_pool: {checking_pool}')
        if waiting_num >= 2:
            # 抽取检查对象
            now_checking = random.sample(checking_pool, k=2)
            # 更新checking_pool
            checking_pool = [x for x in checking_pool if x not in now_checking]
        else:
            now_checking = checking_pool.copy()
            checking_pool.clear()
        logger.debug(f'bili live pool mode debug info, A_checking_pool: {checking_pool}')
        logger.debug(f'bili live pool mode debug info, now_checking: {now_checking}')

        # 检查now_checking里面的直播间(异步)
        tasks = []
        for rid in now_checking:
            tasks.append(check_live(rid))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"bilibili_live_monitor: pool mode enable, checking completed, "
                         f"checked: {', '.join([str(x) for x in now_checking])}.")
        except Exception as e:
            logger.error(f'bilibili_live_monitor: pool mode enable, error occurred in checking {repr(e)}')

    # 没有启用检查池模式
    else:
        # 检查所有在订阅表里面的直播间(异步)
        tasks = []
        for rid in check_sub:
            tasks.append(check_live(rid))
        try:
            await asyncio.gather(*tasks)
            logger.debug(f"bilibili_live_monitor: pool mode disable, checking completed, "
                         f"checked: {', '.join([str(x) for x in check_sub])}.")
        except Exception as e:
            logger.error(f'bilibili_live_monitor: pool mode disable, error occurred in checking  {repr(e)}')


# 分时间段创建计划任务, 夜间闲时降低检查频率
# 根据检查池模式初始化检查时间间隔
if ENABLE_PROXY:
    # 启用了代理
    scheduler.add_job(
        bilibili_live_monitor,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        # hour='9-23',
        # minute='*/2',
        second='*/20',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='bilibili_live_monitor_proxy_enable',
        coalesce=True,
        misfire_grace_time=20
    )
elif ENABLE_BILI_CHECK_POOL_MODE:
    # 检查池启用
    scheduler.add_job(
        bilibili_live_monitor,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        # hour='9-23',
        # minute='*/2',
        second='11-59/11',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='bilibili_live_monitor_pool_enable',
        coalesce=True,
        misfire_grace_time=20
    )
else:
    # 检查池禁用, 日间
    scheduler.add_job(
        bilibili_live_monitor,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        hour='9-23',
        minute='*/1',
        # second='*/30',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='bilibili_live_monitor_in_day_pool_disable',
        coalesce=True,
        misfire_grace_time=30
    )
    # 检查池禁用, 夜间
    scheduler.add_job(
        bilibili_live_monitor,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        hour='0-8',
        minute='*/5',
        # second='*/30',
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='bilibili_live_monitor_in_night_pool_disable',
        coalesce=True,
        misfire_grace_time=30
    )

__all__ = [
    'scheduler',
    'init_add_live_info'
]
