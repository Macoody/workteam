# 徐东摆地摊小程序

第一版小程序先覆盖手机端任务主流程：

- 账号登录
- 微信登录与成员账号绑定
- 查看“我的任务”
- 查看任务详情
- 完成/打卡任务

## 打开方式

1. 用微信开发者工具打开 `miniprogram/` 目录。
2. 没有正式 AppID 时，可以先使用 `touristappid` 预览页面和账号登录流程。
3. 正式联调时，把 `project.config.json` 里的 `appid` 改成真实小程序 AppID。

## 后端配置

小程序默认请求：

```js
https://new.xh-tech.top/api
```

正式微信登录需要在后端环境变量里配置：

```bash
WECHAT_MINI_APP_ID=wx_your_app_id
WECHAT_MINI_APP_SECRET=your_app_secret
```

如果只是本地开发微信绑定流程，可以显式开启：

```bash
WECHAT_DEV_LOGIN_ENABLED=true
```

然后在 `utils/config.js` 里填一个固定 `DEV_OPENID`。

## 发布前检查

- 微信公众平台里配置合法请求域名：`https://new.xh-tech.top`
- 确认服务器已配置小程序 AppID/AppSecret
- 用真实微信账号完成一次“绑定微信并登录”
