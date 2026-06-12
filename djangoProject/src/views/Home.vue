<template>
  <div class="home">
    <!-- CCFI 指数图表（全宽） -->
    <el-row :gutter="20" class="row-margin">
      <el-col :span="24">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <div class="card-header-main">
                <span class="title"><el-icon><Ship /></el-icon>CCFI 分航线指数</span>
                <div class="header-subtitle">
                  中国出口集装箱运价指数 · 数据来源：
                  <a href="https://www.sse.net.cn/index/singleIndex?indexType=ccfi" target="_blank" rel="noopener">上海航运交易所</a>
                </div>
              </div>
              <div class="header-toolbar">
                <el-select
                  v-model="selectedRouteLabel"
                  placeholder="选择 CCFI 航线"
                  size="small"
                  class="route-select"
                  @change="onRouteChange"
                >
                  <el-option
                    v-for="route in routeOptions"
                    :key="route.route_label"
                    :label="route.route_label"
                    :value="route.route_label"
                  />
                </el-select>
                <el-button size="small" @click="refreshFreightData" :loading="freightLoading">
                  <el-icon><Refresh /></el-icon>刷新最新
                </el-button>
              </div>
              <div class="header-meta">
                <span v-if="lastFetchedAt" class="meta-tag">更新于 {{ lastFetchedAt }}</span>
                <span class="meta-tag muted">近 1.5 个月 · 仅公开本期/上期</span>
                <el-tag v-if="freightDataStatus?.cacheFallback" type="warning" size="small" effect="plain" class="status-tag">
                  {{ freightDataStatus.note }}
                </el-tag>
                <el-tag v-else-if="freightDataStatus?.note" type="info" size="small" effect="plain" class="status-tag">
                  {{ freightDataStatus.note }}
                </el-tag>
              </div>
            </div>
          </template>
          <div class="chart-wrap">
            <v-chart class="chart-canvas" :option="freightChartOption" autoresize />
            <div v-if="chartHasLockedZone" class="chart-legend">
              <span class="legend-item"><i class="dot dot-open" />公开：本期 / 上期</span>
              <span class="legend-item"><i class="dot dot-locked" />需登录航交所</span>
            </div>
          </div>
          <div class="current-rate" v-if="currentRate">
            <div class="rate-grid">
              <div class="rate-item">
                <span>{{ currentRate.route_label }}</span>
                <strong>{{ currentRate.index_value }}</strong>
              </div>
              <div class="rate-item">
                <span>上期指数</span>
                <strong>{{ currentRate.index_previous ?? '—' }}</strong>
              </div>
              <div class="rate-item">
                <span>环比</span>
                <strong>{{ currentRate.change_pct != null ? currentRate.change_pct + '%' : '—' }}</strong>
              </div>
              <div class="rate-item" v-if="currentRate.current_period">
                <span>本期日期</span>
                <strong>{{ currentRate.current_period }}</strong>
              </div>
              <div class="rate-item composite" v-if="currentRate.composite_current">
                <span>CCFI 综合</span>
                <strong>{{ currentRate.composite_current }}</strong>
              </div>
              <div class="rate-item trend" :class="currentRate.trend">
                <span>走势</span>
                <strong class="trend-val">
                  <el-icon><component :is="currentRate.trend === 'up' ? 'ArrowUp' : currentRate.trend === 'down' ? 'ArrowDown' : 'Minus'" /></el-icon>
                  {{ currentRate.trend === 'up' ? '上涨' : currentRate.trend === 'down' ? '下跌' : '平稳' }}
                </strong>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- CCFI 分航线指数一览（全宽，在图表下方） -->
    <el-row :gutter="20" class="row-margin">
      <el-col :span="24">
        <el-card class="chart-card ranking-card" shadow="hover">
          <template #header>
            <div class="card-header card-header--compact">
              <div class="card-header-main">
                <span class="title"><el-icon><Histogram /></el-icon>CCFI 分航线指数一览</span>
              </div>
              <div class="header-toolbar">
                <span v-if="ccfiTable.current_period" class="meta-tag">本期 {{ ccfiTable.current_period }}</span>
                <el-button size="small" @click="showFullRanking">
                  <el-icon><ArrowRight /></el-icon>完整一览
                </el-button>
              </div>
            </div>
          </template>
          <div v-if="ccfiTable.composite_current" class="composite-bar">
            <span>CCFI 综合指数</span>
            <strong>{{ ccfiTable.composite_current }}</strong>
            <em v-if="ccfiTable.composite_change_pct != null">{{ ccfiTable.composite_change_pct >= 0 ? '+' : '' }}{{ ccfiTable.composite_change_pct }}%</em>
          </div>
          <div class="ranking-list">
            <div v-for="(route, idx) in ccfiPreview" :key="route.route_label" class="ranking-item" @click="selectRouteFromList(route.route_label)">
              <div class="rank" :class="getRankClass(idx + 1)">{{ idx + 1 }}</div>
              <div class="port-info">
                <span class="port-name">{{ route.route_label }}</span>
                <span class="growth" :class="(route.change_pct ?? 0) >= 0 ? 'positive' : 'negative'">{{ route.change_pct != null ? ((route.change_pct >= 0 ? '+' : '') + route.change_pct + '%') : '—' }}</span>
              </div>
              <div class="throughput">{{ route.index_value }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二行：快捷入口 -->
    <el-row :gutter="20" class="row-margin">
      <el-col :span="24">
        <el-card class="quick-card" shadow="hover">
          <div class="quick-links">
            <div class="quick-item" @click="$router.push('/compare')"><el-icon><DataLine /></el-icon><span>指数对比</span><em>对比多航线 CCFI 指数</em></div>
            <div class="quick-item" @click="$router.push('/predict')"><el-icon><TrendCharts /></el-icon><span>智能预测</span><em>基于 CCFI 指数预测走势</em></div>
            <div class="quick-item" @click="$router.push('/schedule')"><el-icon><Calendar /></el-icon><span>船期查询</span><em>查询最新船期</em></div>
            <div class="quick-item" @click="$router.push('/indices')"><el-icon><PieChart /></el-icon><span>航运指数</span><em>市场风向标</em></div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 下半部分：航运热点新闻 -->
    <el-row class="row-margin">
      <el-col :span="24">
        <el-card class="news-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="title"><el-icon><Reading /></el-icon>航运热点新闻</span>
              <div class="header-controls">
                <span class="news-count">来源 <a href="http://www.ship.sh/" target="_blank" rel="noopener">航运界</a> · 库内 {{ newsTotal }} 条 · 展示 {{ newsList.length }} 条</span>
                <el-tag v-if="newsDataStatus?.cacheFallback" type="warning" size="small" effect="plain" class="status-tag">
                  {{ newsDataStatus.note }}
                </el-tag>
                <el-button size="small" @click="refreshNews" :loading="newsLoading"><el-icon><Refresh /></el-icon>拉取最新</el-button>
              </div>
            </div>
          </template>
          <div class="news-list">
            <div v-for="news in newsList" :key="news.id" class="news-item" @click="viewNewsDetail(news)">
              <div class="news-icon" :class="`impact-${news.impact}`"><el-icon><Document /></el-icon></div>
              <div class="news-content">
                <div class="news-title"><span class="category-tag" :class="`category-${news.category}`">{{ news.category }}</span>{{ news.title }}</div>
                <div class="news-summary">{{ news.summary }}</div>
                <div class="news-meta"><span><el-icon><Clock /></el-icon> {{ formatTime(news.publish_time) }}</span><span><el-icon><View /></el-icon> {{ news.views }} 阅读</span><span>来源：{{ news.source }}</span></div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- CCFI 完整一览对话框（与航交所单期页一致） -->
    <el-dialog v-model="rankingDialogVisible" title="CCFI 分航线指数完整一览" width="80%">
      <div class="dialog-header">
        <span v-if="ccfiTable.current_period">本期 {{ ccfiTable.current_period }}</span>
        <span v-if="ccfiTable.previous_period"> · 上期 {{ ccfiTable.previous_period }}</span>
        <el-button type="primary" link @click="loadCcfiTable(true)" :loading="ccfiTableLoading">刷新</el-button>
      </div>
      <el-table :data="ccfiTableAllRows" stripe style="width: 100%">
        <el-table-column type="index" label="序号" width="70" />
        <el-table-column prop="route_label" label="航线" min-width="180" />
        <el-table-column prop="index_previous" label="上期指数" sortable width="120" />
        <el-table-column prop="index_value" label="本期指数" sortable width="120" />
        <el-table-column prop="change_pct" label="环比 (%)" sortable width="120">
          <template #default="{ row }">
            <span :style="{ color: (row.change_pct ?? 0) >= 0 ? '#f56c6c' : '#67c23a' }">
              {{ row.change_pct != null ? ((row.change_pct >= 0 ? '+' : '') + row.change_pct + '%') : '—' }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 新闻详情对话框 -->
    <el-dialog v-model="newsDialogVisible" :title="currentNews?.title" width="60%">
      <div v-if="currentNews" class="news-detail">
        <div class="news-detail-meta"><span><el-icon><Clock /></el-icon> {{ formatTime(currentNews.publish_time) }}</span><span><el-icon><View /></el-icon> {{ currentNews.views }} 阅读</span><span>来源：{{ currentNews.source }}</span><span class="category-tag" :class="`category-${currentNews.category}`">{{ currentNews.category }}</span></div>
        <div class="news-detail-summary">{{ currentNews.summary }}</div>
        <div class="news-detail-content">{{ currentNews.content }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent, GraphicComponent, MarkAreaComponent } from 'echarts/components'
import { Ship, Histogram, Reading, Refresh, ArrowRight, Document, Clock, View, ArrowUp, ArrowDown, Minus, DataLine, TrendCharts, Calendar, PieChart } from '@element-plus/icons-vue'
import freightApi from '@/api/freight'
import newsApi from '@/api/news'
import { NEWS_HOME_LIMIT } from '@/composables/useLiveData'
import { pickDataStatus } from '@/composables/useDataStatus'
import {
  buildEmptyCcfiChartOption,
  buildCcfiChartOption,
  resolveChartErrorMessage,
} from '@/composables/useCcfiChart'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, GraphicComponent, MarkAreaComponent])

const selectedRouteLabel = ref('')
const routeOptions = ref([])
const freightLoading = ref(false)
const currentRate = ref(null)
const freightChartOption = ref(buildEmptyCcfiChartOption(''))
const ccfiTable = ref({ routes: [], composite_current: null, composite_change_pct: null, current_period: null, previous_period: null })
const ccfiTableLoading = ref(false)
const rankingDialogVisible = ref(false)
const ccfiPreview = computed(() => (ccfiTable.value.routes || []).slice(0, 8))
const ccfiTableAllRows = computed(() => {
  const rows = [...(ccfiTable.value.routes || [])]
  if (ccfiTable.value.composite_current != null) {
    rows.unshift({
      route_label: '中国出口集装箱运价综合指数',
      index_previous: ccfiTable.value.composite_previous,
      index_value: ccfiTable.value.composite_current,
      change_pct: ccfiTable.value.composite_change_pct,
    })
  }
  return rows
})
const newsList = ref([])
const newsTotal = ref(0)
const newsLoading = ref(false)
const newsDialogVisible = ref(false)
const currentNews = ref(null)
const lastFetchedAt = ref('')
const freightDataStatus = ref(null)
const newsDataStatus = ref(null)
const chartHasLockedZone = ref(false)

const formatTime = (time) => { const date = new Date(time); const diff = Date.now() - date; if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'; if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'; return `${date.getMonth() + 1}/${date.getDate()}` }
const getRankClass = (rank) => rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : ''

const loadCcfiTable = async (refresh = false) => {
  ccfiTableLoading.value = true
  try {
    ccfiTable.value = await freightApi.getCcfiRouteTable(refresh)
  } catch (error) {
    console.error('加载 CCFI 一览失败', error)
    if (refresh) ElMessage.error('CCFI 分航线指数拉取失败')
  } finally { ccfiTableLoading.value = false }
}
const selectRouteFromList = (routeLabel) => {
  selectedRouteLabel.value = routeLabel
  loadFreightData(true)
}
const showFullRanking = () => { rankingDialogVisible.value = true; loadCcfiTable(true) }

const loadCcfiRoutes = async () => {
  try {
    const routes = await freightApi.getCcfiRoutes()
    routeOptions.value = routes
    if (routes.length) selectedRouteLabel.value = routes.find(r => r.route_label === '欧洲航线')?.route_label || routes[0].route_label
  } catch (error) { console.error('加载 CCFI 航线失败', error) }
}
const formatFetchedAt = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
}

const loadFreightData = async (refresh = false) => {
  if (!selectedRouteLabel.value) return
  const token = localStorage.getItem('token')
  if (!token) {
    currentRate.value = null
    freightChartOption.value = buildEmptyCcfiChartOption('未登录无法查询！！！', ccfiTable.value.current_period)
    return
  }
  freightLoading.value = true
  try {
    const [rate, historicalPayload] = await Promise.all([
      freightApi.getRealtimeRate(selectedRouteLabel.value, refresh),
      freightApi.getHistoricalRates(selectedRouteLabel.value, refresh)
    ])
    currentRate.value = rate
    lastFetchedAt.value = formatFetchedAt(rate.fetched_at)
    freightDataStatus.value = pickDataStatus(rate)
    freightChartOption.value = buildCcfiChartOption(historicalPayload)
    chartHasLockedZone.value = (historicalPayload?.series || []).some(p => p.locked)
    if (refresh) {
      if (rate.cache_fallback && rate.data_note) ElMessage.warning(rate.data_note)
      else if (rate.live) ElMessage.success('已从航交所拉取最新 CCFI 分航线指数')
      else if (rate.data_note) ElMessage.info(rate.data_note)
    }
  } catch (error) {
    console.error('加载指数数据失败', error)
    currentRate.value = null
    freightChartOption.value = buildEmptyCcfiChartOption(
      resolveChartErrorMessage(error),
      ccfiTable.value.current_period || currentRate.value?.current_period
    )
    const msg = error.response?.data?.error || resolveChartErrorMessage(error)
    if (refresh) ElMessage.error(msg)
  } finally { freightLoading.value = false }
}
const refreshFreightData = async () => {
  await Promise.all([loadFreightData(true), loadCcfiTable(true)])
}
const onRouteChange = () => loadFreightData(true)
const loadNews = async (refresh = false) => {
  try {
    const data = await newsApi.getNewsList(NEWS_HOME_LIMIT, 0, refresh)
    newsList.value = data.news
    newsTotal.value = data.total
    newsDataStatus.value = pickDataStatus(data)
    if (refresh) {
      if (data.cache_fallback && data.data_note) ElMessage.warning(data.data_note)
      else if (data.new_count > 0) ElMessage.success(`新增 ${data.new_count} 条，库内累计 ${data.total} 条`)
      else if (data.data_note) ElMessage.info(data.data_note)
    }
  } catch (error) { console.error('加载新闻失败', error); if (refresh) ElMessage.error('新闻同步失败') }
}
const refreshNews = async () => {
  newsLoading.value = true
  try { await loadNews(true) } finally { newsLoading.value = false }
}
const viewNewsDetail = (news) => { currentNews.value = news; newsDialogVisible.value = true }

const initPage = async () => {
  await loadCcfiRoutes()
  newsLoading.value = true
  await Promise.all([
    loadFreightData(true),
    loadCcfiTable(true),
    loadNews(true),
  ])
  newsLoading.value = false
}
onMounted(initPage)
</script>

<style scoped>
.home { width: 100%; }
.row-margin { margin-bottom: 20px; }
.chart-card, .news-card, .quick-card { border-radius: 12px; }

.card-header {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  gap: 10px 16px;
  align-items: center;
}
.card-header--compact { grid-template-rows: auto; }
.card-header-main { grid-column: 1; min-width: 0; }
.card-header .title {
  font-size: 16px;
  font-weight: 600;
  color: #1a3a5c;
  display: flex;
  align-items: center;
  gap: 8px;
}
.header-subtitle { font-size: 12px; color: #909399; margin-top: 4px; line-height: 1.5; }
.header-subtitle a { color: #409eff; text-decoration: none; }
.header-toolbar {
  grid-column: 2;
  grid-row: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.header-meta { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; }
.route-select { width: 220px; }
.meta-tag {
  font-size: 12px;
  color: #606266;
  background: #f4f4f5;
  padding: 2px 10px;
  border-radius: 4px;
  white-space: nowrap;
}
.meta-tag.muted { color: #909399; background: #fafafa; }
.status-tag { max-width: 420px; white-space: normal; height: auto; line-height: 1.4; padding: 4px 8px; }

.chart-wrap { position: relative; height: 340px; margin-bottom: 4px; }
.chart-canvas { width: 100%; height: 300px; }
.chart-legend {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  padding: 0 4px;
  font-size: 11px;
  color: #909399;
}
.legend-item { display: inline-flex; align-items: center; gap: 6px; }
.dot { display: inline-block; width: 12px; height: 12px; border-radius: 2px; flex-shrink: 0; }
.dot-open { background: #2c5a8c; }
.dot-locked {
  background: transparent;
  border: 1px dashed #c0c4cc;
}

.current-rate { margin-top: 12px; padding: 14px 12px; background: #f5f7fa; border-radius: 8px; }
.rate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(88px, 1fr));
  gap: 12px 8px;
}
.rate-item { text-align: center; }
.rate-item span { font-size: 12px; color: #666; display: block; margin-bottom: 4px; }
.rate-item strong { font-size: 18px; color: #1a3a5c; font-weight: 700; }
.rate-item.composite strong { color: #e6a23c; }
.rate-item.trend.up .trend-val { color: #f56c6c; }
.rate-item.trend.down .trend-val { color: #67c23a; }
.rate-item.trend.stable .trend-val { color: #909399; }
.trend-val { display: inline-flex; align-items: center; justify-content: center; gap: 4px; font-size: 16px !important; }

.ranking-list { max-height: 300px; overflow-y: auto; }
.ranking-item { display: flex; align-items: center; padding: 12px 8px; border-bottom: 1px solid #ebeef5; cursor: pointer; }
.ranking-item:hover { background-color: #f5f7fa; }
.composite-bar { display: flex; align-items: center; gap: 12px; padding: 10px 12px; margin-bottom: 8px; background: #fdf6ec; border-radius: 8px; font-size: 13px; color: #666; }
.composite-bar strong { font-size: 20px; color: #e6a23c; }
.composite-bar em { font-style: normal; color: #f56c6c; font-weight: 500; }

.header-controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.news-count { font-size: 13px; color: #999; white-space: nowrap; }
.news-count a { color: #409eff; text-decoration: none; }
.dialog-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; font-size: 14px; color: #606266; }
.rank { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-weight: 600; border-radius: 8px; background: #f0f2f5; margin-right: 12px; flex-shrink: 0; }
.rank.gold { background: linear-gradient(135deg, #ffd700, #ffb347); color: white; }
.rank.silver { background: linear-gradient(135deg, #c0c0c0, #a8a8a8); color: white; }
.rank.bronze { background: linear-gradient(135deg, #cd7f32, #b87333); color: white; }
.port-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.port-name { font-weight: 500; }
.growth { font-size: 12px; }
.growth.positive { color: #f56c6c; }
.growth.negative { color: #67c23a; }
.throughput { font-weight: 600; color: #1a3a5c; flex-shrink: 0; }

.quick-links { display: flex; justify-content: space-around; flex-wrap: wrap; gap: 8px; padding: 16px 0; }
.quick-item { text-align: center; cursor: pointer; padding: 16px 24px; border-radius: 12px; transition: all 0.3s; flex: 1; min-width: 140px; }
.quick-item:hover { background: #f0f2f5; transform: translateY(-4px); }
.quick-item .el-icon { font-size: 32px; color: #2c5a8c; display: block; margin-bottom: 8px; }
.quick-item span { display: block; font-weight: 600; margin-bottom: 4px; }
.quick-item em { font-size: 12px; color: #999; font-style: normal; }

.news-list { display: flex; flex-direction: column; gap: 16px; }
.news-item { display: flex; gap: 16px; padding: 16px; border-radius: 12px; background: #fafafa; cursor: pointer; transition: all 0.3s; }
.news-item:hover { background: #f0f2f5; transform: translateX(4px); }
.news-icon { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 12px; background: #e8f4f8; color: #2c5a8c; flex-shrink: 0; }
.news-icon.impact-high { background: #ffebee; color: #f56c6c; }
.news-content { flex: 1; min-width: 0; }
.news-title { font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.category-tag { font-size: 12px; padding: 2px 8px; border-radius: 4px; }
.category-行业动态, .category-市场分析 { background: #e8f4f8; color: #2c5a8c; }
.category-港口新闻 { background: #e8f5e9; color: #67c23a; }
.category-运价动态 { background: #ffebee; color: #f56c6c; }
.category-政策法规 { background: #fff3e0; color: #e6a23c; }
.category-技术创新 { background: #f3e5f5; color: #9c27b0; }
.news-summary { font-size: 13px; color: #666; margin-bottom: 8px; line-height: 1.5; }
.news-meta { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: #999; }
.news-meta span { display: flex; align-items: center; gap: 4px; }
.news-detail-meta { display: flex; gap: 20px; flex-wrap: wrap; padding-bottom: 16px; margin-bottom: 16px; border-bottom: 1px solid #ebeef5; color: #666; font-size: 13px; }
.news-detail-summary { font-size: 16px; color: #333; line-height: 1.6; margin-bottom: 20px; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.news-detail-content { font-size: 14px; color: #555; line-height: 1.8; }

@media (max-width: 768px) {
  .card-header { grid-template-columns: 1fr; }
  .header-toolbar { grid-column: 1; justify-content: flex-start; }
  .route-select { width: 100%; }
}
</style>