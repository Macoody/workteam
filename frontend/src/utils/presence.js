import dayjs from 'dayjs'

export function isUserOnline(user) {
  if (!user?.is_online || !user?.last_active_time) return false
  return dayjs().diff(dayjs(user.last_active_time), 'second') <= 90
}

export function userPresenceText(user) {
  if (isUserOnline(user)) return '在线'
  const offlineTime = user?.last_offline_time || user?.last_active_time || user?.last_visit_time
  return offlineTime ? `离线 ${dayjs(offlineTime).format('MM-DD HH:mm')}` : '离线'
}

export function userPresenceTitle(user) {
  if (isUserOnline(user)) {
    return `在线，最后活跃 ${dayjs(user.last_active_time).format('YYYY-MM-DD HH:mm')}`
  }
  const offlineTime = user?.last_offline_time || user?.last_active_time || user?.last_visit_time
  return offlineTime ? `离线时间 ${dayjs(offlineTime).format('YYYY-MM-DD HH:mm')}` : '离线'
}
