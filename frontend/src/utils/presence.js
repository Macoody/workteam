import { formatBusinessTime } from '@/utils/time'

export function isUserOnline(user) {
  return Boolean(user?.is_online)
}

export function userPresenceText(user) {
  if (isUserOnline(user)) return '在线'
  const offlineTime = user?.last_offline_time || user?.last_active_time || user?.last_visit_time
  return offlineTime ? `离线 ${formatBusinessTime(offlineTime, 'MM-DD HH:mm')}` : '离线'
}

export function userPresenceTitle(user) {
  if (isUserOnline(user)) {
    return `在线，最后活跃 ${formatBusinessTime(user.last_active_time)}`
  }
  const offlineTime = user?.last_offline_time || user?.last_active_time || user?.last_visit_time
  return offlineTime ? `离线时间 ${formatBusinessTime(offlineTime)}` : '离线'
}
