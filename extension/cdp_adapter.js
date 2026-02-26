/**
 * CDP 兼容层 (CDPAdapter)

提供对 Chrome DevTools Protocol (CDP) 命令的兼容性抽象。

功能：
1. 统一的命令接口
2. 便于未来迁移
3. 与其他工具链集成
4. 支持获取调试端口（用于混合模式）
5. 支持真实无障碍树获取

支持的命令域：
- Runtime: 脚本执行
- DOM: DOM 操作
- Page: 页面控制
- Network: 网络请求（受限）
- Accessibility: 无障碍访问

混合模式支持：
- 可获取当前 Chrome 的调试端口
- 通过 WebSocket 连接到真实 CDP 获取真实无障碍树
*/

// ==================== 错误码定义 ====================

const CDP_ERROR_CODES = {
  // 成功
  SUCCESS: { code: 0, message: 'Success' },

  // 通用错误
  UNKNOWN: { code: -1, message: 'Unknown error' },
  INVALID_PARAMS: { code: -32600, message: 'Invalid parameters' },
  METHOD_NOT_FOUND: { code: -32601, message: 'Method not found' },
  INTERNAL_ERROR: { code: -32603, message: 'Internal error' },

  // 执行错误
  EVALUATION_ERROR: { code: 1001, message: 'Evaluation error' },
  EVALUATION_TIMEOUT: { code: 1002, message: 'Evaluation timeout' },
  SCRIPT_ERROR: { code: 1003, message: 'Script error' },

  // DOM 错误
  DOM_ERROR: { code: 2001, message: 'DOM operation error' },
  NODE_NOT_FOUND: { code: 2002, message: 'Node not found' },
  INVALID_NODE_TYPE: { code: 2003, message: 'Invalid node type' },

  // 页面错误
  PAGE_ERROR: { code: 3001, message: 'Page error' },
  NAVIGATION_ERROR: { code: 3002, message: 'Navigation error' },

  // 权限错误
  PERMISSION_DENIED: { code: 4001, message: 'Permission denied' },
};

// ==================== 工具注册表 ====================

class CDPAdapter {
  constructor() {
    this.commandHandlers = new Map();
    this.eventListeners = new Map();
    this.defaultTimeout = 30000; // 默认超时 30s
    this._registerDefaultHandlers();
  }

  // ========== 装饰器 ==========

  /**
   * 注册命令处理器
   */
  registerCommand(domain, method, handler, options = {}) {
    const commandName = `${domain}.${method}`;
    this.commandHandlers.set(commandName, {
      handler,
      timeout: options.timeout || this.defaultTimeout,
      validate: options.validate || null,
    });
  }

  /**
   * 注册事件监听器
   */
  onEvent(eventName, listener) {
    if (!this.eventListeners.has(eventName)) {
      this.eventListeners.set(eventName, []);
    }
    this.eventListeners.get(eventName).push(listener);
  }

  /**
   * 移除事件监听器
   */
  offEvent(eventName, listener) {
    const listeners = this.eventListeners.get(eventName);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index !== -1) {
        listeners.splice(index, 1);
      }
    }
  }

  /**
   * 触发事件
   */
  emitEvent(eventName, data) {
    const listeners = this.eventListeners.get(eventName) || [];
    listeners.forEach(listener => {
      try {
        listener(data);
      } catch (e) {
        console.error(`[CDPAdapter] Event handler error: ${e.message}`);
      }
    });
  }

  // ========== 命令执行 ==========

  /**
   * 执行命令
   */
  async executeCommand(domain, method, params = {}, timeout = null) {
    const commandName = `${domain}.${method}`;
    const command = this.commandHandlers.get(commandName);

    if (!command) {
      return this._createErrorResponse(
        CDP_ERROR_CODES.METHOD_NOT_FOUND,
        `Command not found: ${commandName}`
      );
    }

    // 参数验证
    if (command.validate) {
      const validation = command.validate(params);
      if (!validation.valid) {
        return this._createErrorResponse(
          CDP_ERROR_CODES.INVALID_PARAMS,
          `Invalid parameters: ${validation.errors.join(', ')}`,
          { validationErrors: validation.errors }
        );
      }
    }

    // 执行命令
    const startTime = Date.now();
    try {
      const result = await Promise.race([
        command.handler(params),
        this._createTimeoutPromise(timeout || command.timeout),
      ]);

      return this._createSuccessResponse(commandName, result, Date.now() - startTime);

    } catch (e) {
      console.error(`[CDPAdapter] Command execution error: ${commandName}`, e);
      return this._createErrorResponse(
        CDP_ERROR_CODES.INTERNAL_ERROR,
        e.message,
        { exceptionType: e.constructor.name }
      );
    }
  }

  /**
   * 批量执行命令
   */
  async executeCommands(commands) {
    const results = [];
    for (const { domain, method, params } of commands) {
      const result = await this.executeCommand(domain, method, params);
      results.push({ domain, method, result });
    }
    return results;
  }

  // ========== 工具方法 ==========

  /**
   * 执行 JS 表达式
   */
  async evaluate(expression, options = {}) {
    return this.executeCommand('Runtime', 'evaluate', {
      expression,
      returnByValue: options.returnByValue || false,
      awaitPromise: options.awaitPromise || false,
      userGesture: options.userGesture || false,
      timeout: options.timeout,
    });
  }

  /**
   * 调用函数
   */
  async callFunctionOn(objectId, functionDeclaration, args = []) {
    return this.executeCommand('Runtime', 'callFunctionOn', {
      objectId,
      functionDeclaration,
      arguments: args,
      returnByValue: true,
    });
  }

  /**
   * 获取 DOM
   */
  async getDocument() {
    return this.executeCommand('DOM', 'getDocument');
  }

  /**
   * 查询选择器
   */
  async querySelector(nodeId, selector) {
    return this.executeCommand('DOM', 'querySelector', { nodeId, selector });
  }

  /**
   * 获取无障碍树
   */
  async getFullAXTree() {
    return this.executeCommand('Accessibility', 'getFullAXTree');
  }

  // ========== 调试端口（混合模式用）==========

  /**
   * 获取 Chrome 调试端口信息
   * 用于混合模式：Puppeteer 启动的浏览器可以通过此获取 CDP 连接
   */
  async getDebugPort() {
    return this.executeCommand('Browser', 'getDebugPort');
  }

  /**
   * 通过真实 CDP 获取无障碍树
   * 此方法在混合模式下由 Python 端调用
   */
  async getAccessibilityTreeViaCDP() {
    try {
      // 获取调试端口
      const debugInfo = await this.getDebugPort();
      if (!debugInfo.success || !debugInfo.data) {
        return this._createErrorResponse(
          CDP_ERROR_CODES.INTERNAL_ERROR,
          '无法获取调试端口'
        );
      }

      const { host, port } = debugInfo.data;

      // 通过 WebSocket 连接 CDP
      return new Promise((resolve) => {
        const ws = new WebSocket(`ws://${host}:${port}`);

        ws.onopen = () => {
          // 发送 Accessibility.getFullAXTree 命令
          ws.send(JSON.stringify({
            id: 1,
            method: 'Accessibility.getFullAXTree',
            params: {}
          }));
        };

        ws.onmessage = (event) => {
          const response = JSON.parse(event.data);
          ws.close();
          resolve(this._createSuccessResponse('Accessibility.getFullAXTree', response.result || {}));
        };

        ws.onerror = (error) => {
          resolve(this._createErrorResponse(
            CDP_ERROR_CODES.INTERNAL_ERROR,
            `CDP 连接错误: ${error.message}`
          ));
        };

        // 超时处理
        setTimeout(() => {
          ws.close();
          resolve(this._createErrorResponse(
            CDP_ERROR_CODES.EVALUATION_TIMEOUT,
            'CDP 请求超时'
          ));
        }, 10000);
      });
    } catch (e) {
      return this._createErrorResponse(
        CDP_ERROR_CODES.INTERNAL_ERROR,
        `获取无障碍树失败: ${e.message}`
      );
    }
  }

  // ========== 内部方法 ==========

  _registerDefaultHandlers() {
    // Runtime.evaluate 处理器
    this.registerCommand('Runtime', 'evaluate', async (params) => {
      const { expression, returnByValue = true } = params;

      try {
        // 使用 Function 构造函数执行表达式
        const result = new Function(`return (${expression})`)();

        if (result instanceof Promise) {
          const awaited = await result;
          return returnByValue ? this._serializeValue(awaited) : awaited;
        }

        return returnByValue ? this._serializeValue(result) : result;

      } catch (e) {
        throw new CDPError(
          CDP_ERROR_CODES.EVALUATION_ERROR.code,
          `Evaluation failed: ${e.message}`
        );
      }
    }, {
      validate: (params) => {
        if (!params.expression) {
          return { valid: false, errors: ['expression is required'] };
        }
        return { valid: true };
      },
      timeout: 10000,
    });

    // Runtime.callFunctionOn 处理器
    this.registerCommand('Runtime', 'callFunctionOn', async (params) => {
      const { objectId, functionDeclaration, arguments: args = [] } = params;

      // 从 objectId 恢复对象
      // objectId 格式: "obj-{selector}" 或 "obj-{index}"
      let target;
      if (objectId.startsWith('obj-')) {
        const selector = objectId.slice(4);
        target = document.querySelector(selector);
      }

      if (!target) {
        throw new CDPError(
          CDP_ERROR_CODES.NODE_NOT_FOUND.code,
          `Object not found: ${objectId}`
        );
      }

      // 创建函数并调用
      const fn = new Function('target', 'args', functionDeclaration);
      const result = fn(target, args);

      return this._serializeValue(result);

    }, {
      validate: (params) => {
        if (!params.objectId) {
          return { valid: false, errors: ['objectId is required'] };
        }
        if (!params.functionDeclaration) {
          return { valid: false, errors: ['functionDeclaration is required'] };
        }
        return { valid: true };
      },
    });

    // DOM.getDocument 处理器
    this.registerCommand('DOM', 'getDocument', async () => {
      return {
        root: {
          nodeId: 1,
          nodeType: 9, // DOCUMENT_NODE
          nodeName: 'HTML',
          children: [],
        },
      };
    });

    // DOM.querySelector 处理器
    this.registerCommand('DOM', 'querySelector', async (params) => {
      const { nodeId, selector } = params;

      const elements = document.querySelectorAll(selector);
      if (elements.length === 0) {
        throw new CDPError(
          CDP_ERROR_CODES.NODE_NOT_FOUND.code,
          `No node found for selector: ${selector}`
        );
      }

      const el = elements[0];
      return {
        nodeId: `obj-${this._generateCssPath(el)}`,
        backendNodeId: elements.length,
      };
    });

    // Accessibility.getFullAXTree 处理器
    this.registerCommand('Accessibility', 'getFullAXTree', async () => {
      // 使用已有的 A11yTreeGenerator
      if (typeof A11yTreeGenerator !== 'undefined') {
        const generator = new A11yTreeGenerator();
        return generator.buildFullTree();
      }

      // 如果没有 A11yTreeGenerator，返回空树
      return {
        nodes: {},
        rootIds: [],
        totalNodes: 0,
        timestamp: Date.now(),
      };
    });

    // Browser.getDebugPort 处理器 - 获取调试端口信息
    this.registerCommand('Browser', 'getDebugPort', async () => {
      // 尝试获取 Chrome 调试端口
      // 注意：扩展内无法直接获取调试端口，需要通过特定方式
      // 这里返回一个标记，由 Python 端处理

      // 方法1: 尝试从 chrome.runtime 获取（如果有的话）
      if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.id) {
        // 扩展模式，返回特殊标记
        return {
          mode: 'extension',
          message: '扩展模式，需要通过 Python 端连接',
        };
      }

      // 默认返回unknow
      return {
        mode: 'unknown',
        message: '无法确定浏览器模式',
      };
    });
  }

  _createTimeoutPromise(timeout) {
    return new Promise((_, reject) => {
      setTimeout(() => {
        reject(new CDPError(
          CDP_ERROR_CODES.EVALUATION_TIMEOUT.code,
          `Command execution timeout: ${timeout}ms`
        ));
      }, timeout);
    });
  }

  _createSuccessResponse(command, result, duration) {
    return {
      success: true,
      command,
      data: result,
      meta: {
        command,
        durationMs: duration,
        timestamp: new Date().toISOString(),
      },
    };
  }

  _createErrorResponse(error, message, details = {}) {
    return {
      success: false,
      error: {
        code: error.code,
        message: message,
        data: details,
      },
      meta: {
        timestamp: new Date().toISOString(),
      },
    };
  }

  _serializeValue(value) {
    if (value === undefined) return { type: 'undefined' };
    if (value === null) return { type: 'null' };
    if (typeof value === 'string') return { type: 'string', value };
    if (typeof value === 'number') return { type: 'number', value };
    if (typeof value === 'boolean') return { type: 'boolean', value };
    if (Array.isArray(value)) {
      return { type: 'array', value: value.map(v => this._serializeValue(v)) };
    }
    if (typeof value === 'object') {
      const serialized = {};
      for (const [k, v] of Object.entries(value)) {
        serialized[k] = this._serializeValue(v);
      }
      return { type: 'object', value: serialized };
    }
    return { type: 'unknown', value: String(value) };
  }

  _generateCssPath(el) {
    if (el.id) return `#${el.id}`;
    const path = [];
    let current = el;
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      if (current.id) {
        selector = `#${current.id}`;
        path.unshift(selector);
        break;
      }
      const parent = current.parentElement;
      if (parent) {
        const siblings = parent.querySelectorAll(':scope > ' + current.tagName.toLowerCase());
        if (siblings.length > 1) {
          const index = Array.from(siblings).indexOf(current) + 1;
          selector += `:nth-of-type(${index})`;
        }
      }
      path.unshift(selector);
      current = parent;
    }
    return path.join(' > ');
  }

  // ========== 静态方法 ==========

  static create() {
    return new CDPAdapter();
  }

  static getErrorCodes() {
    return CDP_ERROR_CODES;
  }
}

// ==================== CDP 错误类 ====================

class CDPError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'CDPError';
    this.code = code;
  }
}

// ==================== 导出 ====================

if (typeof window !== 'undefined') {
  window.CDPAdapter = CDPAdapter;
  window.CDPError = CDPError;
  window.CDP_ERROR_CODES = CDP_ERROR_CODES;
}

// 导出供模块系统使用
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CDPAdapter, CDPError, CDP_ERROR_CODES };
}