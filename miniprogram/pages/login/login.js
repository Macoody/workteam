const { DEV_OPENID } = require('../../utils/config')
const { formRequest, request, saveSession } = require('../../utils/request')

Page({
  data: {
    username: '',
    password: '',
    message: '',
    messageType: '',
    wechatLoading: false,
    accountLoading: false,
    bindLoading: false
  },

  onLoad() {
    if (wx.getStorageSync('token')) {
      wx.reLaunch({ url: '/pages/tasks/tasks' })
    }
  },

  handleInput(event) {
    const field = event.currentTarget.dataset.field
    this.setData({ [field]: event.detail.value })
  },

  getLoginCode() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) => resolve(res.code),
        fail: reject
      })
    })
  },

  finishLogin(data) {
    saveSession(data)
    wx.reLaunch({ url: '/pages/tasks/tasks' })
  },

  showError(error, fallback) {
    const detail = error && (error.detail || error.errMsg)
    this.setData({
      message: detail || fallback,
      messageType: 'error'
    })
  },

  async wechatLogin() {
    if (this.data.wechatLoading) return
    this.setData({ wechatLoading: true, message: '' })
    try {
      const code = await this.getLoginCode()
      const data = await request({
        url: '/wechat/login',
        method: 'POST',
        auth: false,
        data: {
          code,
          dev_openid: DEV_OPENID
        }
      })
      if (data.bound) {
        this.finishLogin(data)
        return
      }
      this.setData({
        message: data.message || '微信尚未绑定成员账号',
        messageType: 'info'
      })
    } catch (error) {
      this.showError(error, '微信登录失败')
    } finally {
      this.setData({ wechatLoading: false })
    }
  },

  async accountLogin() {
    if (!this.data.username || !this.data.password) {
      this.setData({ message: '请输入用户名和密码', messageType: 'error' })
      return
    }
    this.setData({ accountLoading: true, message: '' })
    try {
      const data = await formRequest('/auth/login', {
        username: this.data.username,
        password: this.data.password
      })
      this.finishLogin(data)
    } catch (error) {
      this.showError(error, '账号登录失败')
    } finally {
      this.setData({ accountLoading: false })
    }
  },

  async bindWechat() {
    if (!this.data.username || !this.data.password) {
      this.setData({ message: '请输入用户名和密码', messageType: 'error' })
      return
    }
    this.setData({ bindLoading: true, message: '' })
    try {
      const code = await this.getLoginCode()
      const data = await request({
        url: '/wechat/bind',
        method: 'POST',
        auth: false,
        data: {
          code,
          dev_openid: DEV_OPENID,
          username: this.data.username,
          password: this.data.password
        }
      })
      this.finishLogin(data)
    } catch (error) {
      this.showError(error, '绑定失败')
    } finally {
      this.setData({ bindLoading: false })
    }
  }
})
