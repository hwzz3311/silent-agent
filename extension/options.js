/**
 * Neurone 设置页面脚本
 */

const DEFAULT_PORT = 18792

// 常用网站预设列表
const PRESET_HOSTS = [
  { domain: 'baidu.com',        label: '百度' },
  { domain: 'google.com',       label: 'Google' },
  { domain: 'github.com',       label: 'GitHub' },
  { domain: 'zhihu.com',        label: '知乎' },
  { domain: 'bilibili.com',     label: 'B站' },
  { domain: 'xiaohongshu.com',  label: '小红书' },
  { domain: 'weibo.com',        label: '微博' },
  { domain: 'taobao.com',       label: '淘宝' },
  { domain: 'jd.com',           label: '京东' },
  { domain: 'douyin.com',       label: '抖音' },
  { domain: 'toutiao.com',      label: '头条' },
  { domain: 'douban.com',       label: '豆瓣' },
  { domain: 'csdn.net',         label: 'CSDN' },
  { domain: 'juejin.cn',        label: '掘金' },
  { domain: 'stackoverflow.com', label: 'StackOverflow' },
  { domain: 'wikipedia.org',    label: 'Wikipedia' },
  { domain: 'youtube.com',      label: 'YouTube' },
  { domain: 'twitter.com',      label: 'X/Twitter' },
]

// ==================== 端口配置 ====================

function clampPort(value) {
  const n = Number.parseInt(String(value || ''), 10)
  if (!Number.isFinite(n)) return DEFAULT_PORT
  if (n <= 0 || n > 65535) return DEFAULT_PORT
  return n
}

function updateRelayUrl(port) {
  const el = document.getElementById('relay-url')
  if (!el) return
  el.textContent = `ws://127.0.0.1:${port}/extension`
}

function setStatus(kind, message) {
  const el = document.getElementById('status')
  if (!el) return
  el.dataset.kind = kind || ''
  el.textContent = message || ''
}

function setPermStatus(kind, message) {
  const el = document.getElementById('perm-status')
  if (!el) return
  el.dataset.kind = kind || ''
  el.textContent = message || ''
}

async function checkRelayReachable(port) {
  const wsUrl = `ws://127.0.0.1:${port}/health-check`
  try {
    await new Promise((resolve, reject) => {
      const ws = new WebSocket(wsUrl)
      const t = setTimeout(() => { ws.close(); reject(new Error('timeout')) }, 2000)
      ws.onopen = () => { clearTimeout(t); ws.close(); resolve() }
      ws.onerror = () => { clearTimeout(t); reject(new Error('unreachable')) }
      ws.onclose = (ev) => {
        clearTimeout(t)
        if (ev.code === 1000) resolve()
        else reject(new Error('closed'))
      }
    })
    setStatus('ok', `✓ Relay 服务器已连接 (端口 ${port})`)
  } catch {
    setStatus('error', `✗ Relay 服务器未运行 (端口 ${port})。请先启动: python relay_server.py`)
  }
}

async function savePort() {
  const input = document.getElementById('port')
  const port = clampPort(input.value)
  await chrome.storage.local.set({ relayPort: port })
  input.value = String(port)
  updateRelayUrl(port)
  setStatus('', '已保存，正在检测连接...')
  await checkRelayReachable(port)
}

// ==================== 权限管理 ====================

/**
 * 将域名转换为 Chrome origin 匹配模式
 * baidu.com → ["*://*.baidu.com/*", "*://baidu.com/*"]
 */
function domainToOrigins(domain) {
  const d = domain.trim().replace(/^https?:\/\//, '').replace(/\/.*$/, '').replace(/^\*\./, '')
  if (!d) return []
  return [`*://*.${d}/*`, `*://${d}/*`]
}

/**
 * 从 origin 模式中提取可读域名
 * "*://*.baidu.com/*" → "*.baidu.com"
 */
function originToDisplay(origin) {
  return origin.replace(/^\*:\/\//, '').replace(/\/\*$/, '')
}

/**
 * 检查某个域名是否已被授权（包含在当前 origins 中）
 */
function isDomainGranted(domain, grantedOrigins) {
  const patterns = domainToOrigins(domain)
  return patterns.some(p => grantedOrigins.includes(p))
}

/**
 * 获取当前所有已授权的 origins
 */
async function getGrantedOrigins() {
  const perms = await chrome.permissions.getAll()
  return perms.origins || []
}

/**
 * 判断是否有全部网站权限
 */
function hasAllUrlsPermission(origins) {
  return origins.includes('<all_urls>') || origins.includes('*://*/*')
}

/**
 * 刷新整个权限 UI
 */
async function refreshPermissionsUI() {
  const origins = await getGrantedOrigins()
  const hasAll = hasAllUrlsPermission(origins)

  // 更新状态文字
  if (hasAll) {
    setPermStatus('ok', '✓ 已授权所有网站访问权限')
  } else if (origins.length) {
    setPermStatus('ok', `✓ 已授权 ${origins.length} 个源`)
  } else {
    setPermStatus('', '未授权任何额外网站（仅 localhost）')
  }

  // 渲染推荐网站标签
  renderPresets(origins, hasAll)

  // 渲染已授权列表
  renderHostList(origins, hasAll)
}

/**
 * 渲染推荐网站标签
 */
function renderPresets(grantedOrigins, hasAll) {
  const container = document.getElementById('host-presets')
  if (!container) return
  container.innerHTML = ''

  for (const { domain, label } of PRESET_HOSTS) {
    const granted = hasAll || isDomainGranted(domain, grantedOrigins)
    const tag = document.createElement('div')
    tag.className = 'host-preset' + (granted ? ' granted' : '')
    tag.innerHTML = `<span class="dot"></span>${label}<span style="opacity:0.5;font-size:11px">${domain}</span>`
    tag.title = granted ? `${domain} 已授权` : `点击授权 ${domain}`

    if (!granted) {
      tag.addEventListener('click', () => void addHostPermission(domain))
    }
    container.appendChild(tag)
  }
}

/**
 * 渲染已授权网站列表
 */
function renderHostList(grantedOrigins, hasAll) {
  const container = document.getElementById('host-list')
  if (!container) return
  container.innerHTML = ''

  // 合并 manifest 中的固定权限（host_permissions）
  // 这些不可移除，标记为"内置"
  const builtinOrigins = new Set(['http://127.0.0.1/*', 'http://localhost/*'])

  if (hasAll) {
    const item = document.createElement('div')
    item.className = 'host-item'
    item.innerHTML = `<code>&lt;all_urls&gt;</code><span class="host-all-badge">全部网站</span>`
    container.appendChild(item)
  }

  // 去重并排序
  const displayOrigins = [...new Set(grantedOrigins)]
    .filter(o => o !== '<all_urls>' && o !== '*://*/*')
    .sort()

  if (!displayOrigins.length && !hasAll) {
    container.innerHTML = '<div class="host-empty">暂无额外授权网站</div>'
    return
  }

  for (const origin of displayOrigins) {
    const display = originToDisplay(origin)
    const isBuiltin = builtinOrigins.has(origin)

    const item = document.createElement('div')
    item.className = 'host-item'

    let badges = ''
    if (isBuiltin) {
      badges = '<span class="host-badge" style="background: color-mix(in oklab, var(--accent-secondary) 15%, transparent); color: color-mix(in oklab, var(--accent-secondary) 85%, canvasText 15%);">内置</span>'
    }

    const removeBtn = isBuiltin
      ? ''
      : '<button class="host-remove" data-origin="">移除</button>'

    item.innerHTML = `<code>${display}</code>${badges}${removeBtn}`

    // 绑定移除事件
    const btn = item.querySelector('.host-remove')
    if (btn) {
      btn.dataset.origin = origin
      btn.addEventListener('click', () => void removeHostPermission(origin))
    }

    container.appendChild(item)
  }
}

// ==================== 权限操作 ====================

async function grantAllHosts() {
  try {
    const granted = await chrome.permissions.request({ origins: ['<all_urls>'] })
    if (granted) {
      setPermStatus('ok', '✓ 已授权所有网站访问权限')
    } else {
      setPermStatus('error', '✗ 用户拒绝了权限请求')
    }
  } catch (e) {
    setPermStatus('error', `✗ 权限请求失败: ${e.message}`)
  }
  await refreshPermissionsUI()
}

async function revokeAllHosts() {
  try {
    const origins = await getGrantedOrigins()
    const removable = origins.filter(o =>
      o !== 'http://127.0.0.1/*' && o !== 'http://localhost/*'
    )
    if (removable.length) {
      await chrome.permissions.remove({ origins: removable })
    }
    setPermStatus('', '已撤销所有额外权限')
  } catch (e) {
    setPermStatus('error', `✗ 撤销失败: ${e.message}`)
  }
  await refreshPermissionsUI()
}

async function addHostPermission(domain) {
  const origins = domainToOrigins(domain)
  if (!origins.length) {
    setPermStatus('error', '✗ 无效的域名')
    return
  }
  try {
    const granted = await chrome.permissions.request({ origins })
    if (granted) {
      setPermStatus('ok', `✓ 已授权 ${domain}`)
    } else {
      setPermStatus('error', `✗ 用户拒绝了 ${domain} 的权限请求`)
    }
  } catch (e) {
    setPermStatus('error', `✗ 授权失败: ${e.message}`)
  }
  await refreshPermissionsUI()
}

async function removeHostPermission(origin) {
  try {
    await chrome.permissions.remove({ origins: [origin] })
    setPermStatus('', `已移除 ${originToDisplay(origin)}`)
  } catch (e) {
    setPermStatus('error', `✗ 移除失败: ${e.message}`)
  }
  await refreshPermissionsUI()
}

async function addHostFromInput() {
  const input = document.getElementById('host-input')
  const raw = (input?.value || '').trim()
  if (!raw) {
    setPermStatus('error', '✗ 请输入域名')
    return
  }
  await addHostPermission(raw)
  if (input) input.value = ''
}

// ==================== 初始化 ====================

async function load() {
  const stored = await chrome.storage.local.get(['relayPort'])
  const port = clampPort(stored.relayPort)
  document.getElementById('port').value = String(port)
  updateRelayUrl(port)
  await checkRelayReachable(port)
  await refreshPermissionsUI()
}

// ==================== 事件绑定 ====================

document.getElementById('save').addEventListener('click', () => void savePort())
document.getElementById('port').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') void savePort()
})

document.getElementById('grant-all')?.addEventListener('click', () => void grantAllHosts())
document.getElementById('revoke-all')?.addEventListener('click', () => void revokeAllHosts())
document.getElementById('add-host')?.addEventListener('click', () => void addHostFromInput())
document.getElementById('host-input')?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') void addHostFromInput()
})

void load()
