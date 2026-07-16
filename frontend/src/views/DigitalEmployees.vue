<template>
  <AppShell title="数字员工" description="集中管理 AI 手机资产、客户交付、付款信息和服务跟进。">
    <template #actions>
      <el-button type="primary" :icon="Plus" @click="openPhoneCreate">登记手机</el-button>
      <el-button type="primary" plain :icon="Plus" @click="openCustomerCreate">新增客户</el-button>
      <el-button :icon="Setting" @click="serviceItemDialog = true">服务配置</el-button>
      <el-button :icon="Refresh" @click="loadAll">刷新</el-button>
    </template>

    <div class="digital-overview-grid">
      <div class="overview-item">
        <div class="overview-label">手机总数</div>
        <div class="overview-value">{{ overview.total_phones }}</div>
        <div class="overview-meta">库存 {{ overview.in_stock_phones }} 台</div>
      </div>
      <div class="overview-item accent-blue">
        <div class="overview-label">员工持有</div>
        <div class="overview-value">{{ overview.assigned_phones }}</div>
        <div class="overview-meta">已分配给成员</div>
      </div>
      <div class="overview-item accent-green">
        <div class="overview-label">客户使用</div>
        <div class="overview-value">{{ overview.sold_phones }}</div>
        <div class="overview-meta">已关联客户</div>
      </div>
      <div class="overview-item accent-amber">
        <div class="overview-label">客户数量</div>
        <div class="overview-value">{{ overview.customers }}</div>
        <div class="overview-meta">正在服务客户</div>
      </div>
      <div class="overview-item accent-rose">
        <div class="overview-label">未完成服务</div>
        <div class="overview-value">{{ overview.unfinished_service_records }}</div>
        <div class="overview-meta">{{ overview.active_service_items }} 个服务配置</div>
      </div>
    </div>

    <div class="panel digital-panel" v-loading="loading">
      <el-tabs v-model="activeTab" class="digital-tabs">
        <el-tab-pane label="手机资产" name="phones">
          <div class="table-toolbar">
            <el-input
              v-model="phoneKeyword"
              :prefix-icon="Search"
              clearable
              placeholder="搜索型号、序列号、账号或客户"
              class="toolbar-search"
            />
            <span class="toolbar-count">{{ filteredPhones.length }} 台手机</span>
          </div>

          <el-table :data="filteredPhones" style="width: 100%">
            <el-table-column label="手机" min-width="230">
              <template #default="{ row }">
                <div class="main-cell">
                  <div class="primary-line">
                    {{ row.model }}
                    <el-tag size="small" effect="light">{{ conditionLabel(row.condition) }}</el-tag>
                  </div>
                  <div class="item-meta">{{ row.memory }} · {{ row.color || '未填颜色' }}</div>
                  <div class="item-meta">序列号 {{ row.serial_number || '--' }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="140">
              <template #default="{ row }">
                <el-tag :type="statusMeta(row.status).type" effect="light" class="status-tag">
                  {{ statusMeta(row.status).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="当前位置" min-width="150">
              <template #default="{ row }">
                <span v-if="row.holder" class="user-chip" :style="{ background: row.holder.color || '#dbeafe' }">
                  {{ userName(row.holder) }}
                </span>
                <span v-else class="text-muted">未分配成员</span>
              </template>
            </el-table-column>
            <el-table-column label="关联客户" min-width="160">
              <template #default="{ row }">
                <span v-if="row.customer" class="customer-link">{{ row.customer.name }}</span>
                <span v-else class="text-muted">未关联</span>
              </template>
            </el-table-column>
            <el-table-column label="绑定账号" min-width="260">
              <template #default="{ row }">
                <div v-if="accountRows(row).length" class="account-stack">
                  <span v-for="item in accountRows(row)" :key="item.label">
                    {{ item.label }}：{{ item.value }}
                  </span>
                </div>
                <span v-else class="text-muted">暂无账号信息</span>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="150">
              <template #default="{ row }">
                {{ formatDate(row.updated_at || row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <div class="row-actions">
                  <el-button size="small" @click="openPhoneEdit(row)">编辑</el-button>
                  <el-button v-if="isAdmin" size="small" type="danger" plain @click="deletePhone(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="客户管理" name="customers">
          <div class="table-toolbar">
            <el-input
              v-model="customerKeyword"
              :prefix-icon="Search"
              clearable
              placeholder="搜索客户、设备号、手机号、微信或来源"
              class="toolbar-search"
            />
            <span class="toolbar-count">{{ filteredCustomers.length }} 个客户</span>
          </div>

          <el-table :data="filteredCustomers" style="width: 100%">
            <el-table-column label="客户" min-width="210">
              <template #default="{ row }">
                <div class="main-cell">
                  <div class="primary-line">{{ row.name }}</div>
                  <div class="item-meta">手机号 {{ row.phone || '--' }}</div>
                  <div class="item-meta">微信 {{ row.wechat || '--' }}</div>
                  <div class="item-meta">设备号 {{ row.device_number || '--' }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="使用手机" min-width="210">
              <template #default="{ row }">
                <div v-if="row.phones?.length" class="phone-chip-stack">
                  <el-tag v-for="phone in row.phones" :key="phone.id" effect="light">
                    {{ phone.model }} {{ phone.memory }}
                  </el-tag>
                </div>
                <span v-else class="text-muted">未关联手机</span>
              </template>
            </el-table-column>
            <el-table-column label="付款" min-width="190">
              <template #default="{ row }">
                <div class="main-cell">
                  <div class="primary-line compact">{{ row.payment_amount || '未填金额' }}</div>
                  <div class="item-meta">{{ paymentMethodText(row) }}</div>
                  <el-tag size="small" :type="paymentStatusMeta(row.payment_status).type" effect="light">
                    {{ paymentStatusMeta(row.payment_status).label }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="服务时间" min-width="210">
              <template #default="{ row }">
                <div class="item-meta">{{ serviceTimeText(row) }}</div>
              </template>
            </el-table-column>
            <el-table-column label="服务跟进" min-width="300">
              <template #default="{ row }">
                <div class="service-cell">
                  <div class="service-progress-row">
                    <el-progress
                      :percentage="serviceProgress(row)"
                      :stroke-width="8"
                      :show-text="false"
                      class="service-progress"
                    />
                    <span>{{ serviceProgressText(row) }}</span>
                  </div>
                  <div class="service-tags">
                    <el-tag
                      v-for="record in row.service_records"
                      :key="record.id"
                      size="small"
                      :type="record.is_done ? 'success' : 'info'"
                      effect="light"
                    >
                      {{ record.service_item?.name || '服务项' }}
                    </el-tag>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <div class="row-actions">
                  <el-button size="small" type="primary" plain @click="openServiceDialog(row)">跟进</el-button>
                  <el-button size="small" @click="openCustomerEdit(row)">编辑</el-button>
                  <el-button v-if="isAdmin" size="small" type="danger" plain @click="deleteCustomer(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="phoneDialog" :title="editingPhoneId ? '编辑手机' : '登记手机'" width="760px">
      <el-form :model="phoneForm" label-position="top">
        <div class="form-grid">
          <el-form-item label="手机型号">
            <el-select v-model="phoneForm.model" placeholder="请选择手机型号" style="width: 100%">
              <el-option v-for="item in phoneModelOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="内存">
            <el-select v-model="phoneForm.memory" style="width: 100%" filterable allow-create>
              <el-option v-for="item in memoryOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="序列号">
            <el-input v-model="phoneForm.serial_number" placeholder="选填，建议唯一记录" />
          </el-form-item>
          <el-form-item label="激活码">
            <el-input v-model="phoneForm.activation_code" placeholder="填写该手机对应的激活码" />
          </el-form-item>
          <el-form-item label="新旧状态">
            <el-select v-model="phoneForm.condition" style="width: 100%">
              <el-option label="全新" value="new" />
              <el-option label="二手" value="used" />
            </el-select>
          </el-form-item>
          <el-form-item label="颜色">
            <el-select v-model="phoneForm.color" placeholder="请选择颜色" style="width: 100%">
              <el-option v-for="item in colorOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="手机状态">
            <el-select v-model="phoneForm.status" style="width: 100%">
              <el-option label="库存" value="in_stock" />
              <el-option label="员工持有" value="assigned" />
              <el-option label="已售/客户使用" value="sold" />
            </el-select>
          </el-form-item>
          <el-form-item label="当前归属员工">
            <el-select v-model="phoneForm.holder_id" clearable filterable style="width: 100%">
              <el-option v-for="user in users" :key="user.id" :label="userName(user)" :value="user.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联客户">
            <el-select
              v-model="phoneForm.customer_id"
              clearable
              filterable
              style="width: 100%"
              @change="handlePhoneCustomerChange"
            >
              <el-option v-for="customer in customers" :key="customer.id" :label="customer.name" :value="customer.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="绑定手机号">
            <el-input v-model="phoneForm.bound_phone" />
          </el-form-item>
          <el-form-item label="抖音账号">
            <el-input v-model="phoneForm.douyin_account" />
          </el-form-item>
          <el-form-item label="小红书账号">
            <el-input v-model="phoneForm.xiaohongshu_account" />
          </el-form-item>
          <el-form-item label="微信账号">
            <el-input v-model="phoneForm.wechat_account" />
          </el-form-item>
          <el-form-item label="快手账号">
            <el-input v-model="phoneForm.kuaishou_account" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="phoneForm.notes" type="textarea" :rows="3" placeholder="采购批次、配件、异常情况等" />
        </el-form-item>
        <div class="dialog-actions">
          <el-button @click="phoneDialog = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="savePhone">保存手机</el-button>
        </div>
      </el-form>
    </el-dialog>

    <el-dialog v-model="customerDialog" :title="editingCustomerId ? '编辑客户' : '新增客户'" width="760px">
      <el-form :model="customerForm" label-position="top">
        <div class="form-grid">
          <el-form-item label="客户名称">
            <el-input v-model="customerForm.name" placeholder="客户姓名或公司名称" />
          </el-form-item>
          <el-form-item label="客户手机号">
            <el-input v-model="customerForm.phone" />
          </el-form-item>
          <el-form-item label="客户微信">
            <el-input v-model="customerForm.wechat" />
          </el-form-item>
          <el-form-item label="设备号">
            <el-input v-model="customerForm.device_number" placeholder="填写客户对应的设备号" />
          </el-form-item>
          <el-form-item label="客户来源">
            <el-input v-model="customerForm.source" placeholder="如 抖音 / 转介绍 / 小红书" />
          </el-form-item>
          <el-form-item label="付款金额">
            <el-input v-model="customerForm.payment_amount" placeholder="如 3980" />
          </el-form-item>
          <el-form-item label="收款方式">
            <el-select v-model="customerForm.payment_method" clearable allow-create filterable style="width: 100%">
              <el-option label="微信" value="微信" />
              <el-option label="支付宝" value="支付宝" />
              <el-option label="银行卡" value="银行卡" />
              <el-option label="现金" value="现金" />
            </el-select>
          </el-form-item>
          <el-form-item label="付款状态">
            <el-select v-model="customerForm.payment_status" style="width: 100%">
              <el-option label="未付款" value="unpaid" />
              <el-option label="部分付款" value="partial" />
              <el-option label="已付款" value="paid" />
              <el-option label="已退款" value="refunded" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联手机">
            <el-select
              v-model="customerForm.phone_ids"
              multiple
              collapse-tags
              collapse-tags-tooltip
              filterable
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="phone in phoneOptionsForCustomer"
                :key="phone.id"
                :label="phoneOptionLabel(phone)"
                :value="phone.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="服务开始时间">
            <el-date-picker v-model="customerForm.service_start_at" type="datetime" style="width: 100%" />
          </el-form-item>
          <el-form-item label="服务结束时间">
            <el-date-picker v-model="customerForm.service_end_at" type="datetime" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="付款备注">
          <el-input v-model="customerForm.payment_note" type="textarea" :rows="2" placeholder="尾款、优惠、合同等信息" />
        </el-form-item>
        <el-form-item label="客户备注">
          <el-input v-model="customerForm.notes" type="textarea" :rows="3" placeholder="客户需求、交付重点、沟通记录摘要等" />
        </el-form-item>
        <div class="dialog-actions">
          <el-button @click="customerDialog = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveCustomer">保存客户</el-button>
        </div>
      </el-form>
    </el-dialog>

    <el-dialog
      v-model="serviceDialog"
      :title="serviceCustomer ? `${serviceCustomer.name} 的服务跟进` : '服务跟进'"
      width="660px"
    >
      <div class="service-record-list">
        <div v-for="record in serviceRecords" :key="record.service_item_id" class="service-record-row">
          <el-checkbox v-model="record.is_done" :disabled="record.saving" @change="saveServiceRecord(record)">
            {{ record.service_item?.name || '服务项' }}
          </el-checkbox>
          <el-input
            v-model="record.notes"
            type="textarea"
            :rows="2"
            placeholder="该项服务的备注"
            @blur="saveServiceRecord(record, true)"
          />
          <div class="record-meta">
            <span>{{ record.is_done ? `完成于 ${formatDate(record.completed_at)}` : '待处理' }}</span>
            <span v-if="record.updated_user">更新人 {{ userName(record.updated_user) }}</span>
          </div>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="serviceItemDialog" title="服务配置" width="560px">
      <div class="config-list">
        <div v-for="item in serviceItems" :key="item.id" class="config-row">
          <div>
            <div class="primary-line compact">{{ item.name }}</div>
            <div class="item-meta">{{ item.description || '暂无说明' }}</div>
          </div>
          <el-tag :type="item.is_active ? 'success' : 'info'" effect="light">
            {{ item.is_active ? '启用' : '停用' }}
          </el-tag>
        </div>
      </div>
      <el-form :model="newServiceItem" label-position="top" class="new-config-form">
        <el-form-item label="新增服务内容">
          <el-input v-model="newServiceItem.name" placeholder="如 账号包装、素材上传、直播设置" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="newServiceItem.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-button type="primary" :loading="savingServiceItem" style="width: 100%" @click="addServiceItem">
          添加服务内容
        </el-button>
      </el-form>
    </el-dialog>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search, Setting } from '@element-plus/icons-vue'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import { formatBusinessTime, toBusinessPayload, toBusinessPickerDate } from '@/utils/time'

const auth = useAuthStore()
const activeTab = ref('phones')
const loading = ref(false)
const saving = ref(false)
const savingServiceItem = ref(false)
const users = ref([])
const phones = ref([])
const customers = ref([])
const serviceItems = ref([])
const phoneKeyword = ref('')
const customerKeyword = ref('')
const phoneDialog = ref(false)
const customerDialog = ref(false)
const serviceDialog = ref(false)
const serviceItemDialog = ref(false)
const editingPhoneId = ref(null)
const editingCustomerId = ref(null)
const serviceCustomer = ref(null)
const serviceRecords = ref([])
const overview = reactive({
  total_phones: 0,
  in_stock_phones: 0,
  assigned_phones: 0,
  sold_phones: 0,
  customers: 0,
  active_service_items: 0,
  unfinished_service_records: 0
})

const phoneModelOptions = ['Redmi note 15', 'Redmi note 15 pro']
const memoryOptions = ['8+128', '8+256', '6+128', '12+256', '12+512']
const colorOptions = ['黑色', '白色', '蓝色']
const isAdmin = computed(() => auth.user?.role === 'admin')

const phoneForm = reactive(defaultPhoneForm())
const customerForm = reactive(defaultCustomerForm())
const newServiceItem = reactive({
  name: '',
  description: ''
})

const filteredPhones = computed(() => {
  const keyword = phoneKeyword.value.trim().toLowerCase()
  if (!keyword) return phones.value
  return phones.value.filter(row => includesKeyword([
    row.model,
    row.memory,
    row.serial_number,
    row.activation_code,
    row.color,
    row.bound_phone,
    row.douyin_account,
    row.xiaohongshu_account,
    row.wechat_account,
    row.kuaishou_account,
    row.customer?.name,
    row.holder?.display_name,
    row.holder?.username
  ], keyword))
})

const filteredCustomers = computed(() => {
  const keyword = customerKeyword.value.trim().toLowerCase()
  if (!keyword) return customers.value
  return customers.value.filter(row => includesKeyword([
    row.name,
    row.phone,
    row.wechat,
    row.device_number,
    row.source,
    row.payment_amount,
    row.payment_method,
    ...(row.phones || []).map(phone => `${phone.model} ${phone.memory} ${phone.serial_number || ''}`)
  ], keyword))
})

const phoneOptionsForCustomer = computed(() => {
  return phones.value.filter(phone => !phone.customer_id || phone.customer_id === editingCustomerId.value)
})

onMounted(async () => {
  await auth.getMe()
  await loadAll()
})

function defaultPhoneForm() {
  return {
    model: 'Redmi note 15',
    memory: '8+128',
    serial_number: '',
    activation_code: '',
    condition: 'new',
    color: '黑色',
    status: 'in_stock',
    holder_id: null,
    customer_id: null,
    bound_phone: '',
    douyin_account: '',
    xiaohongshu_account: '',
    wechat_account: '',
    kuaishou_account: '',
    notes: ''
  }
}

function defaultCustomerForm() {
  return {
    name: '',
    phone: '',
    wechat: '',
    device_number: '',
    source: '',
    payment_amount: '',
    payment_method: '',
    payment_status: 'unpaid',
    payment_note: '',
    service_start_at: null,
    service_end_at: null,
    notes: '',
    phone_ids: []
  }
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([loadUsers(), loadServiceItems()])
    await Promise.all([loadPhones(), loadCustomers()])
    await loadOverview()
  } catch (error) {
    console.error(error)
    ElMessage.error('数字员工数据加载失败')
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  users.value = await api.get('/auth/users')
}

async function loadPhones() {
  phones.value = await api.get('/digital-employees/phones')
}

async function loadCustomers() {
  customers.value = await api.get('/digital-employees/customers')
}

async function loadServiceItems() {
  serviceItems.value = await api.get('/digital-employees/service-items')
}

async function loadOverview() {
  Object.assign(overview, await api.get('/digital-employees/overview'))
}

function openPhoneCreate() {
  editingPhoneId.value = null
  Object.assign(phoneForm, defaultPhoneForm())
  phoneDialog.value = true
}

function openPhoneEdit(row) {
  editingPhoneId.value = row.id
  Object.assign(phoneForm, {
    ...defaultPhoneForm(),
    model: row.model || '',
    memory: row.memory || '8+128',
    serial_number: row.serial_number || '',
    activation_code: row.activation_code || '',
    condition: row.condition || 'new',
    color: row.color || '',
    status: row.status || 'in_stock',
    holder_id: row.holder_id || null,
    customer_id: row.customer_id || null,
    bound_phone: row.bound_phone || '',
    douyin_account: row.douyin_account || '',
    xiaohongshu_account: row.xiaohongshu_account || '',
    wechat_account: row.wechat_account || '',
    kuaishou_account: row.kuaishou_account || '',
    notes: row.notes || ''
  })
  phoneDialog.value = true
}

function handlePhoneCustomerChange(value) {
  if (value && phoneForm.status === 'in_stock') {
    phoneForm.status = 'sold'
  }
}

async function savePhone() {
  if (!phoneForm.model.trim() || !phoneForm.memory.trim()) {
    ElMessage.warning('请填写手机型号和内存')
    return
  }
  saving.value = true
  try {
    const payload = { ...phoneForm }
    if (editingPhoneId.value) {
      await api.put(`/digital-employees/phones/${editingPhoneId.value}`, payload)
      ElMessage.success('手机信息已更新')
    } else {
      await api.post('/digital-employees/phones', payload)
      ElMessage.success('手机已登记')
    }
    phoneDialog.value = false
    await refreshCoreData()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '保存手机失败')
  } finally {
    saving.value = false
  }
}

async function deletePhone(row) {
  try {
    await ElMessageBox.confirm(`确认删除手机记录“${row.model}”？`, '删除确认', { type: 'warning' })
    await api.delete(`/digital-employees/phones/${row.id}`)
    ElMessage.success('手机记录已删除')
    await refreshCoreData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.detail || '删除失败')
    }
  }
}

function openCustomerCreate() {
  editingCustomerId.value = null
  Object.assign(customerForm, defaultCustomerForm())
  customerDialog.value = true
}

function openCustomerEdit(row) {
  editingCustomerId.value = row.id
  Object.assign(customerForm, {
    ...defaultCustomerForm(),
    name: row.name || '',
    phone: row.phone || '',
    wechat: row.wechat || '',
    device_number: row.device_number || '',
    source: row.source || '',
    payment_amount: row.payment_amount || '',
    payment_method: row.payment_method || '',
    payment_status: row.payment_status || 'unpaid',
    payment_note: row.payment_note || '',
    service_start_at: toBusinessPickerDate(row.service_start_at),
    service_end_at: toBusinessPickerDate(row.service_end_at),
    notes: row.notes || '',
    phone_ids: (row.phones || []).map(phone => phone.id)
  })
  customerDialog.value = true
}

async function saveCustomer() {
  if (!customerForm.name.trim()) {
    ElMessage.warning('请填写客户名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...customerForm,
      service_start_at: toBusinessPayload(customerForm.service_start_at),
      service_end_at: toBusinessPayload(customerForm.service_end_at)
    }
    if (editingCustomerId.value) {
      await api.put(`/digital-employees/customers/${editingCustomerId.value}`, payload)
      ElMessage.success('客户信息已更新')
    } else {
      await api.post('/digital-employees/customers', payload)
      ElMessage.success('客户已新增')
    }
    customerDialog.value = false
    await refreshCoreData()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '保存客户失败')
  } finally {
    saving.value = false
  }
}

async function deleteCustomer(row) {
  try {
    await ElMessageBox.confirm(`确认删除客户“${row.name}”？关联手机会保留，只解除客户关系。`, '删除确认', { type: 'warning' })
    await api.delete(`/digital-employees/customers/${row.id}`)
    ElMessage.success('客户记录已删除')
    await refreshCoreData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.detail || '删除失败')
    }
  }
}

function openServiceDialog(row) {
  serviceCustomer.value = row
  serviceRecords.value = (row.service_records || []).map(record => ({
    ...record,
    is_done: Boolean(record.is_done),
    notes: record.notes || '',
    saving: false
  }))
  serviceDialog.value = true
}

async function saveServiceRecord(record, quiet = false) {
  if (!serviceCustomer.value?.id || record.saving) return
  record.saving = true
  try {
    const updated = await api.put(
      `/digital-employees/customers/${serviceCustomer.value.id}/service-records/${record.service_item_id}`,
      {
        is_done: record.is_done,
        notes: record.notes || ''
      }
    )
    Object.assign(record, updated, { saving: false })
    if (!quiet) ElMessage.success('服务进度已更新')
    await Promise.all([loadCustomers(), loadOverview()])
    serviceCustomer.value = customers.value.find(item => item.id === serviceCustomer.value?.id) || serviceCustomer.value
  } catch (error) {
    record.saving = false
    ElMessage.error(error?.response?.data?.detail || '服务进度保存失败')
  }
}

async function addServiceItem() {
  if (!newServiceItem.name.trim()) {
    ElMessage.warning('请填写服务内容')
    return
  }
  savingServiceItem.value = true
  try {
    await api.post('/digital-employees/service-items', {
      name: newServiceItem.name,
      description: newServiceItem.description
    })
    newServiceItem.name = ''
    newServiceItem.description = ''
    ElMessage.success('服务内容已添加')
    await Promise.all([loadServiceItems(), loadCustomers(), loadOverview()])
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '添加服务内容失败')
  } finally {
    savingServiceItem.value = false
  }
}

async function refreshCoreData() {
  await Promise.all([loadPhones(), loadCustomers()])
  await loadOverview()
}

function includesKeyword(values, keyword) {
  return values
    .filter(value => value !== null && value !== undefined && value !== '')
    .some(value => String(value).toLowerCase().includes(keyword))
}

function userName(user) {
  return user?.display_name || user?.username || '成员'
}

function conditionLabel(value) {
  return value === 'used' ? '二手' : '全新'
}

function statusMeta(value) {
  const map = {
    in_stock: { label: '库存', type: 'info' },
    assigned: { label: '员工持有', type: 'warning' },
    sold: { label: '已售/客户使用', type: 'success' }
  }
  return map[value] || { label: '未知', type: 'info' }
}

function paymentStatusMeta(value) {
  const map = {
    unpaid: { label: '未付款', type: 'info' },
    partial: { label: '部分付款', type: 'warning' },
    paid: { label: '已付款', type: 'success' },
    refunded: { label: '已退款', type: 'danger' }
  }
  return map[value] || { label: value || '未填写', type: 'info' }
}

function paymentMethodText(row) {
  const method = row.payment_method || '未填收款方式'
  const note = row.payment_note ? ` · ${row.payment_note}` : ''
  return `${method}${note}`
}

function serviceTimeText(row) {
  const start = row.service_start_at ? formatDate(row.service_start_at) : '未填开始'
  const end = row.service_end_at ? formatDate(row.service_end_at) : '未填结束'
  return `${start} 至 ${end}`
}

function serviceProgress(row) {
  const records = row.service_records || []
  if (!records.length) return 0
  const done = records.filter(record => record.is_done).length
  return Math.round((done / records.length) * 100)
}

function serviceProgressText(row) {
  const records = row.service_records || []
  const done = records.filter(record => record.is_done).length
  return `${done}/${records.length} 已完成`
}

function accountRows(row) {
  return [
    { label: '手机号', value: row.bound_phone },
    { label: '激活码', value: row.activation_code },
    { label: '抖音', value: row.douyin_account },
    { label: '小红书', value: row.xiaohongshu_account },
    { label: '微信', value: row.wechat_account },
    { label: '快手', value: row.kuaishou_account }
  ].filter(item => item.value)
}

function phoneOptionLabel(phone) {
  const serial = phone.serial_number ? ` · ${phone.serial_number}` : ''
  const customer = phone.customer?.name ? ` · 已关联 ${phone.customer.name}` : ''
  return `${phone.model} ${phone.memory}${serial}${customer}`
}

function formatDate(value) {
  return formatBusinessTime(value, 'YYYY-MM-DD HH:mm')
}
</script>

<style scoped>
.digital-overview-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 22px;
}

.overview-item {
  padding: 18px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
}

.overview-label {
  color: #64748b;
  font-size: 13px;
}

.overview-value {
  margin-top: 10px;
  color: #0f172a;
  font-size: 30px;
  font-weight: 800;
  line-height: 1;
}

.overview-meta {
  margin-top: 10px;
  color: #64748b;
  font-size: 12px;
}

.accent-blue {
  border-color: rgba(37, 99, 235, 0.16);
  background: #eff6ff;
}

.accent-green {
  border-color: rgba(22, 163, 74, 0.16);
  background: #f0fdf4;
}

.accent-amber {
  border-color: rgba(217, 119, 6, 0.16);
  background: #fffbeb;
}

.accent-rose {
  border-color: rgba(225, 29, 72, 0.16);
  background: #fff1f2;
}

.digital-panel {
  padding: 18px 18px 8px;
}

.digital-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.toolbar-search {
  width: min(360px, 100%);
}

.toolbar-count {
  color: #64748b;
  font-size: 13px;
  white-space: nowrap;
}

.main-cell {
  display: grid;
  gap: 6px;
}

.primary-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: #0f172a;
  font-weight: 700;
}

.primary-line.compact {
  font-size: 14px;
}

.item-meta,
.text-muted {
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.status-tag {
  min-width: 86px;
  justify-content: center;
}

.user-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 4px 10px;
  border-radius: 999px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 700;
}

.customer-link {
  color: #0f766e;
  font-weight: 700;
}

.account-stack,
.phone-chip-stack,
.service-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.account-stack {
  display: grid;
  color: #334155;
  font-size: 12px;
  line-height: 1.45;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.service-cell {
  display: grid;
  gap: 8px;
}

.service-progress-row {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.service-progress {
  width: 120px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.service-record-list {
  display: grid;
  gap: 12px;
}

.service-record-row {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  background: #f8fafc;
}

.record-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
}

.config-list {
  display: grid;
  gap: 10px;
  margin-bottom: 18px;
}

.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  background: #f8fafc;
}

.new-config-form {
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}

@media (max-width: 1180px) {
  .digital-overview-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .digital-overview-grid {
    grid-template-columns: 1fr;
  }

  .table-toolbar,
  .record-meta {
    align-items: flex-start;
    flex-direction: column;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
