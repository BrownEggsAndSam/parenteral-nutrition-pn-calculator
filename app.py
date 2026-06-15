from __future__ import annotations
import json, os, secrets, sqlite3
from datetime import date, datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash

load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "instance/pn_calculator.sqlite3")
app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

def f(v: Any, d: float = 0.0) -> float:
    try: return d if v in (None, "") else float(v)
    except (TypeError, ValueError): return d

def r(v: float, p: int = 2) -> float:
    return round(float(v) + 10 ** (-(p + 7)), p)

def calculate(d: dict[str, Any]) -> dict[str, Any]:
    wt=f(d.get("dosing_weight_kg")); tfl=f(d.get("tfl_ml_per_kg_day")); iv=f(d.get("ivfe_dose_g_kg_day"))
    art=f(d.get("non_pn_art_line_ml_hr")); uvc=f(d.get("non_pn_uvc_ml_hr")); picc=f(d.get("non_pn_picc_ml_hr")); meds=f(d.get("non_pn_continuous_meds_ml_hr")); bolus=f(d.get("non_pn_bolus_meds_ml_day"))
    prot=f(d.get("protein_g_kg_day")); dex=f(d.get("dextrose_percent")); rdex=f(d.get("rider_dextrose_percent")); rrate=f(d.get("rider_rate_ml_hr")); access=d.get("access_type") or "Peripheral"
    tfl_day=tfl*wt; tfl_hr=tfl_day/24 if wt>0 else 0
    iv_g=iv*wt; iv_ml=iv_g*5; iv_hr=iv_ml/24 if wt>0 else 0
    bolus_hr=bolus/24 if bolus else 0; nonpn=iv_hr+art+uvc+picc+meds+bolus_hr; pn=tfl_hr-nonpn
    prot_g=prot*wt; prot_kcal=prot_g*4; tpn_gir=(dex*pn*0.167)/wt if wt>0 else 0; rider_gir=(rdex*rrate*0.167)/wt if wt>0 else 0; total_gir=tpn_gir+rider_gir
    vals={"tfl_ml_day":r(tfl_day),"tfl_ml_hr":r(tfl_hr,1),"ivfe_g_day":r(iv_g),"ivfe_ml_day":r(iv_ml),"ivfe_ml_hr":r(iv_hr),"non_pn_bolus_meds_ml_hr":r(bolus_hr),"total_non_pn_ml_hr":r(nonpn),"pn_rate_ml_hr":r(pn,1),"protein_g_day":r(prot_g),"protein_kcal_day":r(prot_kcal),"tpn_gir":r(tpn_gir),"rider_gir":r(rider_gir),"total_gir":r(total_gir)}
    warn=[]
    if wt<=0: warn.append("Dosing weight is required before calculations can be trusted.")
    if vals["pn_rate_ml_hr"]<0: warn.append("Non-PN fluids exceed the total fluid limit. Review inputs.")
    if access=="Peripheral" and dex>12.5: warn.append("Peripheral access: worksheet max is D12.5 and osmolarity ≤1000.")
    if wt>0 and dex>0 and vals["total_gir"]<4: warn.append("Worksheet note: Total GIR should generally not be <4 mg/kg/min in ELBW infants when NPO or on trophic feeds.")
    if vals["total_gir"]>14: warn.append("Worksheet note: Avoid GIR >14 mg/kg/min unless needed for hypoglycemia.")
    return {"values": vals, "warnings": warn}

SCHEMA="""CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT,session_name TEXT NOT NULL,calculation_date TEXT NOT NULL,dosing_weight_kg REAL DEFAULT 0,tfl_ml_per_kg_day REAL DEFAULT 0,ivfe_dose_g_kg_day REAL DEFAULT 0,non_pn_art_line_ml_hr REAL DEFAULT 0,non_pn_uvc_ml_hr REAL DEFAULT 0,non_pn_picc_ml_hr REAL DEFAULT 0,non_pn_continuous_meds_ml_hr REAL DEFAULT 0,non_pn_bolus_meds_ml_day REAL DEFAULT 0,protein_g_kg_day REAL DEFAULT 0,dextrose_percent REAL DEFAULT 0,rider_dextrose_percent REAL DEFAULT 0,rider_rate_ml_hr REAL DEFAULT 0,access_type TEXT DEFAULT 'Peripheral',notes TEXT DEFAULT '',calculated_json TEXT DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);"""
FIELDS=["session_name","calculation_date","dosing_weight_kg","tfl_ml_per_kg_day","ivfe_dose_g_kg_day","non_pn_art_line_ml_hr","non_pn_uvc_ml_hr","non_pn_picc_ml_hr","non_pn_continuous_meds_ml_hr","non_pn_bolus_meds_ml_day","protein_g_kg_day","dextrose_percent","rider_dextrose_percent","rider_rate_ml_hr","access_type","notes"]
NUM=set(FIELDS)-{"session_name","calculation_date","access_type","notes"}

def db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True); con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; return con
with db() as con: con.executescript(SCHEMA)
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def csrf():
    session.setdefault("csrf_token", secrets.token_urlsafe(32)); return session["csrf_token"]
def csrf_ok(): return bool(session.get("csrf_token") and request.form.get("csrf_token")==session.get("csrf_token"))
def pw_ok(p):
    h=os.getenv("APP_ACCESS_PASSWORD_HASH")
    return check_password_hash(h,p) if h else secrets.compare_digest(os.getenv("APP_ACCESS_PASSWORD","changeme"),p)
def need_login(fn):
    @wraps(fn)
    def inner(*a,**k):
        if not session.get("authenticated"): return redirect(url_for("login", next=request.path))
        return fn(*a,**k)
    return inner
def form_data():
    d={}
    for x in FIELDS:
        v=request.form.get(x,"").strip(); d[x]=f(v) if x in NUM else v
    d["calculation_date"]=d.get("calculation_date") or date.today().isoformat(); d["access_type"]=d.get("access_type") or "Peripheral"; return d
def blank(): return {x:"" for x in FIELDS} | {"calculation_date":date.today().isoformat(),"access_type":"Peripheral","non_pn_art_line_ml_hr":0,"non_pn_uvc_ml_hr":0,"non_pn_picc_ml_hr":0}
def get_row(i):
    with db() as con: row=con.execute("SELECT * FROM sessions WHERE id=?",(i,)).fetchone()
    if not row: abort(404)
    return row

CSS="""*{box-sizing:border-box}body{margin:0;background:#f6f7fb;color:#152033;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}.wrap{width:min(920px,100%);margin:0 auto;padding:12px 10px 92px}.top{position:sticky;top:0;z-index:3;background:rgba(246,247,251,.95);backdrop-filter:blur(12px);border-bottom:1px solid #e4e8f0}.topin{width:min(920px,100%);margin:auto;padding:10px;display:flex;justify-content:space-between;gap:8px;align-items:center}.brand{font-weight:900}.muted{color:#687386;font-size:12px}.card{background:white;border:1px solid #e4e8f0;border-radius:18px;padding:14px;margin:10px 0;box-shadow:0 8px 22px #0f172a0d}.title{display:flex;gap:8px;align-items:center;margin:0 0 10px}.num{background:#1d4ed8;color:white;width:24px;height:24px;border-radius:99px;display:grid;place-items:center;font-size:12px;font-weight:900}h1{font-size:22px}h2{font-size:16px;margin:0}label{font-size:13px;font-weight:800;display:block;margin:0 0 5px}.req{color:#b91c1c;margin-left:3px}input,select,textarea{width:100%;min-height:46px;border:1px solid #cfd6e3;border-radius:14px;padding:12px;font-size:16px}.grid{display:grid;gap:10px}@media(min-width:720px){.grid2{grid-template-columns:1fr 1fr}}.row{display:flex;gap:6px}.row input{min-width:0}.unit{min-width:70px;border:1px solid #cfd6e3;background:#f8fafc;border-radius:14px;display:grid;place-items:center;color:#687386;font-size:12px;font-weight:900}.calc{background:#f8fbff;border:1px dashed #c8d7f5;border-radius:14px;padding:10px;margin-top:8px;font-size:13px;overflow-wrap:anywhere}.calc b{color:#0f3f9e}.btn{border:0;border-radius:999px;padding:12px 16px;font-weight:900;cursor:pointer;display:inline-flex;text-decoration:none}.primary{background:#1d4ed8;color:white}.soft{background:#eef4ff;color:#1d4ed8}.danger{background:#fee2e2;color:#991b1b}.btns{display:flex;flex-wrap:wrap;gap:8px}.quick{position:fixed;left:0;right:0;bottom:0;background:#fffffff7;backdrop-filter:blur(14px);border-top:1px solid #e4e8f0;z-index:5}.quickin{width:min(920px,100%);margin:auto;display:grid;grid-template-columns:repeat(3,1fr);gap:6px;padding:8px}.q{background:#f8fafc;border:1px solid #e4e8f0;border-radius:14px;text-align:center;padding:8px}.q span{display:block;font-size:10px;color:#687386;font-weight:900}.q b{font-size:14px}.save{grid-column:1/-1}.warn{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:14px;padding:10px;margin-top:8px;font-size:13px}.table{width:100%;border-collapse:collapse}.table td,.table th{border-bottom:1px solid #e4e8f0;padding:9px 4px;text-align:left;font-size:14px}.login{min-height:100vh;display:grid;place-items:center;padding:18px;position:relative;overflow:hidden}.blur{position:absolute;inset:0;background:linear-gradient(135deg,#dbeafe,#f8fafc 45%,#e0f2fe);filter:blur(10px);transform:scale(1.06)}.logincard{position:relative;width:min(440px,100%);background:#ffffffdd;backdrop-filter:blur(20px);border-radius:24px;padding:22px;box-shadow:0 25px 80px #0f172a33}.result{display:grid;grid-template-columns:1fr auto;gap:8px;border-top:1px solid #e4e8f0;padding:9px 0}.result:first-child{border-top:0}.result b{font-size:17px}.flash{padding:10px;border-radius:14px;margin:8px 0;background:#eef4ff;color:#1e3a8a}.note{font-size:12px;color:#687386}@media(max-width:390px){.wrap{padding-left:8px;padding-right:8px}.card{padding:12px}.unit{min-width:58px;font-size:11px}.q b{font-size:13px}}@media print{.top,.quick,.btns{display:none}.wrap{padding:0}.card{box-shadow:none}}"""
BASE="<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>PN Calculator</title><style>"+CSS+"</style></head><body>"
TOP="<header class='top'><div class='topin'><div><div class='brand'>PN Calculator</div><div class='muted'>Quick worksheet math</div></div><form method='post' action='{{url_for(\"logout\")}}'><input type='hidden' name='csrf_token' value='{{csrf_token}}'><button class='btn soft'>Logout</button></form></div></header>"
END="</body></html>"
LOGIN=BASE+"""<div class='login'><div class='blur'></div><main class='logincard'><h1>Restricted PN Calculator</h1><p class='muted'>Enter the shared password to access the calculator.</p>{% for c,m in get_flashed_messages(with_categories=true) %}<div class='flash'>{{m}}</div>{% endfor %}<form method='post'><input type='hidden' name='csrf_token' value='{{csrf_token}}'><label>Password</label><input name='password' type='password' autofocus><br><br><button class='btn primary' style='width:100%;justify-content:center'>Unlock</button></form><p class='note'>Default local password: <b>changeme</b>. Change it in .env.</p></main></div>"""+END
DASH=BASE+TOP+"""<main class='wrap'><div class='card'><h1>Parenteral Nutrition Calculator</h1><p class='muted'>Mobile-first quick calculations for TFL, IVFE, PN rate, protein, and GIR.</p><a class='btn primary' href='{{url_for("new_session")}}'>+ New Calculation</a></div>{% for c,m in get_flashed_messages(with_categories=true) %}<div class='flash'>{{m}}</div>{% endfor %}<div class='card'><h2>Saved Sessions</h2>{% if rows %}<table class='table'><tr><th>Session</th><th>Date</th><th>Weight</th><th></th></tr>{% for x in rows %}<tr><td><b>{{x.session_name}}</b><br><span class='muted'>Updated {{x.updated_at[:10]}}</span></td><td>{{x.calculation_date}}</td><td>{{x.dosing_weight_kg}} kg</td><td class='btns'><a class='btn soft' href='{{url_for("summary",sid=x.id)}}'>View</a><a class='btn soft' href='{{url_for("edit_session",sid=x.id)}}'>Edit</a><form method='post' action='{{url_for("duplicate",sid=x.id)}}'><input type='hidden' name='csrf_token' value='{{csrf_token}}'><button class='btn soft'>Copy</button></form></td></tr>{% endfor %}</table>{% else %}<p class='muted'>No sessions yet.</p>{% endif %}</div></main>"""+END
FORM=BASE+TOP+"""<form method='post' id='calcForm'><input type='hidden' name='csrf_token' value='{{csrf_token}}'><main class='wrap'>
<div class='card'><div class='title'><span class='num'>1</span><h2>Session</h2></div><div class='grid grid2'><div><label>Session Name<span class='req'>*</span></label><input name='session_name' value='{{d.session_name}}' required></div><div><label>Date</label><input type='date' name='calculation_date' value='{{d.calculation_date}}'></div></div><label style='margin-top:10px'>Dosing Weight (kg)<span class='req'>*</span></label><div class='row'><input data-calc name='dosing_weight_kg' inputmode='decimal' value='{{d.dosing_weight_kg}}' required><span class='unit'>kg</span></div></div>
<div class='card'><div class='title'><span class='num'>2</span><h2>Total Fluid Limit</h2></div><label>TFL</label><div class='row'><input data-calc name='tfl_ml_per_kg_day' inputmode='decimal' value='{{d.tfl_ml_per_kg_day}}' placeholder='120'><span class='unit'>mL/kg/day</span></div><div class='calc'>mL/day: <b id='tflDay'>0</b> = TFL × weight<br>mL/hr: <b id='tflHr'>0</b> = mL/day ÷ 24</div></div>
<div class='card'><div class='title'><span class='num'>3</span><h2>IVFE</h2></div><label>Ordered IVFE dose</label><div class='row'><input data-calc name='ivfe_dose_g_kg_day' inputmode='decimal' value='{{d.ivfe_dose_g_kg_day}}'><span class='unit'>g/kg/day</span></div><div class='calc'>g/day: <b id='ivfeGDay'>0</b> = dose × weight<br>mL/day: <b id='ivfeMlDay'>0</b> = g/day × 5 mL/g<br>mL/hr IVFE: <b id='ivfeHr'>0</b> = mL/day ÷ 24</div></div>
<div class='card'><div class='title'><span class='num'>4</span><h2>PN Volume</h2></div><div class='grid grid2'><div><label>Art KVO</label><div class='row'><input data-calc name='non_pn_art_line_ml_hr' inputmode='decimal' value='{{d.non_pn_art_line_ml_hr}}'><span class='unit'>mL/hr</span></div></div><div><label>UVC KVO</label><div class='row'><input data-calc name='non_pn_uvc_ml_hr' inputmode='decimal' value='{{d.non_pn_uvc_ml_hr}}'><span class='unit'>mL/hr</span></div></div><div><label>PICC KVO</label><div class='row'><input data-calc name='non_pn_picc_ml_hr' inputmode='decimal' value='{{d.non_pn_picc_ml_hr}}'><span class='unit'>mL/hr</span></div></div><div><label>Continuous meds</label><div class='row'><input data-calc name='non_pn_continuous_meds_ml_hr' inputmode='decimal' value='{{d.non_pn_continuous_meds_ml_hr}}'><span class='unit'>mL/hr</span></div></div><div><label>Bolus meds/flushes</label><div class='row'><input data-calc name='non_pn_bolus_meds_ml_day' inputmode='decimal' value='{{d.non_pn_bolus_meds_ml_day}}'><span class='unit'>mL/day</span></div></div></div><div class='calc'>Bolus rate: <b id='bolusHr'>0</b> mL/hr = bolus ÷ 24<br>Total non-PN: <b id='nonPnTotal'>0</b> mL/hr = IVFE + KVOs + meds<br>PN rate: <b id='pnRate'>0</b> mL/hr = TFL - non-PN<br>Order range: <b id='pnRange'>0–0 mL/hr</b></div><p class='note'>KVO = keep vein open. Order PN as a range so bedside nurses can titrate to TFL.</p></div>
<div class='card'><div class='title'><span class='num'>5</span><h2>Protein</h2></div><label>Ordered protein dose</label><div class='row'><input data-calc name='protein_g_kg_day' inputmode='decimal' value='{{d.protein_g_kg_day}}'><span class='unit'>g/kg/day</span></div><div class='calc'>Protein g/day: <b id='proteinGDay'>0</b> = dose × weight<br>Protein kcal/day: <b id='proteinKcal'>0</b> = g/day × 4</div></div>
<div class='card'><div class='title'><span class='num'>6</span><h2>Dextrose / GIR</h2></div><div class='grid grid2'><div><label>Dextrose</label><div class='row'><input data-calc name='dextrose_percent' inputmode='decimal' value='{{d.dextrose_percent}}'><span class='unit'>%</span></div></div><div><label>Access</label><select data-calc name='access_type'><option {% if d.access_type=='Peripheral' %}selected{% endif %}>Peripheral</option><option {% if d.access_type=='Central' %}selected{% endif %}>Central</option></select></div><div><label>Rider dextrose</label><div class='row'><input data-calc name='rider_dextrose_percent' inputmode='decimal' value='{{d.rider_dextrose_percent}}'><span class='unit'>%</span></div></div><div><label>Rider rate</label><div class='row'><input data-calc name='rider_rate_ml_hr' inputmode='decimal' value='{{d.rider_rate_ml_hr}}'><span class='unit'>mL/hr</span></div></div></div><div class='calc'>TPN GIR: <b id='tpnGir'>0</b> = (% dex × PN rate × 0.167) ÷ kg<br>Rider GIR: <b id='riderGir'>0</b><br>Total GIR: <b id='totalGir'>0</b> mg/kg/min</div><div id='warnings'></div></div>
<div class='card'><label>Notes</label><textarea name='notes'>{{d.notes}}</textarea><div class='btns' style='margin-top:12px'><button class='btn primary'>Save Calculation</button><a class='btn soft' href='{{url_for("dashboard")}}'>Cancel</a></div><p class='note'>Calculation aid only. Verify all PN orders, labs, compatibility, and local protocol.</p></div></main><div class='quick'><div class='quickin'><div class='q'><span>TFL</span><b id='quickTfl'>0</b></div><div class='q'><span>PN Rate</span><b id='quickPn'>0</b></div><div class='q'><span>GIR</span><b id='quickGir'>0</b></div><button class='btn primary save'>Save</button></div></div></form><script>
function n(x){let v=parseFloat(document.querySelector(`[name="${x}"]`)?.value||0);return isFinite(v)?v:0}function s(i,v){let e=document.getElementById(i);if(e)e.textContent=v}function rr(v,p=2){return (Math.round((v+Number.EPSILON)*10**p)/10**p).toFixed(p)}function calc(){let wt=n('dosing_weight_kg'),tfl=n('tfl_ml_per_kg_day'),iv=n('ivfe_dose_g_kg_day'),td=tfl*wt,th=wt>0?td/24:0,ig=iv*wt,imd=ig*5,ih=wt>0?imd/24:0,bh=n('non_pn_bolus_meds_ml_day')/24,non=ih+n('non_pn_art_line_ml_hr')+n('non_pn_uvc_ml_hr')+n('non_pn_picc_ml_hr')+n('non_pn_continuous_meds_ml_hr')+bh,pn=th-non,pg=n('protein_g_kg_day')*wt,pk=pg*4,dex=n('dextrose_percent'),tg=wt>0?(dex*pn*.167)/wt:0,rg=wt>0?(n('rider_dextrose_percent')*n('rider_rate_ml_hr')*.167)/wt:0,total=tg+rg;s('tflDay',rr(td));s('tflHr',rr(th,1));s('ivfeGDay',rr(ig));s('ivfeMlDay',rr(imd));s('ivfeHr',rr(ih));s('bolusHr',rr(bh));s('nonPnTotal',rr(non));s('pnRate',rr(pn,1));s('pnRange',`0–${rr(pn,1)} mL/hr`);s('proteinGDay',rr(pg));s('proteinKcal',rr(pk));s('tpnGir',rr(tg));s('riderGir',rr(rg));s('totalGir',rr(total));s('quickTfl',rr(th,1)+' mL/hr');s('quickPn',rr(pn,1)+' mL/hr');s('quickGir',rr(total));let w=[];let access=document.querySelector('[name="access_type"]').value;if(wt<=0)w.push('Dosing weight is required.');if(pn<0)w.push('Non-PN fluids exceed TFL.');if(access==='Peripheral'&&dex>12.5)w.push('Peripheral max is D12.5.');if(wt>0&&dex>0&&total<4)w.push('Total GIR should generally not be <4 mg/kg/min in ELBW infants when NPO/trophic feeds.');if(total>14)w.push('Avoid GIR >14 unless needed for hypoglycemia.');document.getElementById('warnings').innerHTML=w.map(x=>`<div class="warn">${x}</div>`).join('')}document.querySelectorAll('[data-calc]').forEach(e=>{e.oninput=calc;e.onchange=calc});calc();</script>"""+END
SUM=BASE+TOP+"""<main class='wrap'><div class='card'><h1>{{row.session_name}}</h1><p class='muted'>{{row.calculation_date}} · Dosing Weight: {{row.dosing_weight_kg}} kg</p><div class='btns'><a class='btn soft' href='{{url_for("edit_session",sid=row.id)}}'>Edit</a><button class='btn soft' onclick='print()'>Print</button><form method='post' action='{{url_for("duplicate",sid=row.id)}}'><input type='hidden' name='csrf_token' value='{{csrf_token}}'><button class='btn soft'>Duplicate</button></form><form method='post' action='{{url_for("delete",sid=row.id)}}' onsubmit='return confirm("Delete this session?")'><input type='hidden' name='csrf_token' value='{{csrf_token}}'><button class='btn danger'>Delete</button></form></div></div>{% if c.warnings %}<div class='card'><h2>Warnings</h2>{% for w in c.warnings %}<div class='warn'>{{w}}</div>{% endfor %}</div>{% endif %}<div class='card'><h2>TFL</h2><div class='result'><span>{{row.tfl_ml_per_kg_day}} × {{row.dosing_weight_kg}}</span><b>{{c.values.tfl_ml_day}} mL/day</b></div><div class='result'><span>{{c.values.tfl_ml_day}} ÷ 24</span><b>{{c.values.tfl_ml_hr}} mL/hr</b></div></div><div class='card'><h2>IVFE</h2><div class='result'><span>{{row.ivfe_dose_g_kg_day}} × {{row.dosing_weight_kg}}</span><b>{{c.values.ivfe_g_day}} g/day</b></div><div class='result'><span>{{c.values.ivfe_g_day}} × 5</span><b>{{c.values.ivfe_ml_day}} mL/day</b></div><div class='result'><span>{{c.values.ivfe_ml_day}} ÷ 24</span><b>{{c.values.ivfe_ml_hr}} mL/hr</b></div></div><div class='card'><h2>PN Rate</h2><div class='result'><span>Total non-PN</span><b>{{c.values.total_non_pn_ml_hr}} mL/hr</b></div><div class='result'><span>TFL - non-PN</span><b>{{c.values.pn_rate_ml_hr}} mL/hr</b></div><div class='result'><span>Order range</span><b>0–{{c.values.pn_rate_ml_hr}} mL/hr</b></div></div><div class='card'><h2>Protein</h2><div class='result'><span>{{row.protein_g_kg_day}} × {{row.dosing_weight_kg}}</span><b>{{c.values.protein_g_day}} g/day</b></div><div class='result'><span>{{c.values.protein_g_day}} × 4</span><b>{{c.values.protein_kcal_day}} kcal/day</b></div></div><div class='card'><h2>GIR</h2><div class='result'><span>TPN GIR</span><b>{{c.values.tpn_gir}}</b></div><div class='result'><span>Rider GIR</span><b>{{c.values.rider_gir}}</b></div><div class='result'><span>Total GIR</span><b>{{c.values.total_gir}} mg/kg/min</b></div></div>{% if row.notes %}<div class='card'><h2>Notes</h2><p>{{row.notes}}</p></div>{% endif %}</main>"""+END

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        if not csrf_ok(): abort(400)
        if pw_ok(request.form.get('password','')):
            session.clear(); session['authenticated']=True; session['csrf_token']=secrets.token_urlsafe(32); return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Incorrect password.')
    return render_template_string(LOGIN, csrf_token=csrf())
@app.route('/logout', methods=['POST'])
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/')
@need_login
def dashboard():
    with db() as con: rows=con.execute('SELECT * FROM sessions ORDER BY updated_at DESC').fetchall()
    return render_template_string(DASH, rows=rows, csrf_token=csrf())
@app.route('/session/new', methods=['GET','POST'])
@need_login
def new_session():
    d=blank()
    if request.method=='POST':
        if not csrf_ok(): abort(400)
        d=form_data()
        if not d['session_name']: flash('Session Name is required.')
        else:
            c=calculate(d); ts=now(); vals=tuple(d[x] for x in FIELDS)+(json.dumps(c),ts,ts)
            with db() as con:
                cur=con.execute('INSERT INTO sessions('+','.join(FIELDS)+',calculated_json,created_at,updated_at) VALUES ('+','.join(['?']*(len(FIELDS)+3))+')', vals); con.commit()
            return redirect(url_for('summary', sid=cur.lastrowid))
    return render_template_string(FORM,d=d,csrf_token=csrf())
@app.route('/session/<int:sid>')
@need_login
def summary(sid):
    row=get_row(sid); return render_template_string(SUM,row=row,c=calculate(dict(row)),csrf_token=csrf())
@app.route('/session/<int:sid>/edit', methods=['GET','POST'])
@need_login
def edit_session(sid):
    row=get_row(sid); d=dict(row)
    if request.method=='POST':
        if not csrf_ok(): abort(400)
        d=form_data()
        if not d['session_name']: flash('Session Name is required.')
        else:
            c=calculate(d); vals=tuple(d[x] for x in FIELDS)+(json.dumps(c),now(),sid)
            with db() as con: con.execute('UPDATE sessions SET '+','.join([x+'=?' for x in FIELDS])+',calculated_json=?,updated_at=? WHERE id=?', vals); con.commit()
            return redirect(url_for('summary',sid=sid))
    return render_template_string(FORM,d=d,csrf_token=csrf())
@app.route('/session/<int:sid>/duplicate', methods=['POST'])
@need_login
def duplicate(sid):
    if not csrf_ok(): abort(400)
    d=dict(get_row(sid)); d['session_name']='Copy of '+d['session_name']; d['calculation_date']=date.today().isoformat(); c=calculate(d); ts=now(); vals=tuple(d[x] for x in FIELDS)+(json.dumps(c),ts,ts)
    with db() as con: cur=con.execute('INSERT INTO sessions('+','.join(FIELDS)+',calculated_json,created_at,updated_at) VALUES ('+','.join(['?']*(len(FIELDS)+3))+')', vals); con.commit()
    return redirect(url_for('edit_session',sid=cur.lastrowid))
@app.route('/session/<int:sid>/delete', methods=['POST'])
@need_login
def delete(sid):
    if not csrf_ok(): abort(400)
    with db() as con: con.execute('DELETE FROM sessions WHERE id=?',(sid,)); con.commit()
    return redirect(url_for('dashboard'))
if __name__=='__main__': app.run(debug=True)
