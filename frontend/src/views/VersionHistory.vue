<template>
  <AppShell title="版本更新" description="查看系统版本号、更新摘要和完整历史，方便协作交接与部署对照。">
    <section class="version-hero panel">
      <div class="version-hero-top">
        <div>
          <div class="version-label">当前版本</div>
          <h2 class="version-title">{{ latestRelease.version }}</h2>
        </div>
        <div class="version-date">{{ latestRelease.date }}</div>
      </div>
      <div class="version-summary">{{ latestRelease.summary }}</div>
      <div class="version-meta">{{ latestRelease.title }}</div>
    </section>

    <section class="panel">
      <div class="history-header">
        <div>
          <h3 class="section-title">更新明细</h3>
          <div class="history-subtitle">按更新条目分页，每页 20 行，最近更新排在最前。</div>
        </div>
        <div class="history-count">共 {{ flattenedRows.length }} 条</div>
      </div>

      <div v-if="pagedRows.length" class="version-list">
        <div v-for="row in pagedRows" :key="row.key" class="version-row">
          <div class="version-row-meta">
            <span class="version-chip">{{ row.version }}</span>
            <span class="version-row-date">{{ row.date }}</span>
          </div>
          <div class="version-row-main">
            <div class="version-row-title">{{ row.title }}</div>
            <div class="version-row-detail">{{ row.detail }}</div>
          </div>
        </div>
      </div>
      <div v-else class="empty-card">还没有版本记录。</div>

      <div class="pagination-wrap">
        <el-pagination
          background
          layout="prev, pager, next"
          :total="flattenedRows.length"
          :page-size="pageSize"
          v-model:current-page="currentPage"
        />
      </div>
    </section>
  </AppShell>
</template>

<script setup>
import { computed, ref } from 'vue'
import AppShell from '@/components/AppShell.vue'
import { versionHistory } from '@/data/versionHistory'

const pageSize = 20
const currentPage = ref(1)

const latestRelease = computed(() => versionHistory[0] || {
  version: 'v0.01',
  date: '--',
  title: '初始化版本',
  summary: '暂无更新说明。'
})

const flattenedRows = computed(() =>
  versionHistory.flatMap(release =>
    (release.details || []).map((detail, index) => ({
      key: `${release.version}-${index}`,
      version: release.version,
      date: release.date,
      title: release.title,
      detail
    }))
  )
)

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return flattenedRows.value.slice(start, start + pageSize)
})
</script>

<style scoped>
.version-hero {
  margin-bottom: 20px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc 52%, #eefbf3);
}

.version-hero-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.version-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.version-title {
  margin: 8px 0 0;
  font-size: 36px;
  line-height: 1;
}

.version-date {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.version-summary {
  margin-top: 14px;
  font-size: 16px;
  color: #0f172a;
  line-height: 1.6;
}

.version-meta {
  margin-top: 10px;
  color: #64748b;
  font-size: 14px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
}

.history-subtitle,
.history-count {
  color: #64748b;
  font-size: 13px;
}

.version-list {
  display: grid;
  gap: 12px;
}

.version-row {
  display: flex;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

.version-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.version-row-meta {
  width: 126px;
  flex: 0 0 126px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.version-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.version-row-date {
  color: #64748b;
  font-size: 12px;
}

.version-row-main {
  min-width: 0;
  flex: 1;
}

.version-row-title {
  font-size: 15px;
  font-weight: 700;
}

.version-row-detail {
  margin-top: 6px;
  color: #475569;
  font-size: 14px;
  line-height: 1.7;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

@media (max-width: 900px) {
  .version-row {
    flex-direction: column;
  }

  .version-row-meta {
    width: auto;
    flex: none;
  }

  .history-header,
  .version-hero-top {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
