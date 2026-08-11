/**
 * ux-dom XElement browser runtime — `x_element.js`
 *
 * Used with Python:
 *   from ux_dom.dom import XElement, CustomElement, WebComponent, AlpineComponent
 *   from ux_dom.scripts import x_element_js
 *
 * Contract (one name, one attribute):
 *   Python class ………… XElement (and subclasses)
 *   Definition attr …… x-tagname="toggle"   on <template> / definition node
 *   Custom element ……… <x-toggle>           (prefix "x-" + tag name)
 *   This file …………… x_element.js          served via x_element_js Component
 *
 * Load once per page (preferred URL from package mount):
 *   <script src="/ux-dom/static/x_element.js" defer></script>
 *
 * Single-copy model: this file lives in the installed ux_dom package.
 * Default Document/XElementRuntime serves it from site-packages — do not
 * maintain a divergent dual copy under app assets/js/ (skews after upgrades).
 *
 * Optional companions: Alpine.js (x-data inside the definition), HTMX
 * (htmx:afterSwap re-scans for new x-tagname definitions).
 *
 * Public browser API: window.UxDom.XElement { scan, defineFrom, ATTR_TAG, ... }
 * WS helpers: document.setUpOrGetWebSocket, document.ux_domMessageHandler,
 * document.ux_domWaitForConnection.
 */

(function (global) {
  "use strict";

  /** Sole definition attribute — matches Python XElement.__x_element_checks */
  var ATTR_TAG = "x-tagname";

  function guid() {
    function s4() {
      return (((1 + Math.random()) * 0x10000) | 0).toString(16).substring(1);
    }
    return s4() + s4() + "-" + s4() + "-" + s4() + "-" + s4() + "-" + s4() + s4() + s4();
  }

  function isJSON(str) {
    if (typeof str !== "string" || !str) return false;
    try {
      JSON.parse(str);
      return true;
    } catch (e) {
      return false;
    }
  }

  function tagNameFrom(el) {
    return el.getAttribute(ATTR_TAG);
  }

  function customTagName(base) {
    return "x-" + String(base).toLowerCase();
  }

  function observeAttrChange(el, cb) {
    var observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        if (mutation.type === "attributes") {
          var oldVal = mutation.oldValue;
          var newVal = mutation.target.getAttribute(mutation.attributeName);
          cb(mutation.attributeName, oldVal, newVal);
        }
      });
    });
    observer.observe(el, {
      attributes: true,
      attributeOldValue: true,
      attributeFilter: ["id", "class", "style"],
    });
    return observer;
  }

  /* ── shared WebSocket pool ───────────────────────────────────────── */
  var sockets = {};
  var messageHandlers = {};
  var connectionResolvers = {};
  var waitForConnection = {};

  function setUpOrGetWebSocket(elementID, handlers, endPoint) {
    endPoint = endPoint || "/ws";
    if (!sockets[endPoint]) {
      var url = new URL(document.location.href);
      var wsUrl =
        url.protocol.replace("http", "ws") +
        "//" +
        url.host +
        endPoint;
      sockets[endPoint] = new WebSocket(wsUrl);
      connectionResolvers[endPoint] = connectionResolvers[endPoint] || [];
      waitForConnection[endPoint] = function () {
        return new Promise(function (resolve, reject) {
          if (sockets[endPoint] && sockets[endPoint].readyState === WebSocket.OPEN) {
            resolve();
            return;
          }
          connectionResolvers[endPoint].push({ resolve: resolve, reject: reject });
        });
      };
      sockets[endPoint].addEventListener("open", function () {
        (connectionResolvers[endPoint] || []).forEach(function (r) {
          r.resolve();
        });
        connectionResolvers[endPoint] = [];
      });
      sockets[endPoint].onclose = function () {
        sockets[endPoint] = null;
      };
      sockets[endPoint].onerror = function () {
        /* leave connection resolvers to time out / retry at send-time */
      };
    }
    sockets[endPoint].onmessage = function (message) {
      var data = message.data;
      if (isJSON(data)) data = JSON.parse(data);
      var h = handlers[elementID];
      if (typeof h === "function") h(data);
    };
    return sockets[endPoint];
  }

  document.setUpOrGetWebSocket = setUpOrGetWebSocket;
  document.ux_domMessageHandler = messageHandlers;
  document.ux_domWaitForConnection = waitForConnection;

  /* ── Custom Element factory (pairs with Python XElement) ─────────── */
  function createXElementClass(definitionEl) {
    var base = tagNameFrom(definitionEl);
    var TagName = customTagName(base);

    function XElementHost() {
      return Reflect.construct(HTMLElement, [], this.constructor);
    }
    XElementHost.prototype = Object.create(HTMLElement.prototype);
    XElementHost.prototype.constructor = XElementHost;

    XElementHost.prototype.connectedCallback = function () {
      var self = this;
      var isShadow =
        definitionEl.getAttribute("shadowroot") ||
        definitionEl.getAttribute("shadowdom");
      var template =
        definitionEl.tagName === "TEMPLATE"
          ? definitionEl
          : definitionEl.getElementsByTagName("template")[0];

      function mountInto(root, source) {
        var dataEl = source.querySelector
          ? source.querySelector("[x-data]")
          : null;
        if (!dataEl && source.content) {
          dataEl = source.content.querySelector("[x-data]");
        }
        self._includeDataInXData(dataEl);
        if (source.content) {
          root.appendChild(source.content.cloneNode(true));
        } else {
          root.appendChild(source.cloneNode(true));
        }
      }

      if (isShadow) {
        var mode =
          String(isShadow).toLowerCase() === "closed" ? "closed" : "open";
        var shadow = this.attachShadow({ mode: mode });
        if (template && template.content && template.content.childElementCount) {
          mountInto(shadow, template);
        } else {
          shadow.appendChild(document.createElement("slot"));
        }
        this.shadow = shadow;
        this._checkOrCreateId();
        this._initAlpine(this.shadow);
      } else {
        if (template) {
          mountInto(this, template);
        } else {
          this.appendChild(definitionEl.cloneNode(true));
        }
        this._checkOrCreateId();
        this._initAlpine(this);
      }

      this.dataCallback = this.dataCallback.bind(this);
      this._dataState = this.stateData();

      this._dataState.forEach(function (value, attr) {
        if (Object.prototype.hasOwnProperty.call(self, attr)) {
          throw new Error(
            "attribute " + attr + " conflicts with HTMLElement property"
          );
        }
        Object.defineProperty(self, "_data_" + attr, {
          get: function () {
            return self.hasAttribute(attr) ? self.getAttribute(attr) : undefined;
          },
          set: function (v) {
            self.setAttribute(attr, isJSON(v) ? JSON.parse(v) : v);
          },
        });
      });

      if (this._dataState.get("ws")) {
        messageHandlers[this.id] = this.dataCallback;
        this.ws = setUpOrGetWebSocket(
          this.id,
          messageHandlers,
          this._dataState.get("ws")
        );
        this.waitForConnection =
          waitForConnection[this._dataState.get("ws")];
      }

      this.observer = observeAttrChange(this, function (attr, o, n) {
        var key = attr.replace("_data_", "");
        if (self._dataState.get(key)) {
          self.attributeChangedCallback(key, o, n);
        }
      });

      if (this.getAttribute("ws_send")) {
        this.send(JSON.stringify(this._dataState.get("ws_send")));
      }
    };

    XElementHost.prototype._initAlpine = function (root) {
      if (typeof Alpine === "undefined") return;
      var run = function () {
        try {
          Alpine.initTree(root);
        } catch (e) {
          /* Alpine may not expose initTree in all builds */
        }
      };
      if (global.Alpine && Alpine.version) {
        document.addEventListener("alpine:initialized", run, { once: true });
        // also try immediately for late-mounted nodes
        queueMicrotask(run);
      } else {
        document.addEventListener("alpine:initialized", run, { once: true });
      }
    };

    XElementHost.prototype._includeDataInXData = function (dataEl) {
      if (!dataEl) return;
      var orig = dataEl.getAttribute("x-data");
      var hostData = this.data();
      if (orig && isJSON(orig)) {
        var parsed = JSON.parse(orig);
        dataEl.setAttribute(
          "x-data",
          JSON.stringify(Object.assign({}, parsed, hostData))
        );
      } else if (!orig) {
        dataEl.setAttribute("x-data", JSON.stringify(hostData));
      }
    };

    XElementHost.prototype._checkOrCreateId = function () {
      if (!this.id) this.id = TagName + "-" + guid();
    };

    XElementHost.prototype.dataCallback = function (message) {
      if (isJSON(message)) message = JSON.parse(message);
      if (typeof message === "string") {
        return;
      }
      if (this.id === message.id) {
        this.attributeChangedCallback(message.attr, message.oldVal, message.newVal);
      }
      if (this.ws) this.send(JSON.stringify(message));
    };

    XElementHost.prototype.attributeChangedCallback = function (attrName, o, n) {
      if (n !== o) {
        try {
          this[attrName] = n;
        } catch (e) {
          /* ignore non-writable */
        }
      }
    };

    XElementHost.prototype.disconnectedCallback = function () {
      if (this.observer) {
        this.observer.disconnect();
        this.observer = null;
      }
      if (this.ws) {
        try {
          this.ws.close();
        } catch (e) {}
        this.ws = null;
      }
    };

    XElementHost.prototype.send = function (data, retries) {
      retries = retries === undefined ? 4 : retries;
      if (!this.ws) return;
      try {
        this.ws.send(data);
        return data;
      } catch (error) {
        if (retries > 0 && error.name === "InvalidStateError" && this.waitForConnection) {
          var self = this;
          return this.waitForConnection().then(function () {
            return self.send(data, retries - 1);
          });
        }
        throw error;
      }
    };

    XElementHost.prototype.dispatch = function (name, data, options) {
      options = options || { bubble: true, cancelable: false, composed: false };
      this.dispatchEvent(
        new CustomEvent(name, {
          bubbles: options.bubble,
          cancelable: options.cancelable,
          composed: options.composed,
          detail: data,
        })
      );
    };

    XElementHost.prototype.data = function () {
      var filterAttr = ["@", "x-", "id", "class", ":"];
      var entries = Array.from(this.stateData().entries()).filter(function (pair) {
        var attr = pair[0];
        return !filterAttr.some(function (letter) {
          return attr.startsWith(letter);
        });
      });
      return Object.fromEntries(entries);
    };

    XElementHost.prototype.stateData = function () {
      var data = new Map();
      Array.from(this.getAttributeNames()).forEach(function (attribute) {
        var raw = this.getAttribute(attribute);
        data.set(attribute, isJSON(raw) ? JSON.parse(raw) : raw);
      }, this);
      return data;
    };

    return XElementHost;
  }

  function defineFrom(node) {
    var base = tagNameFrom(node);
    if (!base) return;
    var name = customTagName(base);
    if (!customElements.get(name)) {
      customElements.define(name, createXElementClass(node));
    }
  }

  function scan(root) {
    root = root || document;
    if (!root.querySelectorAll) return;
    root.querySelectorAll("[" + ATTR_TAG + "]").forEach(defineFrom);
  }

  function boot() {
    scan(document);
    document.addEventListener("htmx:afterSwap", function (ev) {
      if (ev && ev.target) scan(ev.target);
    });
    if (document.body) {
      new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
          if (mutation.type !== "childList") return;
          mutation.addedNodes.forEach(function (node) {
            if (node.nodeType !== 1) return;
            if (node.nodeName && String(node.nodeName).indexOf("X-") === 0) {
              scan(document);
            }
            if (node.querySelectorAll) scan(node);
          });
        });
      }).observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  // Public API
  global.UxDom = global.UxDom || {};
  /** Mirror of Python ux_dom.dom.XElement */
  global.UxDom.XElement = {
    scan: scan,
    defineFrom: defineFrom,
    tagNameFrom: tagNameFrom,
    customTagName: customTagName,
    ATTR_TAG: ATTR_TAG,  // "x-tagname"
  };
})(typeof window !== "undefined" ? window : globalThis);
