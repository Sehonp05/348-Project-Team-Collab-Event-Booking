from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3, os, logging, pathlib
from typing import Optional

app = FastAPI(title="Corporate Team Building Event Booking System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log = logging.getLogger("uvicorn.error")

DB_PATH = os.getenv("DB_PATH", "app.db")

EMBEDDED_SCHEMA = r"""
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS Companies (
  company_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL UNIQUE,
  industry     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Teams (
  team_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id   INTEGER NOT NULL,
  name         TEXT NOT NULL,
  department   TEXT NOT NULL,
  leader_name  TEXT NOT NULL,
  leader_email TEXT NOT NULL UNIQUE,
  headcount    INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY(company_id) REFERENCES Companies(company_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Venues (
  venue_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL,
  category     TEXT NOT NULL,
  address      TEXT,
  max_capacity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS TimeSlots (
  slot_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  venue_id     INTEGER NOT NULL,
  slot_date    TEXT NOT NULL,
  start_time   TEXT NOT NULL,
  end_time     TEXT NOT NULL,
  max_capacity INTEGER NOT NULL,
  is_available INTEGER NOT NULL DEFAULT 1,
  FOREIGN KEY(venue_id) REFERENCES Venues(venue_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Bookings (
  booking_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id      INTEGER NOT NULL,
  slot_id      INTEGER NOT NULL,
  headcount    INTEGER NOT NULL,
  status       TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','confirmed','cancelled')),
  note         TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(team_id) REFERENCES Teams(team_id) ON DELETE CASCADE,
  FOREIGN KEY(slot_id) REFERENCES TimeSlots(slot_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_teams_company    ON Teams(company_id);
CREATE INDEX IF NOT EXISTS idx_slots_venue      ON TimeSlots(venue_id);
CREATE INDEX IF NOT EXISTS idx_slots_date       ON TimeSlots(slot_date);
CREATE INDEX IF NOT EXISTS idx_slots_available  ON TimeSlots(is_available, slot_date);
CREATE INDEX IF NOT EXISTS idx_bookings_team    ON Bookings(team_id);
CREATE INDEX IF NOT EXISTS idx_bookings_slot    ON Bookings(slot_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status  ON Bookings(status, created_at);
"""

EMBEDDED_SEED = r"""
INSERT INTO Companies (name, industry) VALUES
  ('Purdue',  'Education'),
  ('CS',      'Engineering'),
  ('348',     'Consulting');

INSERT INTO Teams (company_id, name, department, leader_name, leader_email, headcount) VALUES
  (1, 'Engineering',  'Engineering',  'Sehyeong1', 'Sehyeong1@purdue.edu', 12),
  (1, 'HR',           'HR',           'Sehyeong2', 'Sehyeong2@purdue.edu',  8),
  (2, 'Server',       'Server',       'Sehyeong3', 'Sehyeong3@purdue.edu', 10),
  (2, 'Cloud',        'Cloud',        'Sehyeong4', 'Sehyeong4@purdue.edu', 15),
  (3, 'Accounting',   'Accounting',   'Sehyeong5', 'Sehyeong5@purdue.edu',  6),
  (3, 'Marketing',    'Marketing',    'Sehyeong6', 'Sehyeong6@purdue.edu',  9);

INSERT INTO Venues (name, category, address, max_capacity) VALUES
  ('LaserTag', 'Laser Tag',    '111 St, West Lafayette, Indiana, 47906', 30),
  ('Bowling',  'Bowling',      '222 St, West Lafayette, Indiana, 47906', 40),
  ('GoCart',   'Go-Kart',      '333 St, West Lafayette, Indiana, 47906', 20),
  ('Tennis',   'Tennis Court', '444 St, West Lafayette, Indiana, 47906', 24),
  ('McDonalds','Restaurant',   '555 St, West Lafayette, Indiana, 47906', 60);

INSERT INTO TimeSlots (venue_id, slot_date, start_time, end_time, max_capacity, is_available) VALUES
  (1, '2026-04-01', '10:00', '11:00', 20, 1),
  (1, '2026-04-01', '14:00', '15:00', 20, 1),
  (1, '2026-04-01', '19:00', '20:00', 30, 1),
  (1, '2026-04-02', '10:00', '11:00', 30, 1),
  (1, '2026-04-02', '15:00', '16:00', 30, 1),
  (1, '2026-04-03', '11:00', '12:00', 20, 1),
  (2, '2026-04-01', '12:00', '14:00', 40, 1),
  (2, '2026-04-01', '18:00', '20:00', 40, 1),
  (2, '2026-04-02', '12:00', '14:00', 40, 1),
  (2, '2026-04-03', '13:00', '15:00', 40, 1),
  (3, '2026-04-01', '09:00', '10:30', 20, 1),
  (3, '2026-04-01', '13:00', '14:30', 20, 1),
  (3, '2026-04-02', '10:00', '11:30', 20, 1),
  (3, '2026-04-03', '09:00', '10:30', 20, 1),
  (4, '2026-04-01', '08:00', '10:00', 24, 1),
  (4, '2026-04-01', '14:00', '16:00', 24, 1),
  (4, '2026-04-02', '09:00', '11:00', 24, 1),
  (4, '2026-04-03', '14:00', '16:00', 24, 1),
  (5, '2026-04-01', '11:00', '13:00', 60, 1),
  (5, '2026-04-01', '17:00', '19:00', 60, 1),
  (5, '2026-04-02', '11:00', '13:00', 60, 1),
  (5, '2026-04-03', '12:00', '14:00', 60, 1);
"""

EMBEDDED_FRONTEND = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Team Building System</title>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
  :root { --bg:#0f172a; --fg:#e2e8f0; --muted:#94a3b8; --card:#0b1220; --line:#1f2937; --accent:#22d3ee; }
  *{box-sizing:border-box}
  body{ margin:0; background:var(--bg); color:var(--fg); font-family:ui-sans-serif,system-ui,sans-serif; font-size:14px; }
  h1{ font-size:20px; margin:0 0 4px; }
  h2{ font-size:16px; margin:0 0 12px; }
  header{ background:var(--card); padding:16px 24px; border-bottom:1px solid var(--line); }
  header p{ margin:0; font-size:12px; color:var(--muted); }
  nav{ background:var(--card); border-bottom:1px solid var(--line); padding:0 24px; display:flex; gap:4px; }
  .tab{ padding:10px 16px; cursor:pointer; color:var(--muted); font-size:13px; border-bottom:2px solid transparent; }
  .tab:hover{ color:var(--fg); }
  .tab.active{ color:var(--accent); border-bottom-color:var(--accent); }
  main{ padding:24px; max-width:1100px; margin:0 auto; }
  .page{ display:none; }
  .page.active{ display:block; }
  section{ background:var(--card); padding:16px; border:1px solid var(--line); border-radius:10px; margin:12px 0; }
  label{ display:block; font-size:12px; color:var(--muted); margin-bottom:5px; }
  input,select,textarea{ width:100%; padding:8px 10px; border-radius:8px; border:1px solid var(--line); background:#060d1a; color:var(--fg); font-size:13px; margin-bottom:10px; }
  textarea{ resize:vertical; min-height:60px; }
  button{ padding:8px 14px; border-radius:8px; cursor:pointer; font-size:13px; border:1px solid var(--line); background:transparent; color:var(--fg); }
  button.primary{ background:var(--accent); color:#000; border:none; font-weight:600; }
  button.danger{ color:#f87171; border-color:#f87171; }
  .right{ display:flex; gap:8px; justify-content:flex-end; margin-top:8px; }
  .cols{ display:flex; gap:12px; flex-wrap:wrap; }
  .cols > div{ flex:1; min-width:140px; }
  table{ width:100%; border-collapse:collapse; font-size:13px; margin-top:8px; }
  th,td{ border-bottom:1px solid var(--line); padding:8px; text-align:left; }
  th{ color:var(--muted); font-size:12px; }
  .pill{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; border:1px solid var(--line); color:var(--muted); }
  .pill-pending{ color:#fbbf24; border-color:#fbbf24; }
  .pill-confirmed{ color:#4ade80; border-color:#4ade80; }
  .pill-cancelled{ color:#f87171; border-color:#f87171; }
  input[type=hidden]{ display:none!important; }
  #toast{ position:fixed; bottom:20px; right:20px; background:#1e293b; color:var(--fg); padding:10px 16px; border-radius:8px; font-size:13px; border:1px solid var(--line); display:none; z-index:9999; }
  #toast.show{ display:block; }
  #toast.success{ border-color:#4ade80; color:#4ade80; }
  #toast.error{ border-color:#f87171; color:#f87171; }
  pre{ background:#060d1a; color:#4ade80; padding:12px; border-radius:8px; font-size:12px; overflow:auto; margin-top:10px; border:1px solid var(--line); white-space:pre-wrap; }
</style>
</head>
<body>

<header>
  <h1>Team Building System</h1>
  <p>designed by Sehyeong Oh (oh283)</p>
</header>

<nav>
  <div class="tab active" onclick="goTab('bookings')">Bookings</div>
  <div class="tab" onclick="goTab('new-booking')">New Booking</div>
  <div class="tab" onclick="goTab('venues')">Venues & Slots</div>
  <div class="tab" onclick="goTab('teams')">Teams</div>
  <div class="tab" onclick="goTab('admin')">Admin</div>
</nav>

<main>

<div class="page active" id="page-bookings">
  <h2>Bookings</h2>

  <section id="edit-section" style="display:none">
    <h2>Edit Booking #<span id="edit-id-label"></span></h2>
    <input type="hidden" id="edit-id"/>
    <div class="cols">
      <div>
        <label>Status</label>
        <select id="edit-status">
          <option value="pending">pending</option>
          <option value="confirmed">confirmed</option>
          <option value="cancelled">cancelled</option>
        </select>
      </div>
      <div><label>Headcount</label><input type="number" id="edit-headcount" min="1"/></div>
      <div><label>Note</label><input type="text" id="edit-note"/></div>
    </div>
    <div class="right">
      <button onclick="cancelEdit()">Cancel</button>
      <button class="primary" onclick="saveEdit()">Save</button>
    </div>
  </section>

  <section>
    <div class="cols">
      <div>
        <label>Filter by Status</label>
        <select id="f-status" onchange="refreshBookings()">
          <option value="">(all)</option>
          <option value="pending">pending</option>
          <option value="confirmed">confirmed</option>
          <option value="cancelled">cancelled</option>
        </select>
      </div>
      <div>
        <label>Filter by Company</label>
        <select id="f-company" onchange="refreshBookings()"><option value="">(all)</option></select>
      </div>
      <div>
        <label>Filter by Team</label>
        <select id="f-team" onchange="refreshBookings()"><option value="">(all)</option></select>
      </div>
    </div>
    <div class="right"><button onclick="refreshBookings()">Refresh</button></div>
    <table>
      <thead><tr><th>ID</th><th>Team</th><th>Company</th><th>Venue</th><th>Date</th><th>Time</th><th>Headcount</th><th>Status</th><th>Note</th><th></th></tr></thead>
      <tbody id="bookings-tbody"><tr><td colspan="10" style="color:var(--muted);padding:20px">Loading...</td></tr></tbody>
    </table>
  </section>
</div>

<div class="page" id="page-new-booking">
  <h2>New Booking</h2>
  <section>
    <div class="cols">
      <div>
        <label>Company</label>
        <select id="nb-company" onchange="onNbCompanyChange()"><option value="">-- select --</option></select>
      </div>
      <div>
        <label>Team</label>
        <select id="nb-team" onchange="onNbTeamChange()"><option value="">-- select --</option></select>
      </div>
      <div><label>Headcount</label><input type="number" id="nb-headcount" min="1" placeholder="# of people"/></div>
    </div>
    <div class="cols">
      <div>
        <label>Venue</label>
        <select id="nb-venue" onchange="onNbVenueChange()"><option value="">-- select --</option></select>
      </div>
      <div>
        <label>Date</label>
        <select id="nb-date" onchange="loadNbSlots()"><option value="">-- select --</option></select>
      </div>
      <div>
        <label>Time Slot</label>
        <select id="nb-slot"><option value="">-- select --</option></select>
      </div>
    </div>
    <div class="cols">
      <div><label>Note (optional)</label><input type="text" id="nb-note" placeholder="any special requirements"/></div>
    </div>
    <div class="right">
      <button onclick="goTab('bookings')">Cancel</button>
      <button class="primary" onclick="submitBooking()">Create Booking</button>
    </div>
  </section>
</div>

<div class="page" id="page-venues">
  <h2>Venues & Time Slots</h2>
  <section>
    <div class="cols">
      <div>
        <label>Select Venue</label>
        <select id="vp-venue" onchange="loadVenueSlots()"><option value="">-- select --</option></select>
      </div>
    </div>
    <table id="vp-table" style="display:none">
      <thead><tr><th>Slot ID</th><th>Date</th><th>Start</th><th>End</th><th>Capacity</th><th>Available</th></tr></thead>
      <tbody id="vp-tbody"></tbody>
    </table>
  </section>
</div>

<div class="page" id="page-teams">
  <h2>Teams</h2>
  <section>
    <div class="cols">
      <div>
        <label>Filter by Company</label>
        <select id="tp-company" onchange="loadTeamsPage()"><option value="">(all)</option></select>
      </div>
    </div>
    <table>
      <thead><tr><th>ID</th><th>Team</th><th>Department</th><th>Company</th><th>Leader</th><th>Email</th><th>Headcount</th></tr></thead>
      <tbody id="teams-tbody"></tbody>
    </table>
  </section>
</div>

<div class="page" id="page-admin">
  <h2>Admin</h2>
  <section>
    <p style="color:var(--muted);margin-bottom:12px">Re-seed resets all data to demo dataset.</p>
    <button class="danger" onclick="reseed()">Re-seed Database</button>
  </section>
  <section>
    <label>Query Plan (Index Demo)</label>
    <select id="qp-kind">
      <option value="bookings_by_status">Bookings by status &rarr; idx_bookings_status</option>
      <option value="available_slots">Available slots (composite) &rarr; idx_slots_available</option>
      <option value="slots_by_date">Slots by date &rarr; idx_slots_date</option>
      <option value="slots_by_venue">Slots by venue &rarr; idx_slots_venue</option>
      <option value="bookings_by_team">Bookings by team &rarr; idx_bookings_team</option>
      <option value="bookings_by_slot">Bookings by slot &rarr; idx_bookings_slot</option>
      <option value="teams_by_company">Teams by company &rarr; idx_teams_company</option>
    </select>
    <div class="right"><button class="primary" onclick="runQP()">Explain</button></div>
    <pre id="qp-out" style="display:none"></pre>
  </section>
</div>

</main>
<div id="toast"></div>

<script>
const $ = s => document.querySelector(s);
async function api(m,p,b){
  const r = await fetch(p,{method:m,headers:{"Content-Type":"application/json"},body:b?JSON.stringify(b):undefined});
  const d = await r.json().catch(()=>({detail:"error"}));
  if(!r.ok) throw new Error(d.detail||JSON.stringify(d));
  return d;
}
const get  = p    => api("GET",p);
const post = (p,b)=> api("POST",p,b);
const put  = (p,b)=> api("PUT",p,b);
const del  = p    => api("DELETE",p);

function toast(msg,type=""){
  const t=$("#toast"); t.textContent=msg; t.className="show "+type;
  setTimeout(()=>t.className="",3000);
}
function pill(s){ return `<span class="pill pill-${s}">${s}</span>`; }

let _companies=[], _teams=[], _venues=[];

async function loadLookups(){
  [_companies,_teams,_venues] = await Promise.all([get("/companies"),get("/teams"),get("/venues")]);
  ["f-company","tp-company"].forEach(id=>{
    const el=document.getElementById(id); if(!el)return;
    const first=el.options[0]; el.innerHTML=""; if(first)el.appendChild(first);
    _companies.forEach(c=>{ const o=document.createElement("option"); o.value=c.company_id; o.textContent=c.name; el.appendChild(o); });
  });
  const nbC=document.getElementById("nb-company");
  nbC.innerHTML='<option value="">-- select --</option>';
  _companies.forEach(c=>{ const o=document.createElement("option"); o.value=c.company_id; o.textContent=c.name; nbC.appendChild(o); });
  const nbV=document.getElementById("nb-venue");
  nbV.innerHTML='<option value="">-- select --</option>';
  _venues.forEach(v=>{ const o=document.createElement("option"); o.value=v.venue_id; o.textContent=v.name+" ("+v.category+")"; nbV.appendChild(o); });
  const vpV=document.getElementById("vp-venue");
  vpV.innerHTML='<option value="">-- select --</option>';
  _venues.forEach(v=>{ const o=document.createElement("option"); o.value=v.venue_id; o.textContent=v.name; vpV.appendChild(o); });
}

function goTab(id){
  document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
  document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(t=>{ if(t.getAttribute("onclick")?.includes("'"+id+"'")) t.classList.add("active"); });
  $("#page-"+id)?.classList.add("active");
  if(id==="bookings") refreshBookings();
  if(id==="teams")    loadTeamsPage();
  if(id==="venues")   document.getElementById("vp-table").style.display="none";
}

async function refreshBookings(){
  const status  = document.getElementById("f-status")?.value||"";
  const company = document.getElementById("f-company")?.value||"";
  const team    = document.getElementById("f-team")?.value||"";
  const ts=document.getElementById("f-team"); const prev=ts.value;
  ts.innerHTML='<option value="">(all)</option>';
  _teams.filter(t=>!company||String(t.company_id)===company).forEach(t=>{
    const o=document.createElement("option"); o.value=t.team_id; o.textContent=t.name; ts.appendChild(o);
  });
  ts.value=prev;
  let qs=new URLSearchParams();
  if(status)  qs.set("status",status);
  if(company) qs.set("company_id",company);
  if(team)    qs.set("team_id",team);
  const rows=await get("/bookings?"+qs).catch(e=>{toast(e.message,"error");return[];});
  const tb=document.getElementById("bookings-tbody");
  if(!rows.length){ tb.innerHTML=`<tr><td colspan="10" style="color:var(--muted);padding:20px">No bookings.</td></tr>`; return; }
  tb.innerHTML=rows.map(b=>`<tr>
    <td>${b.booking_id}</td><td>${b.team_name}</td><td>${b.company_name}</td>
    <td>${b.venue_name}</td><td>${b.slot_date}</td><td>${b.start_time}-${b.end_time}</td>
    <td>${b.headcount}</td><td>${pill(b.status)}</td>
    <td style="color:var(--muted)">${b.note||"-"}</td>
    <td style="white-space:nowrap">
      <button onclick="startEdit(${b.booking_id},'${b.status}',${b.headcount},\`${(b.note||"").replace(/\`/g,"'")}\`)">Edit</button>
      <button class="danger" onclick="deleteBooking(${b.booking_id})">Del</button>
    </td>
  </tr>`).join("");
}
function startEdit(id,status,headcount,note){
  const s=document.getElementById("edit-section"); s.style.display="block";
  document.getElementById("edit-id").value=id;
  document.getElementById("edit-id-label").textContent=id;
  document.getElementById("edit-status").value=status;
  document.getElementById("edit-headcount").value=headcount;
  document.getElementById("edit-note").value=note;
  s.scrollIntoView({behavior:"smooth"});
}
function cancelEdit(){ document.getElementById("edit-section").style.display="none"; }
async function saveEdit(){
  const id=document.getElementById("edit-id").value;
  const status=document.getElementById("edit-status").value;
  const headcount=Number(document.getElementById("edit-headcount").value);
  const note=document.getElementById("edit-note").value;
  if(headcount<1){toast("Headcount must be >= 1","error");return;}
  await put("/bookings/"+id,{status,headcount,note}).catch(e=>{toast(e.message,"error");return null;});
  toast("Updated","success"); cancelEdit(); refreshBookings();
}
async function deleteBooking(id){
  if(!confirm("Delete booking #"+id+"?")) return;
  await del("/bookings/"+id).catch(e=>{toast(e.message,"error");return null;});
  toast("Deleted"); refreshBookings();
}

function onNbCompanyChange(){
  const cid=document.getElementById("nb-company").value;
  const ts=document.getElementById("nb-team");
  ts.innerHTML='<option value="">-- select --</option>';
  _teams.filter(t=>String(t.company_id)===cid).forEach(t=>{
    const o=document.createElement("option"); o.value=t.team_id; o.textContent=t.name; ts.appendChild(o);
  });
}
function onNbTeamChange(){
  const tid=document.getElementById("nb-team").value;
  const t=_teams.find(x=>String(x.team_id)===tid);
  if(t) document.getElementById("nb-headcount").value=t.headcount;
}
async function onNbVenueChange(){
  const vid=document.getElementById("nb-venue").value;
  if(!vid) return;
  const slots=await get("/timeslots?venue_id="+vid).catch(()=>[]);
  const dates=[...new Set(slots.map(s=>s.slot_date))].sort();
  const ds=document.getElementById("nb-date");
  ds.innerHTML='<option value="">-- select --</option>';
  dates.forEach(d=>{ const o=document.createElement("option"); o.value=d; o.textContent=d; ds.appendChild(o); });
  document.getElementById("nb-slot").innerHTML='<option value="">-- select --</option>';
}
async function loadNbSlots(){
  const vid=document.getElementById("nb-venue").value;
  const date=document.getElementById("nb-date").value;
  if(!vid||!date) return;
  const slots=await get("/timeslots?venue_id="+vid+"&date="+date).catch(()=>[]);
  const hc=Number(document.getElementById("nb-headcount").value)||0;
  const ss=document.getElementById("nb-slot");
  ss.innerHTML='<option value="">-- select --</option>';
  slots.filter(s=>s.is_available&&(!hc||s.max_capacity>=hc)).forEach(s=>{
    const o=document.createElement("option"); o.value=s.slot_id;
    o.textContent=s.start_time+" - "+s.end_time+" (cap "+s.max_capacity+")";
    ss.appendChild(o);
  });
}
async function submitBooking(){
  const team_id=Number(document.getElementById("nb-team").value);
  const slot_id=Number(document.getElementById("nb-slot").value);
  const headcount=Number(document.getElementById("nb-headcount").value);
  const note=document.getElementById("nb-note").value||null;
  if(!team_id||!slot_id||!headcount){toast("Fill in all fields","error");return;}
  const r=await post("/bookings",{team_id,slot_id,headcount,note,status:"pending"}).catch(e=>{toast(e.message,"error");return null;});
  if(!r) return;
  toast("Booking #"+r.booking_id+" created","success");
  goTab("bookings");
}

async function loadVenueSlots(){
  const vid=document.getElementById("vp-venue").value;
  if(!vid){ document.getElementById("vp-table").style.display="none"; return; }
  const slots=await get("/timeslots?venue_id="+vid).catch(()=>[]);
  const tb=document.getElementById("vp-tbody");
  tb.innerHTML=slots.map(s=>`<tr>
    <td>${s.slot_id}</td><td>${s.slot_date}</td><td>${s.start_time}</td><td>${s.end_time}</td>
    <td>${s.max_capacity}</td><td style="color:${s.is_available?"#4ade80":"#f87171"}">${s.is_available?"Available":"Booked"}</td>
  </tr>`).join("")||`<tr><td colspan="6" style="color:var(--muted)">No slots.</td></tr>`;
  document.getElementById("vp-table").style.display="table";
}

async function loadTeamsPage(){
  const cid=document.getElementById("tp-company").value;
  let qs=new URLSearchParams(); if(cid) qs.set("company_id",cid);
  const teams=await get("/teams?"+qs).catch(()=>[]);
  document.getElementById("teams-tbody").innerHTML=teams.map(t=>`<tr>
    <td>${t.team_id}</td><td>${t.name}</td><td>${t.department}</td><td>${t.company_name}</td>
    <td>${t.leader_name}</td><td style="color:var(--muted)">${t.leader_email}</td><td>${t.headcount}</td>
  </tr>`).join("")||`<tr><td colspan="7" style="color:var(--muted)">No teams.</td></tr>`;
}

async function reseed(){
  if(!confirm("Reset all data?")) return;
  await post("/admin/reseed").catch(e=>{toast(e.message,"error");return null;});
  toast("Re-seeded","success"); await loadLookups(); refreshBookings();
}
async function runQP(){
  const kind=document.getElementById("qp-kind").value;
  const d=await get("/admin/qp?kind="+kind).catch(e=>{toast(e.message,"error");return null;});
  if(!d) return;
  const el=document.getElementById("qp-out"); el.style.display="block";
  el.textContent =
    "-- "+d.description+" --\n\nSQL:\n"+d.sql+"\n\nPLAN:\n"+
    JSON.stringify(d.plan,null,2);
}

(async()=>{ await loadLookups(); refreshBookings(); })();
</script>
</body>
</html>
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=3000;")
    return conn


def tx_begin(conn, mode="IMMEDIATE"):
    conn.execute(f"BEGIN {mode};")

def tx_commit(conn):
    conn.execute("COMMIT;")

def tx_rollback(conn):
    conn.execute("ROLLBACK;")


def init_db():
    conn = get_conn()
    conn.executescript(EMBEDDED_SCHEMA)
    cnt = conn.execute("SELECT COUNT(*) FROM Companies").fetchone()[0]
    if cnt == 0:
        conn.executescript(EMBEDDED_SEED)
    conn.close()


@app.on_event("startup")
def on_startup():
    init_db()


class BookingIn(BaseModel):
    team_id:     int
    slot_id:     int
    headcount:   int
    note:        Optional[str] = None
    status:      str = "pending"

class BookingUpdate(BaseModel):
    status:    str
    headcount: int
    note:      Optional[str] = None


VALID_STATUSES = {"pending", "confirmed", "cancelled"}

def validate_status(s: str) -> str:
    if s not in VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {VALID_STATUSES}")
    return s


@app.get("/", response_class=HTMLResponse)
def home():
    return EMBEDDED_FRONTEND

@app.get("/app", response_class=HTMLResponse)
def app_page():
    return EMBEDDED_FRONTEND


@app.get("/companies")
def list_companies():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM Companies ORDER BY name").fetchall()
        return [dict(r) for r in rows]

@app.get("/categories")
def list_categories():
    with get_conn() as conn:
        return [r["category"] for r in conn.execute(
            "SELECT DISTINCT category FROM Venues ORDER BY category")]

@app.get("/teams")
def list_teams(company_id: Optional[int] = None):
    with get_conn() as conn:
        sql = """
            SELECT t.*, c.name AS company_name
            FROM Teams t
            JOIN Companies c ON c.company_id = t.company_id
            WHERE (? IS NULL OR t.company_id = ?)
            ORDER BY c.name, t.name
        """
        rows = conn.execute(sql, (company_id, company_id)).fetchall()
        return [dict(r) for r in rows]

@app.get("/venues")
def list_venues(category: Optional[str] = None):
    with get_conn() as conn:
        sql = """
            SELECT * FROM Venues
            WHERE (? IS NULL OR category = ?)
            ORDER BY category, name
        """
        rows = conn.execute(sql, (category, category)).fetchall()
        return [dict(r) for r in rows]

@app.get("/venues/available")
def available_venues(category: Optional[str] = None, date: Optional[str] = None):
    with get_conn() as conn:
        sql = """
            SELECT v.*, COUNT(s.slot_id) AS available_slots
            FROM Venues v
            JOIN TimeSlots s ON s.venue_id = v.venue_id
            WHERE s.is_available = 1
              AND (? IS NULL OR v.category = ?)
              AND (? IS NULL OR s.slot_date = ?)
            GROUP BY v.venue_id
            ORDER BY v.category, v.name
        """
        rows = conn.execute(sql, (category, category, date, date)).fetchall()
        return [dict(r) for r in rows]

@app.get("/timeslots")
def list_timeslots(venue_id: Optional[int] = None, date: Optional[str] = None):
    with get_conn() as conn:
        sql = """
            SELECT * FROM TimeSlots
            WHERE (? IS NULL OR venue_id = ?)
              AND (? IS NULL OR slot_date = ?)
            ORDER BY slot_date, start_time
        """
        rows = conn.execute(sql, (venue_id, venue_id, date, date)).fetchall()
        return [dict(r) for r in rows]


# ---- Bookings CRUD ----

@app.get("/bookings")
def list_bookings(
    status:     Optional[str] = None,
    company_id: Optional[int] = None,
    team_id:    Optional[int] = None,
):
    if status:
        validate_status(status)
    with get_conn() as conn:
        sql = """
            SELECT b.*,
                   t.name  AS team_name,
                   c.name  AS company_name,
                   v.name  AS venue_name,
                   v.category,
                   s.slot_date, s.start_time, s.end_time
            FROM Bookings b
            JOIN Teams     t ON t.team_id    = b.team_id
            JOIN Companies c ON c.company_id = t.company_id
            JOIN TimeSlots s ON s.slot_id    = b.slot_id
            JOIN Venues    v ON v.venue_id   = s.venue_id
            WHERE (? IS NULL OR b.status     = ?)
              AND (? IS NULL OR c.company_id = ?)
              AND (? IS NULL OR b.team_id    = ?)
            ORDER BY b.booking_id DESC
        """
        rows = conn.execute(sql, (
            status, status,
            company_id, company_id,
            team_id, team_id
        )).fetchall()
        return [dict(r) for r in rows]


def _assert_exists(conn, table: str, pk_col: str, pk_val: int):
    ok = conn.execute(
        f"SELECT 1 FROM {table} WHERE {pk_col} = ? LIMIT 1", (pk_val,)
    ).fetchone()
    if not ok:
        raise HTTPException(400, f"Invalid {table}.{pk_col}: {pk_val}")


@app.post("/bookings", status_code=201)
def create_booking(b: BookingIn):
    validate_status(b.status)
    if b.headcount < 1:
        raise HTTPException(400, "headcount must be >= 1")
    with get_conn() as conn:
        try:
            tx_begin(conn)
            _assert_exists(conn, "Teams",     "team_id", b.team_id)
            _assert_exists(conn, "TimeSlots", "slot_id", b.slot_id)

            slot = conn.execute(
                "SELECT * FROM TimeSlots WHERE slot_id = ?", (b.slot_id,)
            ).fetchone()
            if not slot["is_available"]:
                raise HTTPException(409, "This time slot is no longer available.")
            if b.headcount > slot["max_capacity"]:
                raise HTTPException(400,
                    f"Headcount {b.headcount} exceeds slot capacity {slot['max_capacity']}.")

            cur = conn.execute(
                """INSERT INTO Bookings (team_id, slot_id, headcount, status, note)
                   VALUES (?, ?, ?, ?, ?)""",
                (b.team_id, b.slot_id, b.headcount, b.status, b.note)
            )
            new_id = cur.lastrowid
            conn.execute(
                "UPDATE TimeSlots SET is_available = 0 WHERE slot_id = ?", (b.slot_id,)
            )
            row = conn.execute(
                "SELECT * FROM Bookings WHERE booking_id = ?", (new_id,)
            ).fetchone()
            tx_commit(conn)
            return dict(row)
        except HTTPException:
            tx_rollback(conn)
            raise
        except Exception as e:
            tx_rollback(conn)
            raise HTTPException(500, f"Create failed: {e}")


@app.put("/bookings/{booking_id}")
def update_booking(booking_id: int, upd: BookingUpdate):
    validate_status(upd.status)
    if upd.headcount < 1:
        raise HTTPException(400, "headcount must be >= 1")
    with get_conn() as conn:
        try:
            tx_begin(conn)
            existing = conn.execute(
                "SELECT * FROM Bookings WHERE booking_id = ?", (booking_id,)
            ).fetchone()
            if not existing:
                raise HTTPException(404, "Booking not found")

            if existing["status"] == "cancelled" and upd.status != "cancelled":
                slot = conn.execute(
                    "SELECT * FROM TimeSlots WHERE slot_id = ?",
                    (existing["slot_id"],)
                ).fetchone()
                if upd.headcount > slot["max_capacity"]:
                    raise HTTPException(400, "Headcount exceeds slot capacity")

            conn.execute(
                """UPDATE Bookings
                   SET status=?, headcount=?, note=?
                   WHERE booking_id=?""",
                (upd.status, upd.headcount, upd.note, booking_id)
            )
            row = conn.execute(
                "SELECT * FROM Bookings WHERE booking_id=?", (booking_id,)
            ).fetchone()
            tx_commit(conn)
            return dict(row)
        except HTTPException:
            tx_rollback(conn)
            raise
        except Exception as e:
            tx_rollback(conn)
            raise HTTPException(500, f"Update failed: {e}")


@app.delete("/bookings/{booking_id}")
def delete_booking(booking_id: int):
    with get_conn() as conn:
        try:
            tx_begin(conn)
            existing = conn.execute(
                "SELECT slot_id FROM Bookings WHERE booking_id=?", (booking_id,)
            ).fetchone()
            if not existing:
                raise HTTPException(404, "Booking not found")
            conn.execute("DELETE FROM Bookings WHERE booking_id=?", (booking_id,))
            conn.execute(
                "UPDATE TimeSlots SET is_available=1 WHERE slot_id=?",
                (existing["slot_id"],)
            )
            tx_commit(conn)
            return {"deleted": booking_id}
        except HTTPException:
            tx_rollback(conn)
            raise
        except Exception as e:
            tx_rollback(conn)
            raise HTTPException(500, f"Delete failed: {e}")

@app.get("/reports/bookings")
def report_bookings(
    date_from:  Optional[str] = None,
    date_to:    Optional[str] = None,
    status:     Optional[str] = None,
    company_id: Optional[int] = None,
):
    if status:
        validate_status(status)
    with get_conn() as conn:
        sql = """
            SELECT b.*,
                   t.name  AS team_name,
                   c.name  AS company_name,
                   v.name  AS venue_name,
                   v.category,
                   s.slot_date, s.start_time, s.end_time
            FROM Bookings b
            JOIN Teams     t ON t.team_id    = b.team_id
            JOIN Companies c ON c.company_id = t.company_id
            JOIN TimeSlots s ON s.slot_id    = b.slot_id
            JOIN Venues    v ON v.venue_id   = s.venue_id
            WHERE (? IS NULL OR s.slot_date  >= ?)
              AND (? IS NULL OR s.slot_date  <= ?)
              AND (? IS NULL OR b.status      = ?)
              AND (? IS NULL OR c.company_id  = ?)
            ORDER BY s.slot_date, b.booking_id
        """
        rows = conn.execute(sql, (
            date_from, date_from,
            date_to,   date_to,
            status,    status,
            company_id, company_id
        )).fetchall()
        bookings = [dict(r) for r in rows]

        total   = len(bookings)
        conf    = sum(1 for b in bookings if b["status"]=="confirmed")
        pend    = sum(1 for b in bookings if b["status"]=="pending")
        canc    = sum(1 for b in bookings if b["status"]=="cancelled")
        total_hc = sum(b["headcount"] for b in bookings)
        avg_hc   = (total_hc / total) if total else None

        from collections import Counter
        venue_counts = Counter(b["venue_name"] for b in bookings)
        top_venue = venue_counts.most_common(1)[0][0] if venue_counts else None

        return {
            "total_bookings":  total,
            "confirmed":       conf,
            "pending":         pend,
            "cancelled":       canc,
            "total_headcount": total_hc,
            "avg_headcount":   avg_hc,
            "top_venue":       top_venue,
            "filters": {
                "date_from": date_from, "date_to": date_to,
                "status": status, "company_id": company_id
            },
            "bookings": bookings,
        }


@app.post("/admin/reseed")
def admin_reseed():
    conn = get_conn()
    conn.executescript("""
        DELETE FROM Bookings;
        DELETE FROM TimeSlots;
        DELETE FROM Venues;
        DELETE FROM Teams;
        DELETE FROM Companies;
    """)
    conn.executescript(EMBEDDED_SEED)
    n = conn.execute("SELECT COUNT(*) FROM Companies").fetchone()[0]
    conn.close()
    return {"ok": True, "companies": n}


@app.get("/admin/qp")
def admin_qp(kind: str):
    queries = {
        "bookings_by_status": (
            """SELECT b.*, t.name AS team_name
               FROM Bookings b
               JOIN Teams t ON t.team_id = b.team_id
               WHERE b.status = ? AND b.created_at >= ?""",
            ("confirmed", "2025-01-01"),
            "Bookings page status filter + /reports/bookings -> idx_bookings_status",
        ),
        "available_slots": (
            """SELECT * FROM TimeSlots
               WHERE is_available = 1 AND slot_date = ?""",
            ("2026-04-01",),
            "New Booking page slot lookup (composite index) -> idx_slots_available",
        ),
        "slots_by_date": (
            """SELECT * FROM TimeSlots WHERE slot_date = ?""",
            ("2026-04-01",),
            "Date-based slot listing -> idx_slots_date",
        ),
        "slots_by_venue": (
            """SELECT * FROM TimeSlots WHERE venue_id = ?""",
            (1,),
            "Venues & Slots page -> idx_slots_venue",
        ),
        "bookings_by_team": (
            """SELECT * FROM Bookings WHERE team_id = ?""",
            (1,),
            "Per-team booking history -> idx_bookings_team",
        ),
        "bookings_by_slot": (
            """SELECT * FROM Bookings WHERE slot_id = ?""",
            (1,),
            "Slot-to-booking join / FK lookup -> idx_bookings_slot",
        ),
        "teams_by_company": (
            """SELECT * FROM Teams WHERE company_id = ?""",
            (1,),
            "Teams page company filter -> idx_teams_company",
        ),
    }
    if kind not in queries:
        raise HTTPException(400, f"Unknown kind. Valid: {list(queries.keys())}")

    sql, params, desc = queries[kind]
    with get_conn() as conn:
        plan = conn.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
        return {
            "kind": kind,
            "description": desc,
            "sql": sql.strip(),
            "plan": [tuple(r) for r in plan],
        }