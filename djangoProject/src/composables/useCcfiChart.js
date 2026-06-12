/** 首页 CCFI 走势图：约 1.5 个月（6 个周度刻度，锚定航交所「本期」） */
export const CCFI_CHART_WEEKS = 6

/** 锁定区：仅虚线矩形框，无填充 */
const LOCKED_ZONE_STYLE = {
  color: 'transparent',
  borderColor: 'rgba(192, 196, 204, 0.85)',
  borderWidth: 1,
  borderType: 'dashed',
}

export function formatChartDateLabel(isoDate) {
  if (!isoDate) return ''
  const parts = String(isoDate).split('-')
  if (parts.length >= 3) {
    return `${parseInt(parts[1], 10)}.${parts[2]}`
  }
  return isoDate
}

/** 从「本期」日期往前推 weeks 个周度刻度（不用今天） */
export function buildWeeklyAxisFromAnchor(anchorDate, weeks = CCFI_CHART_WEEKS) {
  if (!anchorDate) return []
  const [y, m, d] = anchorDate.split('-').map(Number)
  const anchor = new Date(y, m - 1, d)
  const labels = []
  for (let i = weeks; i >= 0; i--) {
    const dt = new Date(anchor)
    dt.setDate(dt.getDate() - i * 7)
    labels.push(formatChartDateLabel(
      `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`
    ))
  }
  return labels
}

export function resolveChartErrorMessage(error) {
  const status = error?.response?.status
  if (status === 401) return '未登录无法查询！！！'
  if (status === 403) return '无权限查询指数数据'
  return error?.response?.data?.error || '指数数据无法查询'
}

/**
 * 锁定区右缘对齐 X 轴「上一期」刻度。
 * 微调：只改下面 endX 里的 - 0.5（越小越靠左，越大越靠右）。
 */
function buildLockedMarkAreas(series, axisData, meta = {}) {
  const prevIdx = meta.previous_period
    ? series.findIndex(p => p.date === meta.previous_period)
    : series.findIndex(p => p.public && !p.locked)

  if (prevIdx <= 0) return []

  const endX = prevIdx - 0.5

  return [[
    {
      xAxis: 0,
      itemStyle: LOCKED_ZONE_STYLE,
      label: {
        show: true,
        position: 'inside',
        formatter: '需登录查看\n航交所历史指数未公开',
        color: '#909399',
        fontSize: 12,
        lineHeight: 18,
      },
    },
    { xAxis: endX },
  ]]
}

function buildMessageBadge(message) {
  const cardW = 200
  const cardH = 52
  return [{
    type: 'group',
    left: 'center',
    top: 'middle',
    z: 10,
    children: [
      {
        type: 'rect',
        shape: { width: cardW, height: cardH, r: 10 },
        x: -cardW / 2,
        y: -cardH / 2,
        style: {
          fill: 'rgba(255, 255, 255, 0.95)',
          stroke: '#dcdfe6',
          lineWidth: 1,
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.06)',
        },
      },
      {
        type: 'text',
        style: {
          text: message,
          fontSize: 15,
          fontWeight: 600,
          fill: '#606266',
          textAlign: 'center',
          width: cardW,
        },
        x: -cardW / 2,
        y: -10,
      },
    ],
  }]
}

export function buildEmptyCcfiChartOption(message, anchorDate = null) {
  const axisData = buildWeeklyAxisFromAnchor(anchorDate)
  return {
    tooltip: { show: false },
    grid: { left: 52, right: 20, top: 36, bottom: 40, containLabel: false },
    graphic: message ? buildMessageBadge(message) : [],
    xAxis: {
      type: 'category',
      data: axisData,
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisTick: { alignWithLabel: true },
      axisLabel: { color: '#606266' },
    },
    yAxis: {
      type: 'value',
      name: 'CCFI 指数',
      nameTextStyle: { color: '#909399' },
      axisLine: { show: true, lineStyle: { color: '#dcdfe6' } },
      splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } },
    },
    series: [],
  }
}

export function buildCcfiChartOption(historicalPayload) {
  const series = historicalPayload?.series || historicalPayload || []
  const hasLocked = series.some(p => p.locked)

  const axisData = series.map(p => formatChartDateLabel(p.date))
  const values = series.map(p => (p.value != null ? p.value : null))
  const markAreaData = hasLocked
    ? buildLockedMarkAreas(series, axisData, {
      previous_period: historicalPayload?.previous_period,
      current_period: historicalPayload?.current_period,
    })
    : []

  const lineSeries = {
    type: 'line',
    data: values,
    connectNulls: false,
    smooth: false,
    showSymbol: true,
    symbolSize: (val, params) => (series[params.dataIndex]?.public ? 9 : 0),
    z: 2,
    areaStyle: { opacity: 0.12, color: '#2c5a8c' },
    lineStyle: { color: '#2c5a8c', width: 2 },
    itemStyle: { color: '#1a3a5c', borderColor: '#fff', borderWidth: 2 },
  }

  if (markAreaData.length) {
    lineSeries.markArea = {
      silent: true,
      z: 1,
      data: markAreaData,
    }
  }

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#ebeef5',
      textStyle: { color: '#606266', fontSize: 13 },
      formatter(params) {
        const p = params[0]
        const idx = p?.dataIndex
        if (!p || p.value == null) {
          return `<div style="line-height:1.6">
            <strong>${p?.axisValue}</strong><br/>
            <span style="color:#909399">— 需登录航交所查看 —</span>
          </div>`
        }
        const tag = series[idx]?.public ? '公开数据' : ''
        return `<div style="line-height:1.6">
          <strong>${p.axisValue}</strong>
          <span style="color:#67c23a;font-size:11px;margin-left:6px">${tag}</span><br/>
          CCFI 指数：<strong>${p.value}</strong>
        </div>`
      },
    },
    grid: { left: 52, right: 20, top: 36, bottom: 40, containLabel: false },
    xAxis: {
      type: 'category',
      data: axisData,
      boundaryGap: true,
      axisLabel: { color: '#606266' },
      axisLine: { lineStyle: { color: '#dcdfe6' } },
    },
    yAxis: {
      type: 'value',
      name: 'CCFI 指数',
      nameTextStyle: { color: '#909399' },
      splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } },
      scale: true,
    },
    series: [lineSeries],
  }
}

/** 对比页等小图复用 locked 区样式 */
export function buildCompareLineSeries(historical) {
  const series = historical || []
  const axisData = series.map(p => formatChartDateLabel(p.date))
  const values = series.map(p => (p.value != null ? p.value : null))
  const hasLocked = series.some(p => p.locked)
  const markAreaData = hasLocked
    ? buildLockedMarkAreas(series, axisData, {
      previous_period: historical?.previous_period,
      current_period: historical?.current_period,
    })
    : []

  const cfg = {
    type: 'line',
    data: values,
    connectNulls: false,
    smooth: false,
    showSymbol: true,
    symbolSize: (val, params) => (series[params.dataIndex]?.public ? 7 : 0),
    areaStyle: { opacity: 0.15 },
    lineStyle: { width: 2 },
  }
  if (markAreaData.length) {
    cfg.markArea = { silent: true, z: 1, data: markAreaData }
  }
  return { axisData, values, seriesConfig: cfg }
}
