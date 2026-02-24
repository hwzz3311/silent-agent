/**
 * 事件监听器 (EventListener)

捕获用户操作并序列化为结构化数据。

支持的事件类型:
- 鼠标事件: mousedown, mouseup, click, dblclick
- 键盘事件: keydown, keyup, keypress
- 输入事件: input, change
- 导航事件: beforeunload, hashchange
- 自定义事件: navigate, scroll

使用示例:
```javascript
const recorder = new EventListener({
  recordClicks: true,
  recordKeyboard: true,
  recordInput: true,
  recordScroll: true,
  recordNavigation: true,
});

// 开始录制
await recorder.start();

// ... 用户操作 ...

// 停止录制并获取结果
const actions = recorder.stop();

// 获取当前录制状态
const isRecording = recorder.isRecording();
```
*/

class EventListener {
  /**
   * @param {Object} options - 配置选项
   * @param {boolean} options.recordClicks - 记录点击事件
   * @param {boolean} options.recordKeyboard - 记录键盘事件
   * @param {boolean} options.recordInput - 记录输入事件
   * @param {boolean} options.recordScroll - 记录滚动事件
   * @param {boolean} options.recordNavigation - 记录导航事件
   * @param {boolean} options.recordScreenshot - 记录截图
   * @param {number} options.screenshotInterval - 截图间隔（毫秒）
   * @param {Function} options.filterSelector - 选择器过滤函数
   * @param {Function} options.onAction - 动作记录回调
   */
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

    // 绑定 this
    this._boundHandler = this._handleEvent.bind(this);
  }

  // ========== 属性 ==========

  get isRecording() {
    return this._isRecording;
  }

  get actions() {
    return [...this._actions];
  }

  get actionCount() {
    return this._actions.length;
  }

  get duration() {
    if (!this._startTime) return 0;
    return Date.now() - this._startTime;
  }

  // ========== 录制控制 ==========

  /**
   * 开始录制
   */
  async start() {
    if (this._isRecording) {
      console.warn("[EventListener] 已经在录制中");
      return false;
    }

    this._isRecording = true;
    this._actions = [];
    this._startTime = Date.now();
    this._pageUrl = window.location.href;
    this._pageTitle = document.title;
    this._lastScrollPosition = { x: window.scrollX, y: window.scrollY };
    this._lastScreenshot = null;

    // 初始化选择器生成器
    this._selectorGenerator = new SelectorGenerator();

    // 注册事件监听器
    this._attachListeners();

    // 开始截图定时器
    if (this.options.recordScreenshot) {
      this._startScreenshotTimer();
    }

    console.log("[EventListener] 开始录制");
    return true;
  }

  /**
   * 停止录制
   */
  stop() {
    if (!this._isRecording) {
      console.warn("[EventListener] 未在录制中");
      return this._actions;
    }

    this._isRecording = false;

    // 停止截图定时器
    this._stopScreenshotTimer();

    // 移除事件监听器
    this._detachListeners();

    // 添加元数据
    const result = {
      actions: this._actions,
      metadata: {
        startTime: this._startTime,
        endTime: Date.now(),
        duration: this.duration,
        pageUrl: this._pageUrl,
        pageTitle: this._pageTitle,
        actionCount: this._actions.length,
      },
    };

    console.log(`[EventListener] 停止录制，共 ${this._actions.length} 个动作`);
    return result;
  }

  /**
   * 暂停录制
   */
  pause() {
    if (!this._isRecording) return false;

    this._isRecording = false;
    this._detachListeners();
    this._stopScreenshotTimer();

    console.log("[EventListener] 录制暂停");
    return true;
  }

  /**
   * 恢复录制
   */
  resume() {
    if (this._isRecording) return false;

    this._isRecording = true;
    this._attachListeners();

    if (this.options.recordScreenshot) {
      this._startScreenshotTimer();
    }

    console.log("[EventListener] 录制恢复");
    return true;
  }

  /**
   * 清除录制
   */
  clear() {
    this._actions = [];
    this._startTime = null;
    this._actionIndex = 0;
    console.log("[EventListener] 录制已清除");
  }

  /**
   * 导出录制数据
   */
  export(format = "json") {
    if (format === "json") {
      return JSON.stringify(this.stop(), null, 2);
    }
    return this.stop();
  }

  /**
   * 获取录制数据（JSON 格式）
   */
  getJSON() {
    return {
      actions: this._actions,
      metadata: {
        startTime: this._startTime,
        endTime: Date.now(),
        duration: this.duration,
        pageUrl: this._pageUrl,
        pageTitle: this._pageTitle,
        actionCount: this._actions.length,
      },
    };
  }

  // ========== 事件监听 ==========

  _attachListeners() {
    const options = this.options;

    if (options.recordClicks) {
      this._addListener("click", this._boundHandler, true);
      this._addListener("dblclick", this._boundHandler, true);
    }

    if (options.recordKeyboard) {
      this._addListener("keydown", this._boundHandler, true);
      this._addListener("keyup", this._boundHandler, true);
    }

    if (options.recordInput) {
      this._addListener("input", this._boundHandler, true);
      this._addListener("change", this._boundHandler, true);
    }

    if (options.recordScroll) {
      this._addListener("scroll", this._boundHandler, false);
    }

    if (options.recordNavigation) {
      window.addEventListener("beforeunload", this._boundHandler);
      window.addEventListener("hashchange", this._boundHandler);
    }
  }

  _detachListeners() {
    const options = this.options;

    if (options.recordClicks) {
      this._removeListener("click", this._boundHandler, true);
      this._removeListener("dblclick", this._boundHandler, true);
    }

    if (options.recordKeyboard) {
      this._removeListener("keydown", this._boundHandler, true);
      this._removeListener("keyup", this._boundHandler, true);
    }

    if (options.recordInput) {
      this._removeListener("input", this._boundHandler, true);
      this._removeListener("change", this._boundHandler, true);
    }

    if (options.recordScroll) {
      this._removeListener("scroll", this._boundHandler, false);
    }

    if (options.recordNavigation) {
      window.removeEventListener("beforeunload", this._boundHandler);
      window.removeEventListener("hashchange", this._boundHandler);
    }
  }

  _addListener(event, handler, capture) {
    window.addEventListener(event, handler, capture);
    this._listeners[event] = { handler, capture };
  }

  _removeListener(event, handler, capture) {
    window.removeEventListener(event, handler, capture);
    delete this._listeners[event];
  }

  // ========== 事件处理 ==========

  async _handleEvent(event) {
    if (!this._isRecording) return;

    // 获取目标元素
    const target = event.target;
    if (!target || !(target instanceof Element)) return;

    // 过滤不需要的元素
    if (this._shouldIgnore(target)) return;

    // 生成选择器
    const selector = this._selectorGenerator.generate(target);
    if (!selector) return;

    // 获取元素信息
    const elementInfo = this._getElementInfo(target);

    // 创建动作记录
    const action = {
      id: this._generateId(),
      type: this._getActionType(event),
      timestamp: Date.now(),
      offset: Date.now() - this._startTime,
      pageUrl: window.location.href,
      target: {
        selector: selector,
        tag: target.tagName.toLowerCase(),
        text: elementInfo.text,
        role: elementInfo.role,
        inputType: elementInfo.inputType,
        href: elementInfo.href,
        placeholder: elementInfo.placeholder,
      },
      params: {},
      position: {
        x: event.clientX,
        y: event.clientY,
        screenX: event.screenX,
        screenY: event.screenY,
      },
    };

    // 根据事件类型添加特定参数
    this._addEventParams(action, event, target);

    // 记录动作
    this._recordAction(action);
  }

  _shouldIgnore(element) {
    // 忽略脚本和样式
    if (element.tagName === "SCRIPT" || element.tagName === "STYLE") {
      return true;
    }

    // 忽略隐藏元素
    if (element.hidden) return true;
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") {
      return true;
    }

    // 忽略不可点击的元素
    const clickable = element.closest("[data-neurone-ignore]");
    if (clickable) return true;

    // 自定义过滤
    if (this.options.filterSelector) {
      const selector = this._selectorGenerator.generate(element);
      if (selector && !this.options.filterSelector(selector, element)) {
        return true;
      }
    }

    return false;
  }

  _getActionType(event) {
    const type = event.type;

    // 鼠标事件
    if (type === "click") return "click";
    if (type === "dblclick") return "double_click";

    // 键盘事件
    if (type === "keydown") return "keydown";
    if (type === "keyup") return "keyup";

    // 输入事件
    if (type === "input") return "input";
    if (type === "change") return "change";

    // 滚动事件
    if (type === "scroll") return "scroll";

    // 导航事件
    if (type === "beforeunload") return "page_unload";
    if (type === "hashchange") return "hash_change";

    return type;
  }

  _addEventParams(action, event, target) {
    switch (action.type) {
      case "click":
      case "double_click":
        action.params = {
          button: ["left", "middle", "right"][event.button] || "left",
          clickCount: event.detail || 1,
        };
        break;

      case "keydown":
      case "keyup":
        action.params = {
          key: event.key,
          code: event.code,
          keyCode: event.keyCode,
          repeat: event.repeat,
        };
        // 修饰键
        if (event.ctrlKey) action.params.ctrlKey = true;
        if (event.altKey) action.params.altKey = true;
        if (event.shiftKey) action.params.shiftKey = true;
        if (event.metaKey) action.params.metaKey = true;
        break;

      case "input":
      case "change":
        action.params = {
          value: target.value || "",
          checked: target.checked,
        };
        break;

      case "scroll":
        action.params = {
          scrollX: window.scrollX,
          scrollY: window.scrollY,
          deltaX: event.deltaX,
          deltaY: event.deltaY,
          deltaMode: event.deltaMode,
        };
        break;
    }
  }

  _getElementInfo(element) {
    const info = {
      text: "",
      role: "",
      inputType: "",
      href: "",
      placeholder: "",
    };

    // 获取文本
    if (element.tagName !== "INPUT" && element.tagName !== "TEXTAREA") {
      info.text = (element.innerText || "").trim().slice(0, 200);
    }

    // 获取 ARIA role
    info.role = element.getAttribute("role") || "";

    // 获取 input 类型
    if (element.tagName === "INPUT") {
      info.inputType = element.type || "text";
    }

    // 获取链接
    if (element.tagName === "A") {
      info.href = element.href || "";
    }

    // 获取 placeholder
    info.placeholder = element.getAttribute("placeholder") || "";

    return info;
  }

  // ========== 截图功能 ==========

  _startScreenshotTimer() {
    this._screenshotTimer = setInterval(() => {
      if (this._isRecording) {
        this._captureScreenshot();
      }
    }, this.options.screenshotInterval);
  }

  _stopScreenshotTimer() {
    if (this._screenshotTimer) {
      clearInterval(this._screenshotTimer);
      this._screenshotTimer = null;
    }
  }

  async _captureScreenshot() {
    try {
      // 使用 html2canvas 或类似库（需要注入）
      // 简化版本：记录当前状态
      this._lastScreenshot = {
        timestamp: Date.now(),
        scrollPosition: { x: window.scrollX, y: window.scrollY },
        url: window.location.href,
      };
    } catch (e) {
      console.warn("[EventListener] 截图失败:", e);
    }
  }

  // ========== 动作记录 ==========

  _recordAction(action) {
    // 添加动作索引
    action.index = this._actionIndex++;
    this._actions.push(action);

    // 调用回调
    if (this.options.onAction) {
      try {
        this.options.onAction(action);
      } catch (e) {
        console.warn("[EventListener] 回调错误:", e);
      }
    }

    // 记录日志
    console.log(`[EventListener] 记录动作: ${action.type} (${action.index})`);
  }

  // ========== 工具方法 ==========

  _generateId() {
    return `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// ==================== 选择器生成器 ====================

class SelectorGenerator {
  /**
   * 生成元素的选择器
   */
  generate(element) {
    if (element.id) {
      return `#${element.id}`;
    }

    // 优先使用 data-testid
    const testId = element.getAttribute("data-testid");
    if (testId) {
      return `[data-testid="${testId}"]`;
    }

    // 优先使用 data-role
    const dataRole = element.getAttribute("data-role");
    if (dataRole) {
      return `[data-role="${dataRole}"]`;
    }

    // 生成 CSS 路径
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

    const result = path.join(" > ");
    return result.length < 200 ? result : this._generateSimpleSelector(element);
  }

  _generateSimpleSelector(element) {
    // 降级为简单选择器
    if (element.tagName === "INPUT") {
      const type = element.type || "text";
      const name = element.name ? `[name="${element.name}"]` : "";
      const placeholder = element.placeholder ? `[placeholder="${element.placeholder}"]` : "";
      return `input[type="${type}"]${name}${placeholder}`.slice(0, 100);
    }

    return `${element.tagName.toLowerCase()}[${element.className.split(" ")[0] || ""}]`.slice(0, 100);
  }
}

// ==================== 录制工具类 ====================

class RecorderTool extends BaseTool {
  constructor() { super('recorder') }

  async execute({ action = 'status', tabId }) {
    const tid = await this.resolveTabId(tabId)

    const r = await this.execInTabMain(tid, (act) => {
      if (typeof EventListener === 'undefined') {
        return { success: false, error: 'EventListener not loaded' }
      }

      const key = '__neurone_recorder'
      window[key] = window[key] || new EventListener()

      switch (act) {
        case 'start':
          window[key].start()
          return { success: true, isRecording: window[key].isRecording }

        case 'stop':
          const result = window[key].stop()
          return { success: true, isRecording: false, actions: result.actions.length, metadata: result.metadata }

        case 'pause':
          window[key].pause()
          return { success: true, isRecording: window[key].isRecording }

        case 'resume':
          window[key].resume()
          return { success: true, isRecording: window[key].isRecording }

        case 'clear':
          window[key].clear()
          return { success: true, actionCount: 0 }

        case 'status':
          return {
            success: true,
            isRecording: window[key].isRecording,
            actionCount: window[key].actionCount,
            duration: window[key].duration,
          }

        case 'get_actions':
          return { success: true, actions: window[key].actions }

        case 'export':
          return { success: true, data: window[key].export() }

        default:
          return { success: false, error: `Unknown action: ${act}` }
      }
    }, [action])

    return this.ok(r)
  }
}

// ==================== 导出 ====================

if (typeof window !== 'undefined') {
  window.EventListener = EventListener;
  window.SelectorGenerator = SelectorGenerator;
  window.RecorderTool = RecorderTool;
}

// 导出供模块系统使用
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { EventListener, SelectorGenerator, RecorderTool };
}