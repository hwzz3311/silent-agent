/**
 * Neurone Chrome Extension - Background Service Worker (v2)
 *
 * 基于 chrome.scripting API 的远程浏览器控制系统
 *
 * 架构：
 * - WebSocket 连接到 Python Relay 服务器
 * - 工具注册表：远程调用 → 本地执行 → 返回结果
 * - 使用 chrome.scripting.executeScript 操作页面（无需 chrome.debugger）
 */

// ==================== 常量 ====================

const DEFAULT_PORT = 18792

const BADGE = {
  on:         { text: 'ON', color: '#22C55E' },
  off:        { text: '',   color: '#000000' },
  connecting: { text: '…',  color: '#F59E0B' },
  error:      { text: '!',  color: '#EF4444' },
}

const MSG = {
  HELLO:       'hello',
  TOOL_CALL:   'tool_call',
  TOOL_RESULT: 'tool_result',
  PING:        'ping',
  PONG:        'pong',
  STATUS:      'status',
  ERROR:       'error',
}

const STORAGE_STATUS = 'server_status'
const STORAGE_CONFIG = 'connection_config'

// ==================== 工具注册表 ====================

/** @type {Map<string, BaseTool>} */
const toolRegistry = new Map()

function registerTool(tool) {
  toolRegistry.set(tool.name, tool)
}

async function executeTool({ name, args }) {
  const tool = toolRegistry.get(name)
  if (!tool) {
    return { content: [{ type: 'error', text: `未知工具: ${name}` }], isError: true }
  }
  try {
    console.log(`[Neurone] 执行工具: ${name}`, args)
    const result = await tool.execute(args || {})
    console.log(`[Neurone] 工具完成: ${name}`)
    return result
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error(`[Neurone] 工具失败: ${name} →`, msg)
    return { content: [{ type: 'error', text: msg }], isError: true }
  }
}

// ==================== BaseTool ====================

class BaseTool {
  constructor(name) { this.name = name }

  /** 等待标签页加载完成 */
  waitForTabLoad(tabId, timeout = 30000) {
    return new Promise(async (resolve, reject) => {
      try {
        const tab = await chrome.tabs.get(tabId)
        if (tab.status === 'complete') return resolve()
      } catch { /* tab may not exist yet */ }

      const timer = setTimeout(() => {
        chrome.tabs.onUpdated.removeListener(fn)
        reject(new Error('页面加载超时'))
      }, timeout)

      function fn(id, info) {
        if (id === tabId && info.status === 'complete') {
          clearTimeout(timer)
          chrome.tabs.onUpdated.removeListener(fn)
          resolve()
        }
      }
      chrome.tabs.onUpdated.addListener(fn)
    })
  }

  /** 在标签页中执行脚本 (ISOLATED world) */
  async execInTab(tabId, func, args = []) {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func,
      args,
    })
    return results?.[0]?.result ?? null
  }

  /** 在标签页中执行脚本 (MAIN world — 可访问页面 JS 上下文) */
  async execInTabMain(tabId, func, args = []) {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func,
      args,
      world: 'MAIN',
    })
    return results?.[0]?.result ?? null
  }

  /** 获取当前活动标签页 */
  async getActiveTab() {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true })
    if (!tabs.length) throw new Error('没有活动标签页')
    return tabs[0]
  }

  /** 解析 tabId：优先使用传入的，否则取活动标签页 */
  async resolveTabId(tabId) {
    if (tabId) return tabId
    return (await this.getActiveTab()).id
  }

  ok(data) {
    const text = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
    return { content: [{ type: 'text', text }] }
  }

  err(message) {
    return { content: [{ type: 'error', text: message }], isError: true }
  }
}

// ==================== 无障碍树生成器 (Accessibility Tree) ====================

/**
 * 模拟无障碍树生成器
 * 从 DOM 树构建一个模拟的无障碍树，用于 AI 理解和操作页面
 */
class A11yTreeGenerator {
  constructor() {
    // HTML 标签到 ARIA role 的隐式映射
    this.SEMANTIC_TAG_ROLES = {
      'A': 'link',
      'BUTTON': 'button',
      'INPUT': 'textbox',
      'SELECT': 'combobox',
      'TEXTAREA': 'textbox',
      'H1': 'heading',
      'H2': 'heading',
      'H3': 'heading',
      'H4': 'heading',
      'H5': 'heading',
      'H6': 'heading',
      'NAV': 'navigation',
      'MAIN': 'main',
      'HEADER': 'banner',
      'FOOTER': 'contentinfo',
      'FORM': 'form',
      'ARTICLE': 'article',
      'ASIDE': 'complementary',
      'SECTION': 'region',
      'TABLE': 'table',
      'TH': 'columnheader',
      'TD': 'cell',
      'UL': 'list',
      'OL': 'list',
      'LI': 'listitem',
      'IMG': 'image',
      'SVG': 'image',
      'CANVAS': 'img',
    }

    // 可交互元素选择器
    this.INTERACTIVE_SELECTORS = [
      'a[href]',
      'button',
      'input:not([type="hidden"])',
      'select',
      'textarea',
      '[role="button"]',
      '[role="link"]',
      '[role="checkbox"]',
      '[role="radio"]',
      '[role="textbox"]',
      '[role="combobox"]',
      '[role="menuitem"]',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(', ')
  }

  /**
   * 构建完整无障碍树
   */
  buildFullTree() {
    const elements = document.querySelectorAll(this.INTERACTIVE_SELECTORS)
    const nodes = []
    const nodeMap = new Map()

    // 第一遍：创建所有节点
    elements.forEach((el, index) => {
      const node = this._buildNode(el, index)
      if (node) {
        nodes.push(node)
        nodeMap.set(node.id, node)
      }
    })

    // 第二遍：建立父子关系
    const rootNodes = []
    const addedElements = new Set()

    nodes.forEach(node => {
      const el = nodeMap.get(node.id)?.element
      if (!el) return

      let parent = el.parentElement
      while (parent && parent !== document.body) {
        const parentNode = nodes.find(n => n.id === this._getElementId(parent))
        if (parentNode) {
          if (!parentNode.children.includes(node.id)) {
            parentNode.children.push(node.id)
          }
          break
        }
        parent = parent.parentElement
      }

      if (!parent || parent === document.body) {
        rootNodes.push(node.id)
      }
    })

    return {
      rootIds: rootNodes,
      nodes: Object.fromEntries(nodes.map(n => [n.id, this._serializeNode(n)])),
      totalNodes: nodes.length,
      timestamp: Date.now(),
    }
  }

  /**
   * 构建聚焦元素的节点
   */
  buildFocusedNode() {
    const activeEl = document.activeElement
    if (!activeEl) return null

    const node = this._buildNode(activeEl, 0)
    if (node) {
      node.focused = true
      return this._serializeNode(node)
    }
    return null
  }

  /**
   * 条件查询节点
   */
  queryNodes(predicate) {
    const elements = document.querySelectorAll(this.INTERACTIVE_SELECTORS)
    const results = []

    elements.forEach((el, index) => {
      const node = this._buildNode(el, index)
      if (node && this._matchPredicate(node, predicate)) {
        results.push(this._serializeNode(node))
      }
    })

    return results
  }

  /**
   * 根据 ID 获取节点（支持路径查找）
   */
  getNode(nodeId) {
    const el = this._findElementById(nodeId)
    if (!el) return null

    const node = this._buildNode(el, 0)
    if (node) return this._serializeNode(node)
    return null
  }

  // ========== 私有方法 ==========

  /**
   * 为元素生成唯一 ID
   */
  _getElementId(el) {
    if (el.id) return `${el.tagName.toLowerCase()}#${el.id}`
    return `${el.tagName.toLowerCase()}[${this._generateCssPath(el).slice(0, 60)}]`
  }

  /**
   * 根据 ID 查找元素
   */
  _findElementById(nodeId) {
    if (nodeId.startsWith('#')) {
      return document.getElementById(nodeId.slice(1))
    }
    // 路径查找
    const selectors = nodeId.split(',')
    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel)
        if (el) return el
      } catch {}
    }
    return null
  }

  /**
   * 生成元素的 CSS 路径
   */
  _generateCssPath(el) {
    if (el.id) return `#${el.id}`

    const path = []
    let current = el
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase()
      if (current.id) {
        selector = `#${current.id}`
        path.unshift(selector)
        break
      }
      const parent = current.parentElement
      if (parent) {
        const siblings = parent.querySelectorAll(':scope > ' + current.tagName.toLowerCase())
        if (siblings.length > 1) {
          const index = Array.from(siblings).indexOf(current) + 1
          selector += `:nth-of-type(${index})`
        }
      }
      path.unshift(selector)
      current = parent
    }
    return path.join(' > ')
  }

  /**
   * 构建单个节点
   */
  _buildNode(el, index) {
    if (!this._isVisible(el)) return null

    const role = this._getRole(el)
    const name = this._getAccessibleName(el)
    const state = this._getState(el)
    const selector = this._generateCssPath(el)

    // 如果没有角色也没有名称，跳过
    if (!role && !name) return null

    return {
      id: this._getElementId(el),
      index,
      role,
      name,
      description: el.getAttribute('aria-describedby') || el.getAttribute('title') || '',
      tag: el.tagName.toLowerCase(),
      selector,
      value: this._getValue(el),
      state,
      boundingBox: this._getBoundingBox(el),
      properties: this._getProperties(el),
      children: [],
      element: el, // 内部引用，用于构建树结构
    }
  }

  /**
   * 序列化节点（移除内部引用）
   */
  _serializeNode(node) {
    const { element, ...serialized } = node
    return serialized
  }

  /**
   * 判断元素是否可见
   */
  _isVisible(el) {
    if (!el) return false
    if (el.offsetParent === null && el.tagName !== 'INPUT') return false
    if (el.hidden) return false
    const style = window.getComputedStyle(el)
    if (style.display === 'none') return false
    if (style.visibility === 'hidden') return false
    if (style.opacity === '0') return false
    return true
  }

  /**
   * 获取元素的 ARIA role
   */
  _getRole(el) {
    // 显式 role
    const explicitRole = el.getAttribute('role')
    if (explicitRole) return explicitRole

    // 隐式 role（基于标签名）
    return this.SEMANTIC_TAG_ROLES[el.tagName] || null
  }

  /**
   * 获取可访问名称
   */
  _getAccessibleName(el) {
    // 1. aria-label
    const ariaLabel = el.getAttribute('aria-label')
    if (ariaLabel && ariaLabel.trim()) return ariaLabel.trim()

    // 2. aria-labelledby
    const ariaLabelledBy = el.getAttribute('aria-labelledby')
    if (ariaLabelledBy) {
      const ids = ariaLabelledBy.split(/\s+/)
      const parts = ids.map(id => {
        const target = document.getElementById(id)
        return target?.innerText || target?.textContent || ''
      }).filter(Boolean)
      if (parts.length) return parts.join(' ').trim().slice(0, 200)
    }

    // 3. alt（图片）
    if (el.tagName === 'IMG' || el.tagName === 'INPUT') {
      const alt = el.getAttribute('alt')
      if (alt) return alt.trim().slice(0, 100)
    }

    // 4. placeholder
    const placeholder = el.getAttribute('placeholder')
    if (placeholder && placeholder.trim()) return placeholder.trim().slice(0, 100)

    // 5. innerText（仅对非输入元素）
    if (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA' && el.tagName !== 'SELECT') {
      const text = el.innerText || el.textContent || ''
      const trimmed = text.trim().slice(0, 100)
      if (trimmed) return trimmed
    }

    // 6. value（特定类型 input）
    if (el.tagName === 'INPUT') {
      return (el.value || '').slice(0, 100)
    }

    return ''
  }

  /**
   * 获取元素状态
   */
  _getState(el) {
    const state = {}

    // 禁用状态
    if (el.disabled) state.disabled = true

    // 选中状态
    if (el.checked) state.checked = true
    if (el.selected) state.selected = true

    // 只读状态
    if (el.readOnly || el.readonly) state.readonly = true

    // 展开/折叠状态
    const expanded = el.getAttribute('aria-expanded')
    if (expanded !== null) state.expanded = expanded === 'true'

    // 选中状态 (aria-selected)
    const ariaSelected = el.getAttribute('aria-selected')
    if (ariaSelected !== null) state['aria-selected'] = ariaSelected === 'true'

    // 焦点状态
    if (document.activeElement === el) state.focused = true

    // 必填状态
    if (el.required) state.required = true

    // 有效性状态
    if (el.validity) {
      if (!el.validity.valid) state.invalid = true
    }

    // 隐藏状态
    if (!this._isVisible(el)) state.hidden = true

    return Object.keys(state).length ? state : null
  }

  /**
   * 获取元素值
   */
  _getValue(el) {
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      return (el.value || '').slice(0, 500)
    }
    if (el.tagName === 'SELECT' && el.multiple) {
      return Array.from(el.selectedOptions).map(o => o.value)
    }
    if (el.tagName === 'SELECT') {
      return el.value
    }
    return null
  }

  /**
   * 获取边界框
   */
  _getBoundingBox(el) {
    const rect = el.getBoundingClientRect()
    if (rect.width < 1 || rect.height < 1) return null

    return {
      x: Math.round(rect.x),
      y: Math.round(rect.y),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
    }
  }

  /**
   * 获取额外属性
   */
  _getProperties(el) {
    const props = {}

    // type（对于 input 元素）
    if (el.tagName === 'INPUT' && el.type) {
      props.inputType = el.type
    }

    // href（对于链接）
    if (el.tagName === 'A' && el.href) {
      props.href = el.href.slice(0, 100)
      props.target = el.target || '_self'
    }

    // autocomplete
    if (el.autocomplete) {
      props.autocomplete = el.autocomplete
    }

    // pattern
    if (el.pattern) {
      props.pattern = el.pattern
    }

    // maxlength
    if (el.maxLength > -1) {
      props.maxLength = el.maxLength
    }

    return Object.keys(props).length ? props : null
  }

  /**
   * 匹配谓词
   */
  _matchPredicate(node, predicate) {
    if (predicate.role && node.role !== predicate.role) return false
    if (predicate.name && !node.name?.includes(predicate.name)) return false
    if (predicate.tag && node.tag !== predicate.tag) return false
    if (predicate.state) {
      for (const [key, val] of Object.entries(predicate.state)) {
        if (node.state?.[key] !== val) return false
      }
    }
    return true
  }
}

// ========== 无障碍树工具 ==========

class A11yTreeTool extends BaseTool {
  constructor() { super('a11y_tree') }

  async execute({ action = 'get_tree', nodeId, predicate, limit = 100, tabId }) {
    const tid = await this.resolveTabId(tabId)
    await this.waitForTabLoad(tid).catch(() => {})

    const r = await this.execInTabMain(tid, (act, nid, pred, lim) => {
      const generator = new A11yTreeGenerator()
      let result = null

      switch (act) {
        case 'get_tree':
          result = generator.buildFullTree()
          // 限制返回的节点详情数量
          const nodeIds = result.rootIds.slice(0, lim)
          const nodeMap = {}
          nodeIds.forEach(id => {
            nodeMap[id] = result.nodes[id]
          })
          return { ...result, nodes: nodeMap }

        case 'get_focused':
          result = generator.buildFocusedNode()
          return result

        case 'get_node':
          result = generator.getNode(nid)
          return result

        case 'query':
          result = generator.queryNodes(pred || {})
          return result.slice(0, lim)

        default:
          return { error: `未知操作: ${act}` }
      }
    }, [action, nodeId, predicate, limit])

    return this.ok(r)
  }
}

// ========== 无障碍树工具 End ====================
class InjectScriptTool extends BaseTool {
  constructor() { super('inject_script') }

  async execute({ code, world = 'MAIN', tabId }) {
    if (!code) return this.err('参数缺失: code')
    const tid = await this.resolveTabId(tabId)
    await this.waitForTabLoad(tid).catch(() => {})

    try {
      const fn = world === 'MAIN' ? this.execInTabMain : this.execInTab
      const result = await fn.call(this, tid, (c) => {
        try { return eval(c) } catch (e) { return { __error: e.message } }
      }, [code])
      if (result && result.__error) return this.err(result.__error)
      return this.ok(result)
    } catch (e) {
      return this.err(`脚本执行失败: ${e.message}`)
    }
  }
}

// ---------- read_page_data ----------
class ReadPageDataTool extends BaseTool {
  constructor() { super('read_page_data') }

  async execute({ path, tabId }) {
    if (!path) return this.err('参数缺失: path')
    const tid = await this.resolveTabId(tabId)
    await this.waitForTabLoad(tid).catch(() => {})

    const result = await this.execInTabMain(tid, (p) => {
      let obj = window
      for (const k of p.split('.')) {
        if (obj == null) return null
        obj = obj[k]
      }
      try { return JSON.parse(JSON.stringify(obj)) } catch { return String(obj) }
    }, [path])
    return this.ok(result)
  }
}

// ---------- chrome_navigate ----------
class NavigateTool extends BaseTool {
  constructor() { super('chrome_navigate') }

  async execute({ url, timeout = 30000, newTab = true, tabId }) {
    if (!url) return this.err('参数缺失: url')

    let tab
    if (newTab) {
      tab = await chrome.tabs.create({ url, active: true })
    } else {
      const tid = await this.resolveTabId(tabId)
      tab = await chrome.tabs.update(tid, { url, active: true })
    }
    if (!tab?.id) return this.err('无法操作标签页')

    try { await this.waitForTabLoad(tab.id, timeout) } catch { /* timeout ok */ }

    const info = await chrome.tabs.get(tab.id)
    return this.ok({ tabId: info.id, url: info.url, title: info.title, status: info.status })
  }
}

// ---------- browser_control ----------
class BrowserControlTool extends BaseTool {
  constructor() { super('browser_control') }

  async execute({ action, params = {} }) {
    switch (action) {
      case 'close_tab':    return this._closeTab(params)
      case 'get_tab':      return this._getTab(params)
      case 'update_tab':   return this._updateTab(params)
      case 'query_tabs':   return this._queryTabs(params)
      case 'get_active_tab': return this._getActiveTab()
      default: return this.err(`未知操作: ${action}`)
    }
  }

  async _closeTab({ tabId }) {
    if (!tabId) return this.err('tabId 必填')
    await chrome.tabs.remove(tabId)
    return this.ok({ success: true, tabId })
  }

  async _getTab({ tabId }) {
    if (!tabId) return this.err('tabId 必填')
    const t = await chrome.tabs.get(tabId)
    return this.ok({ tabId: t.id, url: t.url, title: t.title, status: t.status, active: t.active })
  }

  async _updateTab({ tabId, updateInfo }) {
    if (!tabId) return this.err('tabId 必填')
    await chrome.tabs.update(tabId, updateInfo || {})
    if (updateInfo?.url) await this.waitForTabLoad(tabId).catch(() => {})
    const t = await chrome.tabs.get(tabId)
    return this.ok({ tabId: t.id, url: t.url, title: t.title, status: t.status })
  }

  async _queryTabs({ queryInfo = {} }) {
    const tabs = await chrome.tabs.query(queryInfo)
    return this.ok(tabs.map(t => ({
      tabId: t.id, url: t.url, title: t.title, status: t.status, active: t.active, windowId: t.windowId,
    })))
  }

  async _getActiveTab() {
    const t = await this.getActiveTab()
    return this.ok({ tabId: t.id, url: t.url, title: t.title, status: t.status, active: t.active })
  }
}

// ---------- chrome_extract_data ----------
class ExtractDataTool extends BaseTool {
  constructor() { super('chrome_extract_data') }

  async execute({ selector, path, attribute = 'text', source = 'element', all = false, timeout = 5000, tabId }) {
    const tid = await this.resolveTabId(tabId)
    await this.waitForTabLoad(tid).catch(() => {})

    if (source === 'window' && path) {
      const r = await this.execInTabMain(tid, (p) => {
        let o = window; for (const k of p.split('.')) { if (o == null) return null; o = o[k] }
        try { return JSON.parse(JSON.stringify(o)) } catch { return String(o) }
      }, [path])
      return this.ok(r)
    }

    if (source === 'document' && path) {
      const r = await this.execInTab(tid, (p) => {
        let o = document; for (const k of p.split('.')) { if (o == null) return null; o = o[k] }
        try { return JSON.parse(JSON.stringify(o)) } catch { return String(o) }
      }, [path])
      return this.ok(r)
    }

    if (!selector) return this.err('selector 是必填参数')

    const r = await this.execInTab(tid, (sel, attr, getAll, to) => {
      function extract(el) {
        if (!el) return null
        switch (attr) {
          case 'text':      return el.innerText || el.textContent || ''
          case 'html':      return el.innerHTML || ''
          case 'outerHTML':  return el.outerHTML || ''
          case 'value':     return el.value ?? ''
          case 'checked':   return !!el.checked
          case 'href':      return el.href || ''
          case 'src':       return el.src || ''
          case 'className': return el.className || ''
          case 'id':        return el.id || ''
          case 'tagName':   return el.tagName || ''
          case 'exists':    return true
          default:          return el.getAttribute(attr) || ''
        }
      }
      if (getAll) return Array.from(document.querySelectorAll(sel)).map(extract)
      return extract(document.querySelector(sel))
    }, [selector, attribute, all, timeout])
    return this.ok(r)
  }
}

// ---------- chrome_click ----------
class ClickTool extends BaseTool {
  constructor() { super('chrome_click') }

  async execute({ selector, text, timeout = 5000, waitForNav = false, tabId }) {
    if (!selector) return this.err('selector 是必填参数')
    const tid = await this.resolveTabId(tabId)
    await this.waitForTabLoad(tid).catch(() => {})

    const r = await this.execInTab(tid, (sel, txt, to) => {
      return new Promise(resolve => {
        const t0 = Date.now()
        ;(function poll() {
          let els = Array.from(document.querySelectorAll(sel))
          if (txt) els = els.filter(e => {
            const t = (e.innerText || e.textContent || '').trim()
            return t === txt || t.includes(txt)
          })
          const el = els[0]
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' })
            el.click()
            resolve({ success: true, tag: el.tagName, text: (el.innerText || '').slice(0, 100) })
          } else if (Date.now() - t0 < to) {
            setTimeout(poll, 200)
          } else {
            resolve({ success: false, error: `元素未找到: ${sel}${txt ? ` (文本: "${txt}")` : ''}` })
          }
        })()
      })
    }, [selector, text || null, timeout])

    if (!r?.success) return this.err(r?.error || '点击失败')

    if (waitForNav) {
      await this.waitForTabLoad(tid, 10000).catch(() => {})
      const t = await chrome.tabs.get(tid)
      return this.ok({ ...r, url: t.url, title: t.title })
    }
    return this.ok(r)
  }
}

// ---------- chrome_fill ----------
class FillTool extends BaseTool {
  constructor() { super('chrome_fill') }

  async execute({ selector, value, method = 'set', clearBefore = true, timeout = 5000, tabId }) {
    if (!selector) return this.err('selector 是必填参数')
    if (value == null) return this.err('value 是必填参数')
    const tid = await this.resolveTabId(tabId)
    await this.waitForTabLoad(tid).catch(() => {})

    const r = await this.execInTab(tid, (sel, val, meth, clear, to) => {
      return new Promise(resolve => {
        const t0 = Date.now()
        ;(function poll() {
          const el = document.querySelector(sel)
          if (!el) {
            if (Date.now() - t0 < to) return setTimeout(poll, 200)
            return resolve({ success: false, error: `元素未找到: ${sel}` })
          }
          el.focus()
          if (clear) {
            el.value = ''
            el.dispatchEvent(new Event('input', { bubbles: true }))
          }
          if (meth === 'type') {
            const chars = String(val).split('')
            let i = 0
            ;(function next() {
              if (i >= chars.length) {
                el.dispatchEvent(new Event('change', { bubbles: true }))
                return resolve({ success: true, method: 'type' })
              }
              const ch = chars[i++]
              el.dispatchEvent(new KeyboardEvent('keydown', { key: ch, bubbles: true }))
              el.value += ch
              el.dispatchEvent(new Event('input', { bubbles: true }))
              el.dispatchEvent(new KeyboardEvent('keyup', { key: ch, bubbles: true }))
              setTimeout(next, 20)
            })()
          } else if (meth === 'execCommand') {
            el.focus()
            document.execCommand('selectAll', false, null)
            document.execCommand('insertText', false, String(val))
            resolve({ success: true, method: 'execCommand' })
          } else {
            /* 'set' - 使用原生 setter 触发 React/Vue 等框架的数据绑定 */
            const setter =
              Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set ||
              Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set
            if (setter) setter.call(el, String(val))
            else el.value = String(val)
            el.dispatchEvent(new Event('input', { bubbles: true }))
            el.dispatchEvent(new Event('change', { bubbles: true }))
            resolve({ success: true, method: 'set' })
          }
        })()
      })
    }, [selector, String(value), method, clearBefore, timeout])

    return r?.success ? this.ok(r) : this.err(r?.error || '填充失败')
  }
}

// ---------- chrome_keyboard ----------
class KeyboardTool extends BaseTool {
  constructor() { super('chrome_keyboard') }

  async execute({ keys, selector, delay = 50, tabId }) {
    if (!keys) return this.err('keys 是必填参数')
    const tid = await this.resolveTabId(tabId)

    const r = await this.execInTab(tid, (keyStr, sel, del) => {
      return new Promise(resolve => {
        let target = document.activeElement || document.body
        if (sel) {
          const el = document.querySelector(sel)
          if (el) { el.focus(); target = el }
        }
        const list = keyStr.split(',').map(k => k.trim())
        let i = 0
        ;(function next() {
          if (i >= list.length) return resolve({ success: true, keysPressed: list.length })
          const key = list[i++]
          const opts = { key, bubbles: true, cancelable: true }
          target.dispatchEvent(new KeyboardEvent('keydown', opts))
          target.dispatchEvent(new KeyboardEvent('keypress', opts))
          if (key.length === 1 && target.value !== undefined) {
            target.value += key
            target.dispatchEvent(new Event('input', { bubbles: true }))
          }
          if (key === 'Enter') {
            const form = target.closest?.('form')
            if (form) form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
          }
          target.dispatchEvent(new KeyboardEvent('keyup', opts))
          setTimeout(next, del)
        })()
      })
    }, [keys, selector || null, delay])
    return this.ok(r)
  }
}

// ---------- chrome_wait_elements ----------
class WaitElementsTool extends BaseTool {
  constructor() { super('chrome_wait_elements') }

  async execute({ selector, count = 1, timeout = 60000, checkInterval = 500, tabId }) {
    if (!selector) return this.err('selector 是必填参数')
    const tid = await this.resolveTabId(tabId)

    const r = await this.execInTab(tid, (sel, cnt, to, interval) => {
      return new Promise(resolve => {
        const t0 = Date.now()
        ;(function poll() {
          const n = document.querySelectorAll(sel).length
          if (n >= cnt) resolve({ success: true, found: n, expected: cnt })
          else if (Date.now() - t0 < to) setTimeout(poll, interval)
          else resolve({ success: false, found: n, expected: cnt })
        })()
      })
    }, [selector, count, timeout, checkInterval])

    return r?.success ? this.ok(r) : this.err(`等待超时: 期望 ${count} 个元素，找到 ${r?.found ?? 0}`)
  }
}

// ---------- chrome_screenshot ----------
class ScreenshotTool extends BaseTool {
  constructor() { super('chrome_screenshot') }

  async execute({ tabId, format = 'png', quality = 80 }) {
    const tid = await this.resolveTabId(tabId)
    const tab = await chrome.tabs.get(tid)
    // 确保标签页在前台
    await chrome.tabs.update(tid, { active: true })
    // 短暂延迟确保渲染完成
    await new Promise(r => setTimeout(r, 300))

    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {
      format: format === 'jpeg' ? 'jpeg' : 'png',
      quality,
    })
    return this.ok({ dataUrl, format, tabId: tid })
  }
}

// ---------- chrome_scroll ----------
class ScrollTool extends BaseTool {
  constructor() { super('chrome_scroll') }

  async execute({ selector, direction = 'down', amount = 300, tabId }) {
    const tid = await this.resolveTabId(tabId)

    const r = await this.execInTab(tid, (sel, dir, amt) => {
      let target = sel ? document.querySelector(sel) : null
      const el = target || document.documentElement
      const scrollOpts = { behavior: 'smooth' }
      switch (dir) {
        case 'down':  el.scrollBy({ top: amt, ...scrollOpts }); break
        case 'up':    el.scrollBy({ top: -amt, ...scrollOpts }); break
        case 'left':  el.scrollBy({ left: -amt, ...scrollOpts }); break
        case 'right': el.scrollBy({ left: amt, ...scrollOpts }); break
        case 'top':   el.scrollTo({ top: 0, ...scrollOpts }); break
        case 'bottom': el.scrollTo({ top: el.scrollHeight, ...scrollOpts }); break
      }
      if (sel && target) target.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return { success: true, direction: dir }
    }, [selector || null, direction, amount])
    return this.ok(r)
  }
}

// ---------- chrome_get_page_info ----------
class GetPageInfoTool extends BaseTool {
  constructor() { super('chrome_get_page_info') }

  async execute({ tabId }) {
    const tid = await this.resolveTabId(tabId)
    await this.waitForTabLoad(tid).catch(() => {})

    const pageData = await this.execInTab(tid, () => {
      return {
        url: location.href,
        title: document.title,
        readyState: document.readyState,
        doctype: document.doctype ? document.doctype.name : null,
        charset: document.characterSet,
        contentType: document.contentType,
        scrollHeight: document.documentElement.scrollHeight,
        scrollWidth: document.documentElement.scrollWidth,
        clientHeight: document.documentElement.clientHeight,
        clientWidth: document.documentElement.clientWidth,
        forms: document.forms.length,
        images: document.images.length,
        links: document.links.length,
        scripts: document.scripts.length,
      }
    })

    const tab = await chrome.tabs.get(tid)
    return this.ok({ tabId: tid, tabUrl: tab.url, tabTitle: tab.title, ...pageData })
  }
}

// ==================== WebSocket 客户端 ====================

class NeuroneWSClient {
  constructor() {
    /** @type {WebSocket|null} */
    this.socket = null
    this.shouldReconnect = false
    this.reconnectTimer = null
    this.currentUrl = null
  }

  async connect(url) {
    if (!url) return { success: false, error: '未提供 URL' }
    if (this.socket) { try { this.socket.close() } catch {} }
    this.clearReconnectTimer()
    this.currentUrl = url
    this.shouldReconnect = true

    return new Promise(resolve => {
      try {
        const ws = new WebSocket(url)
        const timer = setTimeout(() => {
          try { ws.close() } catch {}
          resolve({ success: false, error: '连接超时' })
        }, 10000)

        ws.onopen = () => {
          clearTimeout(timer)
          this.socket = ws
          console.log(`[Neurone] WebSocket 已连接: ${url}`)
          this.send({
            type: MSG.HELLO,
            extensionId: chrome.runtime.id,
            version: chrome.runtime.getManifest().version,
            tools: Array.from(toolRegistry.keys()),
          })
          void updateServerStatus({ connected: true, serverUrl: url })
          updateBadge('on')
          void chrome.action.setTitle({ title: 'Neurone: 已连接 (点击断开)' })
          resolve({ success: true })
        }
        ws.onmessage = (ev) => void this._onMessage(ev.data)
        ws.onclose = (ev) => {
          clearTimeout(timer)
          console.log(`[Neurone] WebSocket 关闭: code=${ev.code}`)
          this.socket = null
          // 标记为待重连（Service Worker 重启时需要恢复）
          void setPendingReconnect()
          this._scheduleReconnect()
        }
        ws.onerror = () => {
          clearTimeout(timer)
          console.warn('[Neurone] WebSocket 连接错误')
        }
      } catch (e) {
        resolve({ success: false, error: e.message })
      }
    })
  }

  disconnect() {
    this.shouldReconnect = false
    this.clearReconnectTimer()
    if (this.socket) { try { this.socket.close() } catch {} this.socket = null }
    // 用户手动断开，清除待重连标记
    void updateServerStatus({ connected: false, pendingReconnect: false })
    updateBadge('off')
    void chrome.action.setTitle({ title: 'Neurone: 已断开 (点击连接)' })
  }

  isConnected() {
    return this.socket?.readyState === WebSocket.OPEN
  }

  send(obj) {
    if (!this.isConnected()) return
    this.socket.send(JSON.stringify(obj))
  }

  // ---------- 内部 ----------

  async _onMessage(raw) {
    let text = raw
    if (raw instanceof ArrayBuffer) text = new TextDecoder().decode(raw)
    else if (raw instanceof Blob) text = await raw.text()

    let msg
    try { msg = JSON.parse(text) } catch { return }

    const type = msg.type || msg.method

    if (type === MSG.PING || type === 'ping') {
      this.send({ type: MSG.PONG })
      return
    }

    if (type === MSG.TOOL_CALL || type === 'tool_call') {
      await this._handleToolCall(msg)
      return
    }

    if (type === MSG.STATUS) {
      console.log('[Neurone] 收到状态:', msg)
    }
  }

  async _handleToolCall(msg) {
    const requestId = msg.requestId ?? msg.id
    const payload = msg.payload || msg.params || {}
    const name = payload.name || payload.method
    const args = payload.args || payload.params || {}
    console.log(`[Neurone] TOOL_CALL: ${name}  requestId=${requestId}`)

    const result = await executeTool({ name, args })
    this.send({ type: MSG.TOOL_RESULT, requestId, result })
  }

  _scheduleReconnect() {
    if (!this.shouldReconnect || !this.currentUrl) return
    this.clearReconnectTimer()
    this.reconnectTimer = setTimeout(() => {
      console.log('[Neurone] 自动重连...')
      updateBadge('connecting')
      void this.connect(this.currentUrl)
    }, 5000)
  }

  clearReconnectTimer() {
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null }
  }
}

// ==================== 状态管理 ====================

async function getRelayPort() {
  const s = await chrome.storage.local.get(['relayPort'])
  const n = parseInt(String(s.relayPort || ''), 10)
  return (Number.isFinite(n) && n > 0 && n <= 65535) ? n : DEFAULT_PORT
}

async function getConnectionConfig() {
  const stored = await chrome.storage.local.get([STORAGE_CONFIG])
  const port = await getRelayPort()
  return {
    serverUrl: `ws://127.0.0.1:${port}/extension`,
    autoReconnect: true,
    ...stored[STORAGE_CONFIG],
  }
}

async function getServerStatus() {
  const s = await chrome.storage.local.get([STORAGE_STATUS])
  return { connected: false, serverUrl: '', lastUpdated: 0, pendingReconnect: false, ...s[STORAGE_STATUS] }
}

async function updateServerStatus(update) {
  const cur = await getServerStatus()
  const next = { ...cur, ...update, lastUpdated: Date.now() }
  await chrome.storage.local.set({ [STORAGE_STATUS]: next })
  try { chrome.runtime.sendMessage({ type: 'SERVER_STATUS_CHANGED', status: next }).catch(() => {}) } catch {}
  return next
}

// 设置待重连状态（用于 Service Worker 重启时识别需要重连）
async function setPendingReconnect() {
  await updateServerStatus({ connected: false, pendingReconnect: true })
  updateBadge('connecting')
}

function updateBadge(kind) {
  const c = BADGE[kind]
  void chrome.action.setBadgeText({ text: c.text })
  void chrome.action.setBadgeBackgroundColor({ color: c.color })
  void chrome.action.setBadgeTextColor({ color: '#FFFFFF' }).catch(() => {})
}

// 恢复 badge 状态（Service Worker 重启时调用）
async function restoreBadgeState() {
  const status = await getServerStatus()
  if (status.pendingReconnect || status.connected) {
    // 上次是连接状态，尝试恢复
    updateBadge(status.connected ? 'on' : 'connecting')
    if (status.connected) {
      void chrome.action.setTitle({ title: 'Neurone: 已连接 (点击断开)' })
    } else {
      void chrome.action.setTitle({ title: 'Neurone: 正在连接...' })
    }
    return true
  }
  // 默认断开状态
  updateBadge('off')
  void chrome.action.setTitle({ title: 'Neurone: 已断开 (点击连接)' })
  return false
}

// ==================== 主入口 ====================

const wsClient = new NeuroneWSClient()

async function main() {
  // 动态加载 CDP 适配器
  try {
    const cdpScript = document.createElement('script');
    cdpScript.src = chrome.runtime.getURL('cdp_adapter.js');
    // 由于这是在 background script 中执行，无法直接访问 document
    // CDP 适配器通过 eval 加载
  } catch (e) {
    console.log('[Neurone] CDP adapter will be loaded on demand')
  }

  // 恢复 badge 状态（Service Worker 重启时保持状态）
  console.log('[Neurone] 恢复 badge 状态...')
  const needsReconnect = await restoreBadgeState()

  // 注册工具
  registerTool(new InjectScriptTool())
  registerTool(new ReadPageDataTool())
  registerTool(new NavigateTool())
  registerTool(new BrowserControlTool())
  registerTool(new ExtractDataTool())
  registerTool(new ClickTool())
  registerTool(new FillTool())
  registerTool(new KeyboardTool())
  registerTool(new WaitElementsTool())
  registerTool(new ScreenshotTool())
  registerTool(new ScrollTool())
  registerTool(new GetPageInfoTool())
  registerTool(new A11yTreeTool())
  registerTool(new CDPTool())
  registerTool(new RecorderTool())

  console.log(`[Neurone] v${chrome.runtime.getManifest().version} 已加载`)
  console.log(`[Neurone] 已注册 ${toolRegistry.size} 个工具:`, Array.from(toolRegistry.keys()))

  // 自动连接
  const config = await getConnectionConfig()
  const status = await getServerStatus()
  console.log(`[Neurone] Relay URL: ${config.serverUrl}`)
  console.log(`[Neurone] 上次状态: pendingReconnect=${status.pendingReconnect}, connected=${status.connected}`)

  // 如果之前有连接或待重连，尝试恢复连接
  if (config.autoReconnect && (status.pendingReconnect || status.connected)) {
    // 清除待重连标记（即将重连）
    if (status.pendingReconnect) {
      await updateServerStatus({ pendingReconnect: false })
    }
    updateBadge('connecting')
    await wsClient.connect(config.serverUrl)
  }
}

// 点击图标：连接 / 断开
chrome.action.onClicked.addListener(async () => {
  if (wsClient.isConnected()) {
    wsClient.disconnect()
  } else {
    // 用户手动点击连接，清除待重连标记
    await updateServerStatus({ pendingReconnect: false })
    updateBadge('connecting')
    void chrome.action.setTitle({ title: 'Neurone: 正在连接...' })
    const config = await getConnectionConfig()
    const r = await wsClient.connect(config.serverUrl)
    if (!r.success) {
      updateBadge('error')
      void chrome.action.setTitle({ title: `Neurone: 连接失败 (${r.error})` })
    }
  }
})

// 安装时打开帮助页
chrome.runtime.onInstalled.addListener((d) => {
  if (d.reason === 'install') void chrome.runtime.openOptionsPage()
})

// 内部消息（popup / options 页面）
chrome.runtime.onMessage.addListener((req, _sender, sendResponse) => {
  const handle = async () => {
    switch (req.type) {
      case 'GET_STATUS':
        return { ...(await getServerStatus()), connected: wsClient.isConnected() }
      case 'CONNECT_WEBSOCKET':
        return await wsClient.connect(req.url)
      case 'DISCONNECT_WEBSOCKET':
        wsClient.disconnect(); return { success: true }
      case 'GET_CONNECTION_CONFIG':
        return await getConnectionConfig()
      case 'SAVE_CONNECTION_CONFIG':
        await chrome.storage.local.set({ [STORAGE_CONFIG]: req.config }); return { success: true }
      case 'EXECUTE_TOOL':
        return await executeTool(req.payload)
      case 'LIST_TOOLS':
        return Array.from(toolRegistry.keys())
      default:
        return { error: '未知消息类型' }
    }
  }
  handle().then(sendResponse).catch(e => sendResponse({ error: e.message }))
  return true  // 保持 sendResponse 通道
})

// 启动
void main()

// ========== 导出供测试 ==========
if (typeof window !== 'undefined') {
  window.A11yTreeGenerator = A11yTreeGenerator
  window.CDPAdapter = CDPAdapter;
  window.CDPError = CDPError;
  window.CDP_ERROR_CODES = CDP_ERROR_CODES;
  window.EventListener = EventListener;
  window.SelectorGenerator = SelectorGenerator;
  window.RecorderTool = RecorderTool;
}

// ========== CDP 工具 ==========

class CDPTool extends BaseTool {
  constructor() { super('cdp') }

  async execute({ domain, method, params, timeout, tabId }) {
    if (!domain || !method) return this.err('参数缺失: domain 和 method 是必填参数')

    const tid = await this.resolveTabId(tabId)
    await this.waitForTabLoad(tid).catch(() => {})

    // 在页面上下文中执行 CDP 命令
    const r = await this.execInTabMain(tid, (d, m, p, to) => {
      if (typeof CDPAdapter === 'undefined') {
        return { success: false, error: { message: 'CDPAdapter not loaded' } };
      }
      const adapter = CDPAdapter.create();
      return adapter.executeCommand(d, m, p, to);
    }, [domain, method, params || {}, timeout || 30000])

    if (r && r.success) {
      return this.ok(r)
    } else {
      return this.fail(r?.error?.message || 'CDP 命令执行失败')
    }
  }
}

// ========== 录制工具 ==========

class SelectorGenerator {
  generate(element) {
    if (element.id) return `#${element.id}`;
    const testId = element.getAttribute("data-testid");
    if (testId) return `[data-testid="${testId}"]`;
    const dataRole = element.getAttribute("data-role");
    if (dataRole) return `[data-role="${dataRole}"]`;
    return this._generateCssPath(element);
  }

  _generateCssPath(element) {
    if (element.id) return `#${element.id}`;
    const path = [];
    let current = element;
    let depth = 0;
    const maxDepth = 5;
    while (current && current !== document.documentElement && depth < maxDepth) {
      let selector = current.tagName.toLowerCase();
      if (current.id) {
        selector = `#${current.id}`;
        path.unshift(selector);
        break;
      }
      const parent = current.parentElement;
      if (parent) {
        const siblings = parent.querySelectorAll(`:scope > ${current.tagName.toLowerCase()}`);
        if (siblings.length > 1) {
          const index = Array.from(siblings).indexOf(current) + 1;
          selector += `:nth-of-type(${index})`;
        }
      }
      path.unshift(selector);
      current = parent;
      depth++;
    }
    return path.join(" > ");
  }
}

class EventListener {
  constructor(options = {}) {
    this.options = {
      recordClicks: true,
      recordKeyboard: true,
      recordInput: true,
      recordScroll: true,
      recordNavigation: true,
      recordScreenshot: false,
      screenshotInterval: 5000,
      filterSelector: null,
      onAction: null,
      ...options,
    };
    this._isRecording = false;
    this._actions = [];
    this._actionIndex = 0;
    this._startTime = null;
    this._pageUrl = null;
    this._pageTitle = null;
    this._listeners = {};
    this._screenshotTimer = null;
    this._lastScreenshot = null;
    this._lastScrollPosition = { x: 0, y: 0 };
    this._boundHandler = this._handleEvent.bind(this);
    this._selectorGenerator = new SelectorGenerator();
  }

  get isRecording() { return this._isRecording; }
  get actions() { return [...this._actions]; }
  get actionCount() { return this._actions.length; }
  get duration() { return this._startTime ? Date.now() - this._startTime : 0; }

  async start() {
    if (this._isRecording) return false;
    this._isRecording = true;
    this._actions = [];
    this._startTime = Date.now();
    this._pageUrl = window.location.href;
    this._pageTitle = document.title;
    this._lastScrollPosition = { x: window.scrollX, y: window.scrollY };
    this._attachListeners();
    if (this.options.recordScreenshot) this._startScreenshotTimer();
    return true;
  }

  stop() {
    if (!this._isRecording) return this._actions;
    this._isRecording = false;
    this._detachListeners();
    this._stopScreenshotTimer();
    return { actions: this._actions, metadata: { startTime: this._startTime, endTime: Date.now(), duration: this.duration, pageUrl: this._pageUrl, pageTitle: this._pageTitle, actionCount: this._actions.length } };
  }

  pause() { if (!this._isRecording) return false; this._isRecording = false; this._detachListeners(); this._stopScreenshotTimer(); return true; }

  resume() { if (this._isRecording) return false; this._isRecording = true; this._attachListeners(); if (this.options.recordScreenshot) this._startScreenshotTimer(); return true; }

  clear() { this._actions = []; this._startTime = null; this._actionIndex = 0; }

  _attachListeners() {
    if (this.options.recordClicks) { window.addEventListener("click", this._boundHandler, true); window.addEventListener("dblclick", this._boundHandler, true); }
    if (this.options.recordKeyboard) { window.addEventListener("keydown", this._boundHandler, true); window.addEventListener("keyup", this._boundHandler, true); }
    if (this.options.recordInput) { window.addEventListener("input", this._boundHandler, true); window.addEventListener("change", this._boundHandler, true); }
    if (this.options.recordScroll) { window.addEventListener("scroll", this._boundHandler, false); }
    if (this.options.recordNavigation) { window.addEventListener("hashchange", this._boundHandler); }
  }

  _detachListeners() {
    if (this.options.recordClicks) { window.removeEventListener("click", this._boundHandler, true); window.removeEventListener("dblclick", this._boundHandler, true); }
    if (this.options.recordKeyboard) { window.removeEventListener("keydown", this._boundHandler, true); window.removeEventListener("keyup", this._boundHandler, true); }
    if (this.options.recordInput) { window.removeEventListener("input", this._boundHandler, true); window.removeEventListener("change", this._boundHandler, true); }
    if (this.options.recordScroll) { window.removeEventListener("scroll", this._boundHandler, false); }
    if (this.options.recordNavigation) { window.removeEventListener("hashchange", this._boundHandler); }
  }

  async _handleEvent(event) {
    if (!this._isRecording) return;
    const target = event.target;
    if (!target || !(target instanceof Element)) return;
    if (this._shouldIgnore(target)) return;
    const selector = this._selectorGenerator.generate(target);
    if (!selector) return;
    const action = { id: `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`, type: this._getActionType(event), timestamp: Date.now(), offset: Date.now() - this._startTime, pageUrl: window.location.href, target: { selector, tag: target.tagName.toLowerCase(), text: (target.innerText || "").trim().slice(0, 200), role: target.getAttribute("role") || "", inputType: target.type || "", href: target.href || "", placeholder: target.getAttribute("placeholder") || "" }, params: {}, position: { x: event.clientX, y: event.clientY, screenX: event.screenX, screenY: event.screenY } };
    this._addEventParams(action, event, target);
    action.index = this._actionIndex++;
    this._actions.push(action);
  }

  _shouldIgnore(element) {
    if (element.tagName === "SCRIPT" || element.tagName === "STYLE") return true;
    if (element.hidden) return true;
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") return true;
    return !!element.closest("[data-neurone-ignore]");
  }

  _getActionType(event) {
    const map = { "click": "click", "dblclick": "double_click", "keydown": "keydown", "keyup": "keyup", "input": "input", "change": "change", "scroll": "scroll", "hashchange": "hash_change" };
    return map[event.type] || event.type;
  }

  _addEventParams(action, event, target) {
    switch (action.type) {
      case "click": case "double_click": action.params = { button: ["left", "middle", "right"][event.button] || "left", clickCount: event.detail || 1 }; break;
      case "keydown": case "keyup": action.params = { key: event.key, code: event.code, repeat: event.repeat }; if (event.ctrlKey) action.params.ctrlKey = true; if (event.altKey) action.params.altKey = true; if (event.shiftKey) action.params.shiftKey = true; if (event.metaKey) action.params.metaKey = true; break;
      case "input": case "change": action.params = { value: target.value || "", checked: target.checked }; break;
      case "scroll": action.params = { scrollX: window.scrollX, scrollY: window.scrollY, deltaX: event.deltaX, deltaY: event.deltaY }; break;
    }
  }

  _startScreenshotTimer() { this._screenshotTimer = setInterval(() => { if (this._isRecording) this._lastScreenshot = { timestamp: Date.now(), scrollPosition: { x: window.scrollX, y: window.scrollY }, url: window.location.href }; }, this.options.screenshotInterval); }
  _stopScreenshotTimer() { if (this._screenshotTimer) { clearInterval(this._screenshotTimer); this._screenshotTimer = null; } }
}

class RecorderTool extends BaseTool {
  constructor() { super('recorder') }

  async execute({ action = 'status', tabId }) {
    const tid = await this.resolveTabId(tabId)
    const r = await this.execInTabMain(tid, (act) => {
      const key = '__neurone_recorder';
      if (!window[key]) window[key] = new EventListener();
      const recorder = window[key];
      switch (act) {
        case 'start': recorder.start(); return { success: true, isRecording: recorder.isRecording };
        case 'stop': const result = recorder.stop(); return { success: true, isRecording: false, actions: result.actions.length, metadata: result.metadata };
        case 'pause': recorder.pause(); return { success: true, isRecording: recorder.isRecording };
        case 'resume': recorder.resume(); return { success: true, isRecording: recorder.isRecording };
        case 'clear': recorder.clear(); return { success: true, actionCount: 0 };
        case 'status': return { success: true, isRecording: recorder.isRecording, actionCount: recorder.actionCount, duration: recorder.duration };
        case 'get_actions': return { success: true, actions: recorder.actions };
        case 'export': return { success: true, data: JSON.stringify(recorder.stop()) };
        default: return { success: false, error: `Unknown action: ${act}` };
      }
    }, [action])
    return this.ok(r)
  }
}
