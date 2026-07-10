const { request } = require('../../utils/request')
const { formatDate, isDoneTask, taskTimeText } = require('../../utils/date')

function statusClass(status) {
  if (status === '进行中') return 'doing'
  if (status === '待验收') return 'review'
  if (status === '已完成') return 'done'
  return 'pending'
}

Page({
  data: {
    id: null,
    task: null,
    completedText: '',
    loading: false,
    completing: false
  },

  onLoad(options) {
    this.setData({ id: options.id })
    this.loadTask()
  },

  async loadTask() {
    if (!this.data.id) return
    this.setData({ loading: true })
    try {
      const task = await request({ url: `/tasks/${this.data.id}` })
      const status = task.column_name || '未分配'
      const nextTask = {
        ...task,
        status,
        statusClass: statusClass(status),
        isDone: isDoneTask(task),
        isRecurring: Boolean(task.recurrence_rule_id),
        projectText: `项目 #${task.project_id}`,
        timeText: taskTimeText(task)
      }
      this.setData({
        task: nextTask,
        completedText: task.completed_at ? formatDate(task.completed_at) : ''
      })
    } catch (error) {
      wx.showToast({ title: error.detail || '任务加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  completeTask() {
    wx.showModal({
      title: '完成任务',
      content: '确认完成/打卡这条任务吗？',
      confirmText: '完成',
      success: async (res) => {
        if (!res.confirm) return
        this.setData({ completing: true })
        try {
          await request({ url: `/tasks/${this.data.id}/complete`, method: 'POST' })
          wx.showToast({ title: '已完成', icon: 'success' })
          this.loadTask()
        } catch (error) {
          wx.showToast({ title: error.detail || '操作失败', icon: 'none' })
        } finally {
          this.setData({ completing: false })
        }
      }
    })
  }
})
