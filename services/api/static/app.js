async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    method: opts.method || "GET",
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json().catch(() => ({})) : {};
  return { ok: res.ok, status: res.status, data };
}

async function refreshNavbarUser() {
  const el = document.getElementById("nav-user");
  if (!el) return;
  try {
    const { ok, data } = await fetchJSON("/auth/me");
    if (ok && data && data.email && data.id && data.id !== "public") {
      el.textContent = data.email;
      // add a logout form
      const f = document.createElement("form");
      f.method = "post";
      f.action = "/ui/logout";
      f.style.display = "inline";
      const btn = document.createElement("button");
      btn.type = "submit";
      btn.textContent = "Logout";
      btn.style.marginLeft = "0.5rem";
      f.appendChild(btn);
      el.after(f);
    } else {
      el.innerHTML = '<a href="/ui/login">Login</a>';
    }
  } catch (_) {
    // ignore
  }
}

async function setupAuthForms() {
  const login = document.getElementById("login-form");
  if (login) {
    login.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(login);
      const email = fd.get("email");
      const password = fd.get("password");
      const { ok, data, status } = await fetchJSON("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      const msg = document.getElementById("login-msg");
      if (ok) {
        // server sets cookie; keep token in localStorage for API calls if needed
        if (data && data.access_token) {
          localStorage.setItem("access_token", data.access_token);
        }
        msg.textContent = "Logged in!";
        window.location.href = "/ui/plans";
      } else {
        msg.textContent = data?.detail || `Login failed (${status})`;
      }
    });
  }

  const reg = document.getElementById("register-form");
  if (reg) {
    reg.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(reg);
      const email = fd.get("email");
      const password = fd.get("password");
      const { ok, data, status } = await fetchJSON("/auth/register", {
        method: "POST",
        body: { email, password },
      });
      const msg = document.getElementById("register-msg");
      if (ok) {
        msg.textContent = "Account created. Redirecting…";
	    window.location.assign("/ui/login");
      } else {
        msg.textContent = data?.detail || `Register failed (${status})`;
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  refreshNavbarUser();
  setupAuthForms();
});
