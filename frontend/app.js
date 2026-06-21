/**
 * app.js — Krid AI Dashboard
 * Vanilla JS: fetches API data, renders tenant tabs, session list, chat thread.
 * Includes a chat simulator for testing without WhatsApp.
 * Polls every 4 seconds to keep the view fresh.
 */

const API = '';   // Empty = same origin (FastAPI serves this file)

// ── State ─────────────────────────────────────────────────────────────────────
let state = {
  tenants: [],
  activeTenantId: null,
  sessions: [],
  activeSessionId: null,
  activeSession: null,
  messages: [],
  pollTimer: null,
};

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $tenantTabs     = document.getElementById('tenant-tabs');
const $sessionList    = document.getElementById('session-list');
const $sessionCount   = document.getElementById('session-count');
const $chatEmpty      = document.getElementById('chat-empty');
const $chatHeader     = document.getElementById('chat-header');
const $chatPhone      = document.getElementById('chat-phone');
const $chatStatusBadge= document.getElementById('chat-status-badge');
const $chatTenantName = document.getElementById('chat-tenant-name');
const $chatThread     = document.getElementById('chat-thread');
const $typingIndicator= document.getElementById('typing-indicator');
const $chatInputBar   = document.getElementById('chat-input-bar');
const $chatInput      = document.getElementById('chat-input');
const $chatSendBtn    = document.getElementById('chat-send-btn');

// Broadcast
const $broadcastDrawer = document.getElementById('broadcast-drawer');
const $drawerOverlay   = document.getElementById('drawer-overlay');
const $btnOpenBroadcast  = document.getElementById('btn-open-broadcast');
const $btnCloseBroadcast = document.getElementById('btn-close-broadcast');
const $btnSendBroadcast  = document.getElementById('btn-send-broadcast');
const $broadcastResults  = document.getElementById('broadcast-results');

// Simulator
const $simulatorDrawer   = document.getElementById('simulator-drawer');
const $simDrawerOverlay  = document.getElementById('sim-drawer-overlay');
const $btnOpenSimulator  = document.getElementById('btn-open-simulator');
const $btnCloseSimulator = document.getElementById('btn-close-simulator');
const $btnSendSim        = document.getElementById('btn-send-sim');
const $simResults        = document.getElementById('sim-results');

// ── API helpers ───────────────────────────────────────────────────────────────

async function apiFetch(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API POST ${path} → ${res.status}`);
  return res.json();
}

// ── Initialise ────────────────────────────────────────────────────────────────

async function init() {
  try {
    const data = await apiFetch('/api/tenants');
    state.tenants = data.tenants || [];
    renderTenantTabs();
    if (state.tenants.length > 0) {
      selectTenant(state.tenants[0].tenant_id);
    }
  } catch (err) {
    console.error('Init failed:', err);
    setConnectionStatus(false);
  }
}

// ── Tenant tabs ───────────────────────────────────────────────────────────────

function renderTenantTabs() {
  $tenantTabs.innerHTML = '';
  state.tenants.forEach(tenant => {
    const btn = document.createElement('button');
    btn.className = 'tenant-tab';
    btn.textContent = tenant.name;
    btn.dataset.tenantId = tenant.tenant_id;
    btn.setAttribute('aria-pressed', 'false');
    btn.addEventListener('click', () => selectTenant(tenant.tenant_id));
    $tenantTabs.appendChild(btn);
  });
}

function selectTenant(tenantId) {
  state.activeTenantId = tenantId;
  state.activeSessionId = null;
  state.activeSession = null;

  // Update tab styles
  $tenantTabs.querySelectorAll('.tenant-tab').forEach(btn => {
    const isActive = btn.dataset.tenantId === tenantId;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
  });

  // Reset chat panel
  showChatEmpty();

  // Load sessions for this tenant
  loadSessions(tenantId);

  // Start polling
  clearInterval(state.pollTimer);
  state.pollTimer = setInterval(() => pollUpdates(), 4000);
}

// ── Session list ──────────────────────────────────────────────────────────────

async function loadSessions(tenantId) {
  try {
    const data = await apiFetch(`/api/tenants/${tenantId}/sessions`);
    state.sessions = data.sessions || [];
    renderSessionList();
    setConnectionStatus(true);
  } catch (err) {
    console.error('Load sessions failed:', err);
    setConnectionStatus(false);
  }
}

function renderSessionList() {
  $sessionList.innerHTML = '';
  $sessionCount.textContent = state.sessions.length;

  if (state.sessions.length === 0) {
    const li = document.createElement('li');
    li.style.cssText = 'padding:20px;text-align:center;color:var(--clr-muted);font-size:13px;';
    li.textContent = 'No active conversations yet.';
    $sessionList.appendChild(li);
    return;
  }

  state.sessions.forEach(session => {
    const li = document.createElement('li');
    li.className = 'session-item';
    if (session.session_id === state.activeSessionId) li.classList.add('active');
    li.setAttribute('role', 'button');
    li.setAttribute('tabindex', '0');
    li.dataset.sessionId = session.session_id;

    const statusLabel = statusText(session.status);
    const statusCls = statusClass_(session.status);
    const time = session.updated_at ? formatTime(session.updated_at) : '';

    li.innerHTML = `
      <div class="session-avatar">👤</div>
      <div class="session-info">
        <div class="session-phone">${escapeHtml(session.customer_phone)}</div>
        <div class="session-meta">
          <span class="status-badge ${statusCls}">${statusLabel}</span>
          <span>${time}</span>
        </div>
      </div>
    `;

    li.addEventListener('click', () => selectSession(session));
    li.addEventListener('keydown', e => { if (e.key === 'Enter') selectSession(session); });
    $sessionList.appendChild(li);
  });
}

function selectSession(session) {
  state.activeSessionId = session.session_id;
  state.activeSession = session;

  // Highlight selected item
  $sessionList.querySelectorAll('.session-item').forEach(el => {
    el.classList.toggle('active', el.dataset.sessionId === session.session_id);
  });

  // Show chat panel header + input bar
  showChatPanel(session);
  loadMessages(session.session_id, session.status);
}

// ── Chat thread ───────────────────────────────────────────────────────────────

async function loadMessages(sessionId, sessionStatus) {
  try {
    const data = await apiFetch(`/api/sessions/${sessionId}/messages`);
    state.messages = data.messages || [];
    renderChatThread();

    // Show/hide typing indicator
    const isTyping = sessionStatus === 'AGENT_RESPONDING';
    $typingIndicator.hidden = !isTyping;

    // Scroll to bottom
    $chatThread.scrollTop = $chatThread.scrollHeight;
  } catch (err) {
    console.error('Load messages failed:', err);
  }
}

function renderChatThread() {
  $chatThread.innerHTML = '';

  if (state.messages.length === 0) {
    const div = document.createElement('div');
    div.style.cssText = 'text-align:center;color:var(--clr-muted);font-size:13px;padding:20px;';
    div.textContent = 'No messages yet. Send one using the input below or the Chat Simulator.';
    $chatThread.appendChild(div);
    return;
  }

  state.messages.forEach(msg => {
    const row = document.createElement('div');
    const isInbound = msg.direction === 'inbound';
    row.className = `msg-row msg-row--${isInbound ? 'inbound' : 'outbound'}`;

    const bubble = document.createElement('div');
    bubble.className = `msg-bubble msg-bubble--${isInbound ? 'inbound' : 'outbound'}`;

    // ── Media attachments ──
    if (msg.media_url) {
      const mime = msg.mime_type || '';
      if (mime.startsWith('image/')) {
        const img = document.createElement('img');
        img.src = msg.media_url;
        img.alt = 'Attached image';
        img.className = 'msg-image';
        img.loading = 'lazy';
        bubble.appendChild(img);
      } else if (mime === 'application/pdf' || msg.media_url.endsWith('.pdf')) {
        const link = document.createElement('a');
        link.href = msg.media_url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.className = 'msg-pdf-badge';
        link.innerHTML = '<span class="msg-pdf-badge__icon">📄</span> Download PDF';
        bubble.appendChild(link);
      }
    }

    // ── Text ──
    if (msg.text) {
      const p = document.createElement('p');
      p.textContent = msg.text;
      bubble.appendChild(p);
    }

    // ── Timestamp ──
    if (msg.timestamp) {
      const time = document.createElement('span');
      time.className = 'msg-time';
      time.textContent = formatTime(msg.timestamp);
      // Add typing indicator mark if bot was typing before this msg
      if (!isInbound && msg.bot_was_typing) {
        time.textContent = '⌨️ ' + time.textContent;
      }
      bubble.appendChild(time);
    }

    row.appendChild(bubble);
    $chatThread.appendChild(row);
  });
}

// ── Inline chat input (send as the selected customer) ────────────────────────

$chatSendBtn.addEventListener('click', sendInlineChatMessage);
$chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendInlineChatMessage();
  }
});

async function sendInlineChatMessage() {
  const text = $chatInput.value.trim();
  if (!text || !state.activeSession) return;

  $chatInput.value = '';
  $chatSendBtn.disabled = true;

  try {
    await apiPost('/api/simulate', {
      tenant_id: state.activeSession.tenant_id,
      customer_phone: state.activeSession.customer_phone,
      message: text,
    });
    // The agent runs async — poll will pick up the reply in a few seconds
    // Force an immediate poll
    setTimeout(() => pollUpdates(), 500);
    setTimeout(() => pollUpdates(), 2000);
    setTimeout(() => pollUpdates(), 5000);
  } catch (err) {
    console.error('Inline send failed:', err);
    alert('Failed to send message: ' + err.message);
  } finally {
    $chatSendBtn.disabled = false;
    $chatInput.focus();
  }
}

// ── Poll for live updates ──────────────────────────────────────────────────────

async function pollUpdates() {
  if (!state.activeTenantId) return;
  await loadSessions(state.activeTenantId);

  // If a session is open, refresh its messages too
  if (state.activeSessionId) {
    const session = state.sessions.find(s => s.session_id === state.activeSessionId);
    if (session) {
      state.activeSession = session;
      await loadMessages(state.activeSessionId, session.status);
      // Update the header status badge too
      $chatStatusBadge.textContent = statusText(session.status);
      $chatStatusBadge.className = `chat-header__status-badge status-badge ${statusClass_(session.status)}`;
    }
  }
}

// ── Simulator drawer ───────────────────────────────────────────────────────────

$btnOpenSimulator.addEventListener('click', () => {
  $simulatorDrawer.hidden = false;
  $simDrawerOverlay.hidden = false;
  requestAnimationFrame(() => $simulatorDrawer.classList.add('open'));
});

$btnCloseSimulator.addEventListener('click', closeSimDrawer);
$simDrawerOverlay.addEventListener('click', closeSimDrawer);

function closeSimDrawer() {
  $simulatorDrawer.classList.remove('open');
  $simulatorDrawer.addEventListener('transitionend', () => {
    $simulatorDrawer.hidden = true;
    $simDrawerOverlay.hidden = true;
  }, { once: true });
}

// Preset buttons
document.querySelectorAll('.sim-preset-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.getElementById('sim-message').value = btn.dataset.msg;
  });
});

$btnSendSim.addEventListener('click', async () => {
  const phone   = document.getElementById('sim-phone').value.trim();
  const message  = document.getElementById('sim-message').value.trim();

  if (!phone || !message) {
    alert('Please fill in both phone number and message.');
    return;
  }

  if (!state.activeTenantId) {
    alert('Please select a tenant first.');
    return;
  }

  $btnSendSim.disabled = true;
  $btnSendSim.textContent = 'Sending…';
  $simResults.innerHTML = '';

  try {
    const data = await apiPost('/api/simulate', {
      tenant_id: state.activeTenantId,
      customer_phone: phone,
      message,
    });

    $simResults.innerHTML = `
      <div class="broadcast-result--ok">
        ✓ Message sent via WhatsApp<br>
        <small>ID: ${escapeHtml(data.message_id)}</small><br>
        <small>The bot will reply to the phone number in a few seconds.</small>
      </div>
    `;

    // Trigger a few polls to pick up the response quickly
    setTimeout(() => pollUpdates(), 1000);
    setTimeout(() => pollUpdates(), 3000);
    setTimeout(() => pollUpdates(), 6000);

  } catch (err) {
    $simResults.innerHTML = `<div class="broadcast-result--err">✗ Error: ${escapeHtml(err.message)}</div>`;
  } finally {
    $btnSendSim.disabled = false;
    $btnSendSim.textContent = 'Send to WhatsApp';
  }
});


// ── Broadcast drawer ───────────────────────────────────────────────────────────

$btnOpenBroadcast.addEventListener('click', () => {
  $broadcastDrawer.hidden = false;
  $drawerOverlay.hidden = false;
  requestAnimationFrame(() => $broadcastDrawer.classList.add('open'));
});

$btnCloseBroadcast.addEventListener('click', closeBroadcastDrawer);
$drawerOverlay.addEventListener('click', closeBroadcastDrawer);

function closeBroadcastDrawer() {
  $broadcastDrawer.classList.remove('open');
  $broadcastDrawer.addEventListener('transitionend', () => {
    $broadcastDrawer.hidden = true;
    $drawerOverlay.hidden = true;
  }, { once: true });
}

$btnSendBroadcast.addEventListener('click', async () => {
  const numbersRaw = document.getElementById('broadcast-numbers').value.trim();
  const message    = document.getElementById('broadcast-message').value.trim();

  if (!numbersRaw || !message) {
    alert('Please fill in both phone numbers and message.');
    return;
  }

  const phoneNumbers = numbersRaw.split('\n').map(n => n.trim()).filter(Boolean);

  $btnSendBroadcast.disabled = true;
  $btnSendBroadcast.textContent = 'Sending…';
  $broadcastResults.innerHTML = '';

  try {
    const data = await apiPost('/api/broadcast', {
      tenant_id: state.activeTenantId,
      phone_numbers: phoneNumbers,
      message,
    });

    (data.broadcast_results || []).forEach(r => {
      const div = document.createElement('div');
      div.className = r.status === 'sent' ? 'broadcast-result--ok' : 'broadcast-result--err';
      div.textContent = r.status === 'sent'
        ? `✓ ${r.phone} — sent`
        : `✗ ${r.phone} — ${r.error}`;
      $broadcastResults.appendChild(div);
    });
  } catch (err) {
    $broadcastResults.innerHTML = `<div class="broadcast-result--err">Error: ${escapeHtml(err.message)}</div>`;
  } finally {
    $btnSendBroadcast.disabled = false;
    $btnSendBroadcast.textContent = 'Send Broadcast';
  }
});

// ── UI helpers ─────────────────────────────────────────────────────────────────

function showChatEmpty() {
  $chatEmpty.style.display = '';
  $chatHeader.hidden = true;
  $chatThread.innerHTML = '';
  $typingIndicator.hidden = true;
  $chatInputBar.hidden = true;
}

function showChatPanel(session) {
  $chatEmpty.style.display = 'none';
  $chatHeader.hidden = false;
  $chatInputBar.hidden = false;
  $chatPhone.textContent = session.customer_phone;
  $chatStatusBadge.textContent = statusText(session.status);
  $chatStatusBadge.className = `chat-header__status-badge status-badge ${statusClass_(session.status)}`;
  const tenant = state.tenants.find(t => t.tenant_id === session.tenant_id);
  $chatTenantName.textContent = tenant ? tenant.name : session.tenant_id;
  $chatInput.focus();
}

function setConnectionStatus(ok) {
  const dot = document.querySelector('.status-dot');
  const label = document.querySelector('.topbar__status');
  dot.className = `status-dot ${ok ? 'status-dot--ok' : 'status-dot--error'}`;
  label.childNodes[1].nodeValue = ok ? ' Live' : ' Disconnected';
}

function statusText(status) {
  return {
    WAITING_FOR_BOT:  'Waiting',
    AGENT_RESPONDING: 'Typing…',
    RESOLVED:         'Resolved',
    NEEDS_HUMAN:      'Needs Human',
  }[status] || status;
}

function statusClass_(status) {
  return {
    WAITING_FOR_BOT:  'status-badge--waiting',
    AGENT_RESPONDING: 'status-badge--responding',
    RESOLVED:         'status-badge--resolved',
    NEEDS_HUMAN:      'status-badge--human',
  }[status] || '';
}

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
init();
