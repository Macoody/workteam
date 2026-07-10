const { API_BASE } = require('./config')

function encodeForm(data) {
  return Object.keys(data || {})
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(data[key] || '')}`)
    .join('&')
}

function authHeader() {
  const token = wx.getStorageSync('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function handleUnauthorized() {
  wx.removeStorageSync('token')
  wx.removeStorageSync('user')
  wx.reLaunch({ url: '/pages/login/login' })
}

function request(options) {
  const { url, method = 'GET', data = {}, header = {}, auth = true } = options
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}${url}`,
      method,
      data,
      header: {
        'content-type': 'application/json',
        ...(auth ? authHeader() : {}),
        ...header
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }
        if (res.statusCode === 401) {
          handleUnauthorized()
        }
        reject(res.data || { detail: '请求失败' })
      },
      fail(error) {
        reject(error)
      }
    })
  })
}

function formRequest(url, data) {
  return request({
    url,
    method: 'POST',
    data: encodeForm(data),
    auth: false,
    header: {
      'content-type': 'application/x-www-form-urlencoded'
    }
  })
}

function saveSession(data) {
  if (!data || !data.access_token) return
  wx.setStorageSync('token', data.access_token)
  wx.setStorageSync('user', data.user || null)
  const app = getApp()
  app.globalData.user = data.user || null
}

function clearSession() {
  wx.removeStorageSync('token')
  wx.removeStorageSync('user')
  const app = getApp()
  app.globalData.user = null
}

module.exports = {
  request,
  formRequest,
  saveSession,
  clearSession
}
