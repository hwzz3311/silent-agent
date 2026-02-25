/**
 * SilentAgent Popup 脚本
 *
 * 处理 popup 界面的交互：显示密钥、连接状态、配置和授权
 */

// 常量
const STORAGE_CONFIG = 'connection_config'
const STORAGE_STATUS = 'server_status'
const STORAGE_SECRET_KEY = 'secret_key'

// 元素引用
const elements = {
  statusDot: document.getElementById('statusDot'),
  statusText: document.getElementById('statusText'),
  secretKey: document.getElementById('secretKey'),
  copyKey: document.getElementById('copyKey'),
  hostInput: document.getElementById('hostInput'),
  portInput: document.getElementById('portInput'),
  connectBtn: document.getElementById('connectBtn'),
  disconnectBtn: document.getElementById('disconnectBtn'),
  authSection: document.getElementById('authSection'),
  currentUrl: document.getElementById('currentUrl'),
  authDot: document.getElementById('authDot'),
  authText: document.getElementById('authText'),
  authBtn: document.getElementById('authBtn'),
  openSettings: document.getElementById('openSettings'),
  toast: document.getElementById('toast'),
}

// 显示提示消息
function showToast(message) {
  elements.toast.textContent = message
  elements.toast.classList.add('show')
  setTimeout(() => {
    elements.toast.classList.remove('show')
  }, 2000)
}

// 获取存储的配置
async function getConfig() {
  const [config, status, key] = await Promise.all([
    chrome.storage.local.get([STORAGE_CONFIG]),
    chrome.storage.local.get([STORAGE_STATUS]),
    chrome.storage.local.get([STORAGE_SECRET_KEY]),
  ])

  return {
    host: config[STORAGE_CONFIG]?.host || '127.0.0.1',
    port: config[STORAGE_CONFIG]?.port || config[STORAGE_CONFIG]?.relayPort || 18792,
    autoReconnect: config[STORAGE_CONFIG]?.autoReconnect ?? true,
    secretKey: key[STORAGE_SECRET_KEY] || null,
    connected: status[STORAGE_STATUS]?.connected || false,
    serverUrl: status[STORAGE_STATUS]?.serverUrl || '',
  }
}

// 更新连接状态显示
function updateConnectionStatus(connected, connecting = false) {
  if (connecting) {
    elements.statusDot.className = 'status-dot connecting'
    elements.statusText.textContent = '连接中...'
    elements.connectBtn.disabled = true
    elements.disconnectBtn.disabled = true
  } else if (connected) {
    elements.statusDot.className = 'status-dot connected'
    elements.statusText.textContent = '已连接'
    elements.connectBtn.disabled = true
    elements.disconnectBtn.disabled = false
  } else {
    elements.statusDot.className = 'status-dot'
    elements.statusText.textContent = '未连接'
    elements.connectBtn.disabled = false
    elements.disconnectBtn.disabled = true
  }
}

// 更新密钥显示
function updateSecretKey(key) {
  if (key) {
    elements.secretKey.textContent = key
  } else {
    elements.secretKey.textContent = '未生成'
  }
}

// 获取当前活动标签页
async function getCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  return tab
}

// 获取主域名（如 github.io from pinduoduo-sdk.github.io）
function getMainDomain(hostname) {
  const parts = hostname.split('.')
  // 考虑常见的多级域名：com.cn, com.hk 等
  if (parts.length <= 2) {
    return hostname
  }
  // 取最后两个部分作为主域名
  return parts.slice(-2).join('.')
}

// 检查当前页面是否已授权
async function checkCurrentPageAuth(tab) {
  if (!tab || !tab.url) {
    return { granted: false, url: '' }
  }

  try {
    const url = new URL(tab.url)
    // 检查是否是特殊页面
    if (url.protocol === 'chrome-extension:' ||
        url.protocol === 'chrome:' ||
        url.protocol === 'about:') {
      return { granted: false, url: '浏览器特殊页面', isSpecial: true }
    }

    const urlStr = url.origin
    const hostname = url.hostname
    const mainDomain = getMainDomain(hostname)  // 获取主域名

    const perms = await chrome.storage.local.get('hostPermissions')
    const allHosts = (perms && perms.hostPermissions) || []

    // 检查是否授权所有网站
    const allGranted = allHosts.includes('<all_urls>') || allHosts.includes('*://*/*')

    // 检查具体域名 - 使用主域名匹配
    const domainGranted = allHosts.some(host => {
      if (host.includes('*')) {
        // 通配符匹配：*://*.baidu.com/* 匹配 *.baidu.com
        const pattern = host.replace(/\./g, '\\.').replace(/\*/g, '.*')
        return new RegExp(pattern).test(urlStr) ||
               new RegExp(pattern).test(hostname) ||
               new RegExp(pattern).test(mainDomain)
      }
      // 提取权限中的域名并匹配主域名
      const hostParts = host.replace('*://*.', '').replace('/*', '').split('.')
      const hostMainDomain = hostParts.slice(-2).join('.')
      // 主域名匹配：baidu.com 匹配 baidu.com, *.baidu.com
      return mainDomain === hostMainDomain || hostname.includes(hostMainDomain)
    })

    return {
      granted: allGranted || domainGranted,
      url: tab.url,
      hostname: hostname,
      mainDomain: mainDomain,
    }
  } catch (e) {
    console.error('[Popup] 检查授权失败:', e)
    return { granted: false, url: tab.url }
  }
}

// 更新授权状态显示
function updateAuthStatus(info) {
  elements.currentUrl.textContent = info.url || '无法获取'

  if (info.isSpecial) {
    elements.authDot.className = 'status-dot'
    elements.authText.textContent = '特殊页面'
    elements.authText.className = 'auth-status'
    elements.authBtn.disabled = true
    elements.authBtn.textContent = '无法授权'
    elements.authBtn.className = 'btn-auth'
  } else if (info.granted) {
    elements.authDot.className = 'status-dot connected'
    elements.authText.textContent = '已授权'
    elements.authText.className = 'auth-status auth-granted'
    elements.authBtn.textContent = '撤销授权'
    elements.authBtn.className = 'btn-auth granted'
    elements.authBtn.disabled = false
  } else {
    elements.authDot.className = 'status-dot'
    elements.authText.textContent = '未授权'
    elements.authText.className = 'auth-status auth-not-granted'
    elements.authBtn.textContent = '授权当前页面'
    elements.authBtn.className = 'btn-auth'
    elements.authBtn.disabled = false
  }
}

// 授权当前页面（使用主域名匹配）
async function authorizeCurrentPage(tab) {
  if (!tab || !tab.url) return

  try {
    const url = new URL(tab.url)
    const hostname = url.hostname
    const mainDomain = getMainDomain(hostname)  // 获取主域名

    // 获取当前权限
    const perms = await chrome.storage.local.get('hostPermissions')
    const allHosts = (perms && perms.hostPermissions) || []

    // 添加主域名权限（匹配该主域名下所有子域名和路径）
    // 例如：pinduoduo-sdk.github.io -> *://*.github.io/*
    const newHost = `*://*.${mainDomain}/*`

    // 检查是否已存在相同主域名的权限
    const existingMainDomain = allHosts.some(h => {
      if (h.includes('*')) {
        const hostMain = getMainDomain(h.replace('*://*.', '').replace('/*', ''))
        return hostMain === mainDomain
      }
      return false
    })

    if (!existingMainDomain && !allHosts.includes('<all_urls>')) {
      allHosts.push(newHost)
      await chrome.storage.local.set({ hostPermissions: allHosts })
    }

    showToast(`已授权 ${mainDomain} 域名`)
    // 刷新授权状态
    const info = await checkCurrentPageAuth(tab)
    updateAuthStatus(info)
  } catch (e) {
    console.error('[Popup] 授权失败:', e)
    showToast('授权失败: ' + e.message)
  }
}

// 撤销当前页面授权（使用主域名匹配）
async function revokeCurrentPage(tab) {
  if (!tab || !tab.url) return

  try {
    const url = new URL(tab.url)
    const hostname = url.hostname
    const mainDomain = getMainDomain(hostname)  // 获取主域名

    // 获取当前权限
    const perms = await chrome.storage.local.get('hostPermissions')
    let allHosts = (perms && perms.hostPermissions) || []

    // 移除该主域名的权限
    allHosts = allHosts.filter(h => {
      if (!h.includes('*')) return true
      const hostMain = getMainDomain(h.replace('*://*.', '').replace('/*', ''))
      return hostMain !== mainDomain
    })

    await chrome.storage.local.set({ hostPermissions: allHosts })

    showToast(`已撤销 ${mainDomain} 域名`)
    // 刷新授权状态
    const info = await checkCurrentPageAuth(tab)
    updateAuthStatus(info)
  } catch (e) {
    console.error('[Popup] 撤销失败:', e)
    showToast('撤销失败: ' + e.message)
  }
}

// 连接到 Relay 服务器
async function connect() {
  const host = elements.hostInput.value.trim() || '127.0.0.1'
  const port = elements.portInput.value.trim() || '18792'

  // 保存配置
  await chrome.storage.local.set({
    [STORAGE_CONFIG]: {
      host,
      relayPort: parseInt(port, 10),
      autoReconnect: true,
    },
  })

  // 获取密钥
  const [keyData] = await chrome.storage.local.get([STORAGE_SECRET_KEY])
  const secretKey = keyData[STORAGE_SECRET_KEY]

  updateConnectionStatus(false, true)

  try {
    // 发送连接消息到 background
    const response = await chrome.runtime.sendMessage({
      type: 'CONNECT_WEBSOCKET',
      url: `ws://${host}:${port}/extension`,
      secretKey: secretKey,
    })

    if (response && response.success) {
      updateConnectionStatus(true, false)
      showToast('连接成功')
    } else {
      updateConnectionStatus(false, false)
      showToast('连接失败: ' + (response?.error || '未知错误'))
    }
  } catch (e) {
    updateConnectionStatus(false, false)
    showToast('连接失败: ' + e.message)
  }
}

// 断开连接
async function disconnect() {
  try {
    await chrome.runtime.sendMessage({
      type: 'DISCONNECT_WEBSOCKET',
    })
    updateConnectionStatus(false, false)
    showToast('已断开')
  } catch (e) {
    showToast('断开失败: ' + e.message)
  }
}

// 复制密钥到剪贴板
async function copyKey() {
  const key = elements.secretKey.textContent
  if (key && key !== '加载中...' && key !== '未生成') {
    try {
      await navigator.clipboard.writeText(key)
      showToast('已复制到剪贴板')
    } catch (e) {
      showToast('复制失败')
    }
  }
}

// 打开设置页面
function openSettingsPage() {
  if (chrome.runtime.openOptionsPage) {
    chrome.runtime.openOptionsPage()
  } else {
    window.open('options.html')
  }
  window.close()
}

// 初始化
async function init() {
  // 加载配置
  const config = await getConfig()

  // 填充配置
  elements.hostInput.value = config.host
  elements.portInput.value = config.port

  // 更新密钥显示
  updateSecretKey(config.secretKey)

  // 更新连接状态
  updateConnectionStatus(config.connected)

  // 获取当前标签页并检查授权
  const tab = await getCurrentTab()
  if (tab) {
    const authInfo = await checkCurrentPageAuth(tab)
    updateAuthStatus(authInfo)
  }

  // 监听密钥变化
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && changes[STORAGE_SECRET_KEY]) {
      updateSecretKey(changes[STORAGE_SECRET_KEY].newValue)
    }
    if (area === 'local' && changes[STORAGE_STATUS]) {
      const newStatus = changes[STORAGE_STATUS].newValue
      updateConnectionStatus(newStatus?.connected || false)
    }
  })
}

// 绑定事件
elements.connectBtn.addEventListener('click', connect)
elements.disconnectBtn.addEventListener('click', disconnect)
elements.copyKey.addEventListener('click', copyKey)
elements.openSettings.addEventListener('click', (e) => {
  e.preventDefault()
  openSettingsPage()
})

elements.authBtn.addEventListener('click', async () => {
  const tab = await getCurrentTab()
  const isGranted = elements.authBtn.classList.contains('granted')

  if (isGranted) {
    await revokeCurrentPage(tab)
  } else {
    await authorizeCurrentPage(tab)
  }
})

// 启动
init()