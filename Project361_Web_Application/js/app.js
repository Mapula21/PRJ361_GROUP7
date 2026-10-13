import { auth } from "./firebase-config.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.18.0/firebase-auth.js";
import { getAnalytics, getAlerts, getHistory, getAthlete, sendChatMessage } from "./api.js";

const pages = document.querySelectorAll(".page");
const nav = document.querySelectorAll(".nav-item[data-page]");
const title = document.getElementById("pageTitle");

let readings = [];
let apiHistory = [];
let apiAlerts = [];
let apiAthlete = null;
let lastAnalytics = null;

const LIVE_COLOR = "#75b798";
const OFFLINE_COLOR = "#b0b8bf";

function showPage(name){
  pages.forEach(p=>p.classList.toggle("active-page",p.id===name));
  nav.forEach(n=>n.classList.toggle("active",n.dataset.page===name));
  const labels={dashboard:"Dashboard",history:"Session History",alerts:"Alerts",profile:"Profile"};
  title.textContent=labels[name]||"Dashboard";
  window.scrollTo({top:0,behavior:"smooth"});
}

nav.forEach(n=>n.addEventListener("click",()=>showPage(n.dataset.page)));
document.querySelectorAll("[data-page-link]").forEach(b=>b.addEventListener("click",()=>showPage(b.dataset.pageLink)));

/* ---------- small helpers ---------- */

function escapeHtml(value){
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[ch]));
}

function setText(id, value){
  const el = document.getElementById(id);
  if(el) el.textContent = value;
}

function formatClock(value){
  const d = new Date(value);
  if(Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
}

function formatDuration(seconds){
  if(seconds == null) return "—";
  if(seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if(minutes < 60) return rest ? `${minutes} min ${rest} s` : `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours} h ${minutes % 60} min`;
}

function formatAgo(seconds){
  if(seconds == null) return "unknown";
  if(seconds < 5) return "just now";
  if(seconds < 60) return `${seconds} s ago`;
  if(seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if(seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return `${Math.floor(seconds / 86400)} d ago`;
}

function formatAlertTime(timestamp){
  if(!timestamp) return "Time unavailable";
  const d = new Date(timestamp);
  if(Number.isNaN(d.getTime())) return timestamp;
  return d.toLocaleString([], {dateStyle:"medium", timeStyle:"short"});
}

/* A reading counts as live when the backend says so (or, for an older backend,
   when the newest reading is under 15 seconds old). */
function isLive(data){
  if(!data) return false;
  if(typeof data.is_live === "boolean") return data.is_live;
  const list = data.recent_readings;
  if(!Array.isArray(list) || !list.length) return false;
  const t = new Date(list[list.length - 1].timestamp).getTime();
  return Number.isFinite(t) && (Date.now() - t) < 15000;
}

/* ---------- connection / live status ---------- */

function setStatus(backendOk, live){
  let label, color, system;
  if(!backendOk){
    label = "BACKEND OFFLINE"; color = OFFLINE_COLOR; system = "Backend unreachable";
  }else if(live){
    label = "LIVE"; color = LIVE_COLOR; system = "Device streaming";
  }else{
    label = "WAITING FOR DEVICE"; color = OFFLINE_COLOR; system = "Waiting for device";
  }

  const badge = document.getElementById("liveBadge");
  if(badge) badge.innerHTML = `<span style="background:${color}"></span> ${label}`;

  const dot = document.querySelector(".status-dot");
  if(dot) dot.style.background = color;

  setText("systemStatus", system);
}

/* ---------- chart ---------- */

function drawChart(){
  const canvas=document.getElementById("hrChart");
  if(!canvas)return;
  const dpr=window.devicePixelRatio||1;
  const rect=canvas.getBoundingClientRect();
  canvas.width=rect.width*dpr;
  canvas.height=210*dpr;
  const ctx=canvas.getContext("2d");
  ctx.scale(dpr,dpr);

  const w=rect.width,h=210,p=14;

  ctx.clearRect(0,0,w,h);
  ctx.strokeStyle="#e5e9ec";
  ctx.lineWidth=1;

  for(let i=0;i<4;i++){
    const y=p+i*(h-2*p)/3;
    ctx.beginPath();
    ctx.moveTo(0,y);
    ctx.lineTo(w,y);
    ctx.stroke();
  }

  if(readings.length < 2){
    ctx.fillStyle="#89939b";
    ctx.font="12px Inter, Segoe UI, Arial, sans-serif";
    ctx.textAlign="center";
    ctx.fillText("Waiting for live readings…", w/2, h/2);
    return;
  }

  const min=Math.max(40, Math.min(...readings, 70)-10);
  const max=Math.max(...readings, 100)+10;

  ctx.strokeStyle="#17202a";
  ctx.lineWidth=2;
  ctx.beginPath();

  readings.forEach((v,i)=>{
    const x=i*(w/(Math.max(readings.length-1,1)));
    const y=h-p-((v-min)/(max-min))*(h-2*p);
    i ? ctx.lineTo(x,y) : ctx.moveTo(x,y);
  });

  ctx.stroke();
}

/* Time labels under the chart come from the readings that are plotted. */
function updateChartLabels(recent, live){
  const box = document.getElementById("chartLabels");
  if(!box) return;
  const spans = box.querySelectorAll("span");
  if(!spans.length) return;

  if(!Array.isArray(recent) || recent.length < 2){
    spans.forEach(span => { span.textContent = "—"; });
    return;
  }

  spans.forEach((span, i) => {
    const index = Math.round(i * (recent.length - 1) / Math.max(spans.length - 1, 1));
    const isLast = i === spans.length - 1;
    span.textContent = isLast && live ? "Now" : formatClock(recent[index].timestamp);
  });
}

/* ---------- alerts ---------- */

function severityClass(severity){
  const value = String(severity || "").toLowerCase();
  if(value.includes("high") || value.includes("critical")) return "warning";
  if(value.includes("medium") || value.includes("pending")) return "warning";
  return "info";
}

function renderAlerts(){
  const preview = document.getElementById("alertPreview");
  if(!preview) return;

  if(!apiAlerts.length){
    preview.innerHTML = '<div class="alert-preview"><div class="alert-icon info">i</div><div><strong>No recent alerts</strong><div style="font-size:11px;color:#89939b;margin-top:3px">The system has not reported any recent anomalies.</div></div></div>';
  } else {
    preview.innerHTML = apiAlerts.slice(0,3).map(a => `
      <div class="alert-preview">
        <div class="alert-icon ${severityClass(a.severity)}">${severityClass(a.severity)==="warning" ? "!" : "i"}</div>
        <div>
          <strong>${escapeHtml(a.message || "Heart-rate alert")}</strong>
          <div style="font-size:11px;color:#89939b;margin-top:3px">
            ${formatAlertTime(a.timestamp)} · ${escapeHtml(a.severity || "Info")}
          </div>
        </div>
      </div>
    `).join("");
  }

  const alertsPanel = document.querySelector("#alerts .panel");
  if(alertsPanel){
    if(!apiAlerts.length){
      alertsPanel.innerHTML = '<div class="alert-item"><div class="alert-icon info">i</div><div><strong>No alerts</strong><p>No heart-rate anomalies have been returned by the backend.</p></div><span class="pill good">Normal</span></div>';
    } else {
      alertsPanel.innerHTML = apiAlerts.map(a => `
        <div class="alert-item">
          <div class="alert-icon ${severityClass(a.severity)}">${severityClass(a.severity)==="warning" ? "!" : "i"}</div>
          <div>
            <strong>${escapeHtml(a.message || "Heart-rate alert")}</strong>
            <p>${escapeHtml(a.explanation || a.classification || "Backend alert")}</p>
            <small>${formatAlertTime(a.timestamp)}</small>
          </div>
          <span class="pill ${severityClass(a.severity)==="warning" ? "watch" : "good"}">${escapeHtml(a.severity || "Info")}</span>
        </div>
      `).join("");
    }
  }

  renderRecommendation();
}

/* ---------- AI recommendation panel ---------- */

function renderRecommendation(){
  const main = document.getElementById("dashboardRecommendation");
  const extra = document.getElementById("dashboardReason");
  if(!main) return;

  const live = isLive(lastAnalytics);
  const ai = live ? lastAnalytics.ai : null;
  const latestAlert = apiAlerts.length && apiAlerts[0].message ? apiAlerts[0] : null;
  const lines = [];

  if(!lastAnalytics){
    main.textContent = "Connecting to the monitoring backend…";
  }else if(ai){
    main.textContent = ai.recommendation || "Continue monitoring heart rate and exercise intensity.";
    if(ai.reason) lines.push(`Why: ${ai.reason}`);
  }else if(live){
    main.textContent = "The AI analysis is unavailable for the latest reading.";
  }else{
    main.textContent = "No live signal. Place a finger on the sensor to start monitoring.";
  }

  if(latestAlert){
    lines.push(`Latest alert advice (${formatAlertTime(latestAlert.timestamp)}): ${latestAlert.message}`);
  }

  if(extra) extra.innerHTML = lines.map(escapeHtml).join("<br>");
}

/* ---------- user, profile ---------- */

function updateUserDetails(user){
  const name = user.displayName || user.email?.split("@")[0] || "Athlete";
  const email = user.email || "Email unavailable";

  const initials =
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(x => x[0].toUpperCase())
      .join("") || "A";

  const chip = document.querySelector(".athlete-chip");
  if(chip){
    chip.querySelector(".avatar").textContent = initials;
    chip.querySelector("strong").textContent = name;
    chip.querySelector("span").textContent = "Authenticated session";
  }

  const welcome = document.querySelector(".welcome h2");
  if(welcome){
    const hour = new Date().getHours();
    let greeting;
    if(hour < 12){
      greeting = "Good morning";
    } else if(hour < 18){
      greeting = "Good afternoon";
    } else {
      greeting = "Good evening";
    }
    welcome.textContent = `${greeting}, ${name}.`;
  }

  const profileAvatar = document.getElementById("profileAvatar");
  const profileName = document.getElementById("profileName");
  const profileEmail = document.getElementById("profileEmail");
  if(profileAvatar) profileAvatar.textContent = initials;
  if(profileName) profileName.textContent = name;
  if(profileEmail) profileEmail.textContent = email;
}

function renderProfile(){
  const a = apiAthlete?.athlete;
  setText("profileAge", a?.age != null ? a.age : "—");
  setText("profileRestingHr", a?.resting_hr != null ? `${a.resting_hr} BPM` : "—");
  setText("profileMaximumHr", a?.estimated_max_hr != null ? `${a.estimated_max_hr} BPM` : "—");

  const deviceName = apiAthlete?.device?.name || "PRJ361-ESP32";
  let device = "—";
  if(lastAnalytics){
    if(isLive(lastAnalytics)){
      device = `${deviceName} · streaming`;
    }else if(lastAnalytics.seconds_since_last_reading != null){
      device = `${deviceName} · last seen ${formatAgo(lastAnalytics.seconds_since_last_reading)}`;
    }else{
      device = `${deviceName} · no data yet`;
    }
  }
  setText("profileDevice", device);
}

/* ---------- live metrics ---------- */

const TREND_ARROWS = { rising: "▲", falling: "▼", steady: "▬" };

function updateAnalytics(data){
  if(!data) return;
  lastAnalytics = data;

  const live = isLive(data);
  setStatus(true, live);

  // Current BPM: only show a number while the device is really streaming
  const bpm = live ? (data.current_bpm ?? data.latest_bpm ?? null) : null;
  setText("bpm", bpm != null ? bpm : "—");
  setText("chartCurrentBpm", bpm != null ? `${bpm} BPM` : "—");

  // Zone: "Zone 2 - Light" -> big "Zone 2", small "Light"
  const zoneText = live ? (data.ai?.zone ?? data.current_zone) : null;
  if(zoneText != null && zoneText !== ""){
    const parts = String(zoneText).split(" - ");
    setText("zone", parts[0]);
    setText("zoneFoot", parts[1] ? `${parts[1]} · current training zone` : "Current training zone");
  }else{
    setText("zone", "—");
    setText("zoneFoot", live ? "Zone unavailable" : "Waiting for live reading");
  }

  // AI status: rule-based analyzer + ML anomaly model
  const ai = live ? data.ai : null;
  const aiEl = document.getElementById("aiStatus");
  if(aiEl){
    aiEl.textContent = ai ? `${ai.is_anomalous ? "⚠ " : ""}${ai.status}` : "—";
    aiEl.style.color = ai?.is_anomalous ? "#b3541e" : "";
  }
  if(ai){
    const score = Number(ai.anomaly_score);
    setText("aiStatusFoot", `ML check: ${ai.ml_status}${Number.isFinite(score) ? ` (score ${score.toFixed(2)})` : ""}`);
  }else{
    setText("aiStatusFoot", live ? "AI analysis unavailable" : "Waiting for live reading");
  }

  // Trend: recent average versus the average before it
  const trend = live ? data.trend : null;
  if(trend && TREND_ARROWS[trend.direction]){
    const label = trend.direction.charAt(0).toUpperCase() + trend.direction.slice(1);
    setText("trend", `${TREND_ARROWS[trend.direction]} ${label}`);
    const change = Number(trend.change_bpm);
    setText("trendFoot", Number.isFinite(change)
      ? `${change > 0 ? "+" : ""}${change} BPM vs the previous 6 readings`
      : "Compared with earlier readings");
  }else{
    setText("trend", "—");
    setText("trendFoot", live ? "Collecting readings…" : "Waiting for live reading");
  }

  // Session summary (current session while live, otherwise the last one recorded)
  const session = data.session;
  setText("sessionSubtitle", live ? "Current training session" : "Last recorded session");
  setText("averageBpm", session ? `${session.average_bpm} BPM` : (data.average_bpm != null ? `${data.average_bpm} BPM` : "—"));
  setText("peakBpm", session ? `${session.peak_bpm} BPM` : (data.peak_bpm != null ? `${data.peak_bpm} BPM` : "—"));
  setText("sessionDuration", session ? formatDuration(session.duration_seconds) : "—");
  setText("sessionReadings", session ? session.reading_count : "—");

  // Chart and its time labels
  const recent = Array.isArray(data.recent_readings) ? data.recent_readings.slice(-30) : [];
  readings = recent.map(r => Number(r.bpm)).filter(Number.isFinite);
  updateChartLabels(recent, live);
  drawChart();

  renderRecommendation();
  renderProfile();
}

/* ---------- history ---------- */

function formatHistoryDate(value){
  if(!value) return "—";
  const d = new Date(`${value}T00:00:00`);
  if(Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString([], {day:"2-digit", month:"short", year:"numeric"});
}

function renderHistory(){
  const body = document.getElementById("historyTableBody");
  if(!body) return;

  if(!apiHistory.length){
    body.innerHTML = '<tr><td colspan="7">No session history is available yet.</td></tr>';
    return;
  }

  body.innerHTML = apiHistory.map(session => {
    const status = String(session.status || "Normal");
    const isAlert = status.toLowerCase() === "alert";
    const duration = session.duration_minutes == null ? "—" : `${session.duration_minutes} min`;
    return `
      <tr>
        <td>${escapeHtml(formatHistoryDate(session.date))}</td>
        <td>${escapeHtml(session.session || "Monitoring")}</td>
        <td>${escapeHtml(session.reading_count ?? "—")}</td>
        <td>${session.average_bpm != null ? `${escapeHtml(session.average_bpm)} BPM` : "—"}</td>
        <td>${session.peak_bpm != null ? `${escapeHtml(session.peak_bpm)} BPM` : "—"}</td>
        <td>${escapeHtml(duration)}</td>
        <td><span class="pill ${isAlert ? "watch" : "good"}">${escapeHtml(status)}</span></td>
      </tr>`;
  }).join("");
}

/* ---------- loading ---------- */

async function loadDashboardData(){
  try{
    const [analytics, alerts, history, athlete] = await Promise.all([
      getAnalytics(),
      getAlerts(),
      getHistory(),
      getAthlete().catch(() => null)   // older backends do not have /athlete
    ]);

    apiAlerts = Array.isArray(alerts.alerts) ? alerts.alerts : [];
    apiHistory = Array.isArray(history.sessions) ? history.sessions : [];
    apiAthlete = athlete;

    updateAnalytics(analytics);
    renderAlerts();
    renderHistory();
  }catch(error){
    console.error("Dashboard API error:", error);
    setStatus(false, false);
    const preview = document.getElementById("alertPreview");
    if(preview){
      preview.innerHTML = `<div class="alert-preview"><div class="alert-icon warning">!</div><div><strong>Backend connection unavailable</strong><div style="font-size:11px;color:#89939b;margin-top:3px">${escapeHtml(error.message)}</div></div></div>`;
    }
  }
}

async function refreshLive(){
  if(document.hidden) return;
  try{
    updateAnalytics(await getAnalytics());
  }catch(error){
    console.error("Live refresh error:", error);
    setStatus(false, false);
  }
}

/* ---------- assistant ---------- */

const modal=document.getElementById("chatModal");
const askBtn=document.getElementById("askBtn");
const closeChat=document.getElementById("closeChat");
const sendChat=document.getElementById("sendChat");

function updateChatGreeting(){
  const greeting = document.getElementById("chatGreeting");
  const box = document.querySelector(".chat-box");
  if(!greeting || (box && box.querySelector(".user"))) return;  // conversation already started

  if(lastAnalytics && isLive(lastAnalytics) && lastAnalytics.current_bpm != null){
    const zone = lastAnalytics.ai?.zone ?? lastAnalytics.current_zone;
    const dir = lastAnalytics.trend?.direction;
    const details = [zone, dir && dir !== "unknown" ? `trend ${dir}` : null].filter(Boolean).join(", ");
    greeting.textContent = `Your latest reading is ${lastAnalytics.current_bpm} BPM${details ? ` (${details})` : ""}. What would you like to know?`;
  }else{
    greeting.textContent = "There is no live heart-rate signal right now, but you can still ask about training zones and recovery.";
  }
}

if(askBtn) askBtn.onclick=()=>{
  updateChatGreeting();
  modal.classList.remove("hidden");
};
if(closeChat) closeChat.onclick=()=>modal.classList.add("hidden");

if(sendChat){
  sendChat.onclick=async()=>{
    const input=document.getElementById("chatInput");
    const box=document.querySelector(".chat-box");
    const message=input?.value.trim();

    if(!message) return;

    box.innerHTML += `<div class="user">${escapeHtml(message)}</div>`;
    input.value="";
    sendChat.disabled=true;
    sendChat.textContent="Sending...";

    try{
      const result = await sendChatMessage(message);
      box.innerHTML += `<div class="bot">${escapeHtml(result.reply || "No response returned.")}</div>`;
      box.scrollTop = box.scrollHeight;
    }catch(error){
      box.innerHTML += `<div class="bot">Sorry, the assistant could not be reached. ${escapeHtml(error.message)}</div>`;
    }finally{
      sendChat.disabled=false;
      sendChat.textContent="Send";
    }
  };
}

/* ---------- start-up ---------- */

window.addEventListener("resize",drawChart);
renderAlerts();
renderHistory();
renderProfile();
drawChart();

let liveTimer = null;
let fullTimer = null;

onAuthStateChanged(auth, user => {
  if(user){
    updateUserDetails(user);
    loadDashboardData();
    if(!liveTimer) liveTimer = setInterval(refreshLive, 3000);
    if(!fullTimer) fullTimer = setInterval(() => { if(!document.hidden) loadDashboardData(); }, 15000);
  }else{
    clearInterval(liveTimer);
    clearInterval(fullTimer);
    liveTimer = fullTimer = null;
  }
});
