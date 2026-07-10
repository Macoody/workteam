import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

dayjs.extend(utc)
dayjs.extend(timezone)

export const BUSINESS_TIMEZONE = 'Asia/Shanghai'
const TIMEZONE_SUFFIX_RE = /(Z|[+-]\d{2}:?\d{2})$/i

export function businessDayjs(value) {
  if (!value) return null
  if (dayjs.isDayjs(value)) return value.tz(BUSINESS_TIMEZONE)
  if (value instanceof Date) return dayjs(value).tz(BUSINESS_TIMEZONE)
  const text = String(value).trim()
  if (!text) return null
  return TIMEZONE_SUFFIX_RE.test(text)
    ? dayjs(text).tz(BUSINESS_TIMEZONE)
    : dayjs.tz(text, BUSINESS_TIMEZONE)
}

export function formatBusinessTime(value, pattern = 'YYYY-MM-DD HH:mm') {
  const time = businessDayjs(value)
  return time?.isValid() ? time.format(pattern) : '--'
}

export function businessTimeValue(value) {
  const time = businessDayjs(value)
  return time?.isValid() ? time.valueOf() : 0
}

export function toBusinessPickerDate(value) {
  const time = businessDayjs(value)
  if (!time?.isValid()) return null
  return new Date(
    time.year(),
    time.month(),
    time.date(),
    time.hour(),
    time.minute(),
    time.second(),
    time.millisecond()
  )
}

export function businessNowPickerDate() {
  return toBusinessPickerDate(new Date())
}

export function toBusinessPayload(value) {
  if (!value) return null
  return dayjs(value).format('YYYY-MM-DDTHH:mm:ss')
}

export function businessTodayText() {
  return dayjs().tz(BUSINESS_TIMEZONE).format('YYYY-MM-DD')
}

export function businessNowPayload() {
  return dayjs().tz(BUSINESS_TIMEZONE).format('YYYY-MM-DDTHH:mm:ss')
}
