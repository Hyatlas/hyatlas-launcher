// static/js/main.js
// Hyatlas Launcher – global front-end helpers
// ------------------------------------------
// Loaded once in base.html and available to all pages.

(() => {
  // Simple namespace to avoid polluting window
  const hyatlas = {
    /** JWT token kept only in memory (cleared on refresh). */
    token: null,

    /**
     * Store access_token after successful login.
     * @param {string} tok
     */
    setToken(tok) {
      this.token = tok;
    },

    /** Clear token and redirect to /login. */
    logout() {
      this.token = null;
      window.location.href = "/login";
    },

    /**
     * Wrapper around fetch() that auto-adds Authorization header
     * when a token is present and handles JSON error bodies.
     * @returns {Promise<Response>}
     */
    async apiFetch(url, opts = {}) {
      const headers = Object.assign(
        { "Content-Type": "application/json" },
        opts.headers || {}
      );
      if (this.token) headers.Authorization = `Bearer ${this.token}`;
      const res = await fetch(url, Object.assign({}, opts, { headers }));

      // If backend returns JSON error, bubble up message
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const j = await res.clone().json();
          detail = j.detail || detail;
        } catch (_) {}
        throw new Error(detail);
      }
      return res;
    },

    /**
     * Very small toast / message helper.
     * @param {string} text
     * @param {"error"|"info"} [type="info"]
     */
    toast(text, type = "info") {
      const div = document.createElement("div");
      div.className = `toast ${type}`;
      div.textContent = text;
      document.body.appendChild(div);
      setTimeout(() => div.remove(), 3000);
    }
  };

  // Expose globally
  window.hyatlas = hyatlas;
})();



