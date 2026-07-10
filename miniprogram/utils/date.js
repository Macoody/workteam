function pad(value) {
  return value < 10 ? `0${value}` : `${value}`
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function latestDeliveryDate(task) {
  const dates = task && task.delivery_dates ? task.delivery_dates : []
  return dates.length ? dates[dates.length - 1] : task && task.due_date
}

function isDoneTask(task) {
  return ['待验收', '已完成'].includes(task && task.column_name)
}

function taskTimeText(task) {
  if (isDoneTask(task) && task.completed_at) {
    return `完成 ${formatDate(task.completed_at)}`
  }
  const deliveryDate = latestDeliveryDate(task)
  return deliveryDate ? `交付 ${formatDate(deliveryDate)}` : ''
}

module.exports = {
  formatDate,
  latestDeliveryDate,
  isDoneTask,
  taskTimeText
}
