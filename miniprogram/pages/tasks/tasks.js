const { request, clearSession } = require('../../utils/request')
const { isDoneTask, taskTimeText } = require('../../utils/date')

function statusClass(status) {
  if (status === '进行中') return 'doing'
  if (status === '待验收') return 'review'
  if (status === '已完成') return 'done'
  return 'pending'
}

Page({
  data: {
    userName: '',
    tasks: [],
    displayTasks: [],
    projectsById: {},
    filter: 'active',
    activeCount: 0,
    doneCount: 0,
    loading: false
  },

  onShow() {
    if (!wx.getStorageSync('token')) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    this.loadData()
  },

  onPullDownRefresh() {
    this.loadData().finally(() => wx.stopPullDownRefresh())
  },

  async loadData() {
    this.setData({ loading: true })
    try {
      const [user, projects, tasks] = await Promise.all([
        request({ url: '/auth/me' }),
        request({ url: '/projects' }),
        request({ url: '/tasks?my_tasks=true' })
      ])
      const projectsById = {}
      ;(projects || []).forEach((project) => {
        projectsById[project.id] = project.name
      })
      const normalizedTasks = this.normalizeTasks(tasks || [], projectsById)
      this.setData({
        userName: user.display_name || user.username || '成员',
        projectsById,
        tasks: normalizedTasks,
        activeCount: normalizedTasks.filter((task) => !task.isDone).length,
        doneCount: normalizedTasks.filter((task) => task.isDone).length
      })
      this.applyFilter()
    } catch (error) {
      wx.showToast({ title: error.detail || '任务加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  normalizeTasks(tasks, projectsById) {
    return tasks.map((task) => {
      const status = task.column_name || '未分配'
      return {
        ...task,
        status,
        statusClass: statusClass(status),
        isDone: isDoneTask(task),
        isRecurring: Boolean(task.recurrence_rule_id),
        projectText: projectsById[task.project_id] || `项目 #${task.project_id}`,
        timeText: taskTimeText(task)
      }
    })
  },

  setFilter(event) {
    this.setData({ filter: event.currentTarget.dataset.filter })
    this.applyFilter()
  },

  applyFilter() {
    let nextTasks = this.data.tasks
    if (this.data.filter === 'active') {
      nextTasks = nextTasks.filter((task) => !task.isDone)
    } else if (this.data.filter === 'done') {
      nextTasks = nextTasks.filter((task) => task.isDone)
    }
    this.setData({ displayTasks: nextTasks })
  },

  openTask(event) {
    const id = event.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/task-detail/task-detail?id=${id}` })
  },

  completeTask(event) {
    const id = event.currentTarget.dataset.id
    wx.showModal({
      title: '完成任务',
      content: '确认完成/打卡这条任务吗？',
      confirmText: '完成',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await request({ url: `/tasks/${id}/complete`, method: 'POST' })
          wx.showToast({ title: '已完成', icon: 'success' })
          this.loadData()
        } catch (error) {
          wx.showToast({ title: error.detail || '操作失败', icon: 'none' })
        }
      }
    })
  },

  logout() {
    clearSession()
    wx.reLaunch({ url: '/pages/login/login' })
  }
})
