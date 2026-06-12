<template>
  <div class="index-dashboard">
    <div class="toolbar">
      <el-button type="primary" @click="refreshData" :loading="loading"><el-icon><Refresh /></el-icon>刷新最新指数</el-button>
      <span class="source-note">中国出口集装箱运价指数 CCFI · <a href="https://www.sse.net.cn/index/singleIndex?indexType=ccfi" target="_blank" rel="noopener">航交所官方单期页</a></span>
      <span v-if="fetchedAt" class="fetched-at">更新于 {{ fetchedAt }}</span>
      <el-tag v-if="dataStatus?.cacheFallback" type="warning" size="small" effect="plain" class="status-tag">
        {{ dataStatus.note }}
      </el-tag>
    </div>
    <el-row :gutter="20" class="row-margin">
      <el-col :xs="12" :sm="8" :md="6" :lg="4" v-for="idx in indices" :key="idx.code">
        <el-card class="index-card" shadow="hover">
          <div class="index-name">{{ idx.name }}</div>
          <div class="index-value">{{ idx.value }}</div>
          <div class="index-change" :class="idx.change >= 0 ? 'positive' : 'negative'">{{ idx.change >= 0 ? '+' : '' }}{{ idx.change }}%</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row class="row-margin">
      <el-col :span="24">
        <el-card class="chart-card" shadow="hover">
          <template #header><span class="title"><el-icon><TrendCharts /></el-icon>航运指数走势对比</span></template>
          <div class="chart-container"><v-chart :option="chartOption" autoresize /></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { TrendCharts, Refresh } from '@element-plus/icons-vue'
import extraApi from '@/api/extra'
import { pickDataStatus } from '@/composables/useDataStatus'

const indices = ref([])
const chartOption = ref({})
const loading = ref(false)
const fetchedAt = ref('')
const dataStatus = ref(null)

const formatTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
}

const loadData = async (refresh = false) => {
  loading.value = true
  try {
    const data = await extraApi.getIndices(refresh)
    indices.value = data.indices
    fetchedAt.value = formatTime(data.fetched_at)
    dataStatus.value = pickDataStatus(data)
    chartOption.value = {
      tooltip: { trigger: 'axis' },
      legend: { data: data.history.map(h => h.name) },
      xAxis: { type: 'category', data: data.dates },
      yAxis: { type: 'value', name: '指数值' },
      series: data.history.map(h => ({ name: h.name, type: 'line', data: h.values, smooth: true }))
    }
    if (refresh) {
      if (data.cache_fallback && data.data_note) ElMessage.warning(data.data_note)
      else if (data.live) ElMessage.success('已从航交所拉取最新指数')
      else if (data.data_note) ElMessage.info(data.data_note)
    }
  } catch (error) {
    console.error('加载指数数据失败', error)
    if (refresh) ElMessage.error('刷新失败')
  } finally {
    loading.value = false
  }
}

const refreshData = () => loadData(true)
onMounted(() => loadData(true))
</script>

<style scoped>
.index-dashboard { width: 100%; }
.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.source-note { font-size: 13px; color: #606266; }
.source-note a { color: #409eff; text-decoration: none; }
.fetched-at { font-size: 13px; color: #909399; }
.status-tag { max-width: 480px; white-space: normal; height: auto; line-height: 1.4; }
.row-margin { margin-bottom: 20px; }
.index-card { text-align: center; border-radius: 12px; }
.index-name { font-size: 14px; color: #666; margin-bottom: 8px; }
.index-value { font-size: 28px; font-weight: 700; color: #1a3a5c; }
.index-change { font-size: 14px; margin-top: 8px; }
.index-change.positive { color: #67c23a; }
.index-change.negative { color: #f56c6c; }
.chart-card { border-radius: 12px; }
.title { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.chart-container { height: 400px; }
</style>
