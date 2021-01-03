# nonebot2_miya

基于nonebot2的qq机器人

## 当前适配nonebot2版本

[Nonebot2 PreRelease v2.0.0a8.post2](https://github.com/nonebot/nonebot2/releases/tag/v2.0.0a8.post2)

## 配套使用的api

api主要用于获取pixiv等网站内容

->[Miya API](https://github.com/Ailitonia/miya_api)

## 功能

- B站动态订阅
- B站直播间监控
- 求签抽卡
- Pixiv助手（需要API）
- Pixivision订阅（需要API）
- 复读姬
- roll点抽奖
- 搜二次元图（Saucenao 和 ascii2d）
- 来点涩图（涩图数据库需要自己导入）
- 表情包制作器


## 说点题外话

Omega_miya的设计思路显然与nonebot插件间应该尽可能解耦的设计思路相悖。

当然这和Omega_miya最初的用途有关，她本来是用来督促字幕组~~摸鱼~~干活的，并且一开始设计的时候继承了初代~~真正零号Omega_miya~~的数据库以及设计思路，所以Omega_miya的插件体系是强耦合的，后来随着功能迭代，也就改不过来了。

因此，对于Omega_miya这个项目，我想她可能并不是可以直接拿来就用的，因为她的设计本身就有局限性，这里主要是可以提供一些功能上的思路，希望能给其他的开发者一些启发。

欢迎来提各种issue~
