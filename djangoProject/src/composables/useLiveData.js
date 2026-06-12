/**
 * 进页面自动拉最新数据（refresh=1）。
 * 各业务页 onMounted 时调用 loader(true) 即可。
 */
import { onMounted } from 'vue'

export function useLiveOnMount(loader) {
  onMounted(() => {
    if (typeof loader === 'function') {
      loader(true)
    }
  })
}

export const NEWS_HOME_LIMIT = 8
