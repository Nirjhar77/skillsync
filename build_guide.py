html = r"""{% extends "base.html" %}
{% block title %}{{ career.title }} Visual Guide — SkillSync{% endblock %}
{% block content %}
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&display=swap');
.app-content{padding:0!important;}
.guide-wrap{display:flex;flex-direction:column;height:calc(100vh - 60px);overflow:hidden;}

/* ── Tabs ─────────────────────────────────────────── */
.guide-tabs{display:flex;gap:.4rem;padding:.7rem 1.4rem .5rem;border-bottom:1px solid var(--border);flex-shrink:0;}
.guide-tab{flex:1;text-align:center;padding:.5rem 1rem;border-radius:9px;font-size:.84rem;font-weight:700;cursor:pointer;text-decoration:none;transition:all .2s;color:var(--text-muted);border:1px solid transparent;}
.guide-tab:hover{background:rgba(255,255,255,.06);color:var(--text-primary);}
.guide-tab.active{background:rgba(0,212,255,.1);color:#00d4ff;border-color:rgba(0,212,255,.25);}

/* ── Split body ───────────────────────────────────── */
.guide-body{display:flex;flex:1;overflow:hidden;min-height:0;}

/* ── Left graph panel ─────────────────────────────── */
.guide-graph{flex:1;overflow-y:auto;overflow-x:hidden;padding:2rem 2.5rem 4rem;min-width:0;}
.guide-graph::-webkit-scrollbar{width:4px;}
.guide-graph::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1);border-radius:4px;}
.guide-header{text-align:center;margin-bottom:3rem;}
.guide-title{font-family:'Outfit',sans-serif;font-size:1.9rem;font-weight:900;margin-bottom:.7rem;background:linear-gradient(135deg,#fff 40%,#00d4ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.guide-desc{font-size:.9rem;color:var(--text-secondary);max-width:560px;margin:0 auto;line-height:1.65;}

/* ── Roadmap graph ────────────────────────────────── */
.rg-wrap{position:relative;display:flex;flex-direction:column;align-items:center;max-width:760px;margin:0 auto;}
.rg-svg{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;overflow:visible;}

/* Spine connector (vertical bar between sections) */
.rg-connector{width:4px;height:36px;border-radius:4px;margin:0 auto;position:relative;z-index:1;}

/* Section header node */
.rg-main-node{
  position:relative;z-index:2;text-align:center;padding:.6rem 1.6rem;
  border-radius:10px;font-family:'Outfit',sans-serif;font-size:.8rem;
  font-weight:900;letter-spacing:.08em;text-transform:uppercase;
  cursor:default;transition:transform .2s;white-space:nowrap;
  box-shadow:0 4px 20px rgba(0,0,0,.3);margin:.2rem 0;
}
.rg-main-node:hover{transform:scale(1.03);}

/* Topics section (below each section header) */
.rg-topics{width:100%;display:flex;flex-direction:column;gap:.55rem;margin:.6rem 0;position:relative;z-index:2;}

/* Each row: left topic | 44px spine column | right topic */
.rg-row{display:grid;grid-template-columns:1fr 44px 1fr;align-items:center;gap:.3rem;width:100%;}
.rg-side-l{display:flex;justify-content:flex-end;}
.rg-side-r{display:flex;justify-content:flex-start;}
.rg-spine-mid{height:100%;display:flex;align-items:center;justify-content:center;position:relative;}

/* Topic node */
.rg-topic{
  padding:.42rem .85rem;border-radius:8px;font-size:.79rem;font-weight:600;
  cursor:pointer;transition:all .2s;border:1px solid rgba(255,255,255,.1);
  background:rgba(255,255,255,.04);color:var(--text-secondary);
  max-width:210px;text-align:center;line-height:1.3;position:relative;
}
.rg-topic:hover{transform:translateY(-1px);color:var(--text-primary);}
.rg-topic.selected{color:var(--text-primary);}
.rg-topic.critical{border-left-width:3px;}
.rg-topic.good_to_know{border-style:dashed;opacity:.72;}
.rg-opt{font-size:.6rem;font-weight:700;padding:.08rem .35rem;border-radius:3px;background:rgba(148,163,184,.15);color:#94a3b8;margin-left:.3rem;vertical-align:middle;}

/* ── Right AI panel ───────────────────────────────── */
.guide-panel{width:380px;min-width:0;background:var(--bg-secondary);border-left:1px solid var(--border);display:flex;flex-direction:column;transition:width .3s,min-width .3s;overflow:hidden;flex-shrink:0;}
.guide-panel.closed{width:0;border:none;}
.p-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:1rem;color:var(--text-muted);text-align:center;padding:2rem;}
.p-empty-icon{font-size:2.8rem;opacity:.5;}

/* Panel header */
.p-head{padding:1.1rem 1.3rem .8rem;border-bottom:1px solid var(--border);flex-shrink:0;}
.p-head-row{display:flex;align-items:start;justify-content:space-between;gap:.5rem;margin-bottom:.5rem;}
.p-title{font-family:'Outfit',sans-serif;font-size:1.1rem;font-weight:800;color:var(--text-primary);line-height:1.25;}
.p-close{background:none;border:none;cursor:pointer;color:var(--text-muted);padding:.2rem;border-radius:6px;display:flex;flex-shrink:0;margin-top:2px;}
.p-close:hover{background:rgba(255,255,255,.08);color:var(--text-primary);}
.p-meta{display:flex;gap:.4rem;flex-wrap:wrap;}
.p-badge{font-size:.68rem;font-weight:700;padding:.18rem .6rem;border-radius:20px;}
.p-time{font-size:.72rem;font-weight:700;padding:.18rem .7rem;border-radius:20px;background:rgba(52,211,153,.1);color:#34d399;border:1px solid rgba(52,211,153,.2);}

/* Panel body */
.p-body{flex:1;overflow-y:auto;padding:1.1rem 1.3rem;display:flex;flex-direction:column;gap:1rem;}
.p-body::-webkit-scrollbar{width:3px;}
.p-body::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1);border-radius:3px;}
.p-sec-label{font-size:.66rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--text-muted);margin-bottom:.35rem;display:flex;align-items:center;gap:.35rem;}
.p-text{font-size:.84rem;color:var(--text-secondary);line-height:1.65;}
.p-steps{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:.45rem;}
.p-steps li{font-size:.82rem;color:var(--text-secondary);display:flex;gap:.55rem;line-height:1.5;}
.p-step-n{background:rgba(124,111,255,.2);color:#a78bfa;border-radius:50%;width:19px;height:19px;display:inline-flex;align-items:center;justify-content:center;font-size:.68rem;font-weight:800;flex-shrink:0;margin-top:2px;}
.p-res-list{display:flex;flex-direction:column;gap:.45rem;}
.p-res{display:flex;align-items:center;gap:.55rem;text-decoration:none;padding:.45rem .65rem;border-radius:8px;border:1px solid var(--border);background:rgba(255,255,255,.03);transition:all .2s;}
.p-res:hover{background:rgba(255,255,255,.06);border-color:rgba(124,111,255,.3);}
.p-res-icon{width:26px;height:26px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:.78rem;flex-shrink:0;}
.ri-yt{background:rgba(239,68,68,.2);} .ri-co{background:rgba(139,92,246,.2);} .ri-ar{background:rgba(148,163,184,.12);} .ri-do{background:rgba(0,212,255,.12);}
.p-res-name{font-size:.79rem;font-weight:600;color:var(--text-primary);}
.p-res-type{font-size:.67rem;color:var(--text-muted);text-transform:capitalize;}
.p-mistakes{display:flex;flex-direction:column;gap:.4rem;}
.p-mistake{font-size:.81rem;color:var(--text-secondary);padding:.4rem .6rem;border-radius:7px;background:rgba(251,191,36,.05);border:1px solid rgba(251,191,36,.15);display:flex;gap:.5rem;}
.p-mistake::before{content:'⚠';font-size:.75rem;flex-shrink:0;margin-top:1px;}

/* Skeleton */
.skeleton{animation:sk 1.5s ease-in-out infinite;}
@keyframes sk{0%,100%{opacity:.35;}50%{opacity:.75;}}
.sk-line{height:11px;background:rgba(255,255,255,.08);border-radius:5px;margin-bottom:8px;}

/* Gen button */
.gen-wrap{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:1.1rem;text-align:center;padding:2rem;}
.gen-btn{background:linear-gradient(135deg,#00d4ff,#0ea5e9);color:#000;border:none;border-radius:12px;padding:.8rem 2rem;font-size:.95rem;font-weight:800;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:.5rem;}
.gen-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,212,255,.35);}
.gen-btn:disabled{opacity:.6;cursor:wait;transform:none;}
</style>

<div class="guide-wrap">
  <div class="guide-tabs">
    <a href="{{ url_for('career.roadmap_view', roadmap_id=roadmap.id) }}" class="guide-tab">🗺 Start Journey</a>
    <span class="guide-tab active">🧭 Visual Guide</span>
  </div>

  <div class="guide-body">
    <!-- ── LEFT: graph ──────────────────────────── -->
    <div class="guide-graph" id="guide-graph">

      {% if needs_generation %}
      <div class="gen-wrap">
        <div style="font-size:2.5rem">🗺</div>
        <div style="font-size:1.1rem;font-weight:700;color:var(--text-primary)">Visual Guide Not Generated Yet</div>
        <div style="font-size:.87rem;color:var(--text-muted);max-width:340px;line-height:1.6">
          Click below to build the interactive knowledge map for this career path.
        </div>
        <button class="gen-btn" id="gen-btn" onclick="buildGuide()">
          <i data-lucide="zap" style="width:15px;height:15px"></i> Build Visual Guide
        </button>
        <div id="gen-status" style="font-size:.82rem;color:var(--text-muted);display:none;margin-top:.3rem"></div>
      </div>

      {% else %}
      <div class="guide-header">
        <div class="guide-title">{{ guide_data.get('title', career.title) }}</div>
        <p class="guide-desc">{{ guide_data.get('description','') }}</p>
      </div>

      <div class="rg-wrap" id="rg-wrap">
        <svg class="rg-svg" id="rg-svg"></svg>

        {% for section in guide_data.get('sections',[]) %}
        {% set ph = section.get('phase', loop.index) | int %}
        {% set topics = section.get('topics',[]) %}

        {% if not loop.first %}
        <div class="rg-connector" data-phase="{{ ph }}"></div>
        {% endif %}

        <div class="rg-main-node" data-phase="{{ ph }}" id="sn-{{ section.get('id','s'~loop.index) }}">
          {{ section.get('label','') }}
        </div>

        <div class="rg-topics" data-phase="{{ ph }}" data-section="{{ section.get('label','') }}">
          {% for pair in topics | batch(2, none) %}
          {% set tl = pair[0] %}
          {% set tr = pair[1] %}
          <div class="rg-row">
            <div class="rg-side-l">
              {% if tl %}
              <div class="rg-topic {{ tl.get('importance','important') }}"
                   data-id="{{ tl.get('id','') }}"
                   data-label="{{ tl.get('label','') }}"
                   data-section="{{ section.get('label','') }}"
                   data-phase="{{ ph }}"
                   onclick="pickTopic(this)">
                {{ tl.get('label','') }}{% if tl.get('type')=='optional' %}<span class="rg-opt">opt</span>{% endif %}
              </div>
              {% endif %}
            </div>
            <div class="rg-spine-mid"></div>
            <div class="rg-side-r">
              {% if tr %}
              <div class="rg-topic {{ tr.get('importance','important') }}"
                   data-id="{{ tr.get('id','') }}"
                   data-label="{{ tr.get('label','') }}"
                   data-section="{{ section.get('label','') }}"
                   data-phase="{{ ph }}"
                   onclick="pickTopic(this)">
                {{ tr.get('label','') }}{% if tr.get('type')=='optional' %}<span class="rg-opt">opt</span>{% endif %}
              </div>
              {% endif %}
            </div>
          </div>
          {% endfor %}
        </div>
        {% endfor %}
      </div>
      {% endif %}
    </div>

    <!-- ── RIGHT: AI panel ──────────────────────── -->
    <div class="guide-panel closed" id="guide-panel">
      <div class="p-empty" id="p-empty">
        <div class="p-empty-icon">💡</div>
        <div style="font-size:.88rem;line-height:1.55">Click any topic to get a live AI explanation.</div>
      </div>
      <div id="p-loading" style="display:none;padding:1.3rem">
        <div class="skeleton">
          <div class="sk-line" style="width:70%;height:16px;margin-bottom:14px"></div>
          <div class="sk-line" style="width:40%;margin-bottom:22px"></div>
          <div class="sk-line" style="width:90%"></div><div class="sk-line" style="width:80%"></div><div class="sk-line" style="width:65%;margin-bottom:18px"></div>
          <div class="sk-line" style="width:90%"></div><div class="sk-line" style="width:75%"></div><div class="sk-line" style="width:85%"></div>
        </div>
      </div>
      <div id="p-content" style="display:none;flex-direction:column;height:100%;overflow:hidden;">
        <div class="p-head">
          <div class="p-head-row">
            <div class="p-title" id="p-title">Topic</div>
            <button class="p-close" onclick="closePanel()"><i data-lucide="x" style="width:15px;height:15px"></i></button>
          </div>
          <div class="p-meta" id="p-meta"></div>
        </div>
        <div class="p-body" id="p-body"></div>
      </div>
    </div>
  </div>
</div>

<script>
const ROADMAP_ID = {{ roadmap.id }};
const CAREER = "{{ career.title | e }}";
const cache  = {};

const PC = {
  1:{c:'#818cf8',r:'129,140,248'},
  2:{c:'#00d4ff',r:'0,212,255'},
  3:{c:'#34d399',r:'52,211,153'},
  4:{c:'#fbbf24',r:'251,191,36'},
  5:{c:'#ec4899',r:'236,72,153'},
};
function ph2c(ph){ return PC[parseInt(ph)] || PC[1]; }

function styleNodes(){
  document.querySelectorAll('.rg-main-node').forEach(n=>{
    const {c} = ph2c(n.dataset.phase);
    n.style.background=`linear-gradient(135deg,${c}1a,${c}0d)`;
    n.style.border=`2px solid ${c}55`;
    n.style.color=c;
  });
  document.querySelectorAll('.rg-connector').forEach(n=>{
    const {c} = ph2c(n.dataset.phase);
    n.style.background=`linear-gradient(to bottom,${c}55,${c}33)`;
  });
  document.querySelectorAll('.rg-topic').forEach(n=>{
    const {c,r} = ph2c(n.dataset.phase);
    n.style.setProperty('--tc',c);
    n.style.setProperty('--tr',r);
    if(n.classList.contains('critical')) n.style.borderLeftColor=c;
    n.style.cssText+=`;--hover-shadow:0 0 14px rgba(${r},.25);`;
  });
  document.querySelectorAll('.rg-topic').forEach(n=>{
    n.addEventListener('mouseenter',()=>{ n.style.borderColor=n.style.getPropertyValue('--tc'); n.style.boxShadow=`0 0 14px rgba(${n.style.getPropertyValue('--tr')},.22)`; });
    n.addEventListener('mouseleave',()=>{ if(!n.classList.contains('selected')){ n.style.borderColor=''; n.style.boxShadow=''; } });
  });
}

function drawLines(){
  const wrap = document.getElementById('rg-wrap');
  const svg  = document.getElementById('rg-svg');
  if(!wrap||!svg) return;
  svg.innerHTML='';
  const wr = wrap.getBoundingClientRect();
  const spineX = wr.width/2;
  const graph = document.getElementById('guide-graph');
  const scrollTop = graph.scrollTop;

  document.querySelectorAll('.rg-topics').forEach(ts=>{
    const ph = ts.dataset.phase||1;
    const {c} = ph2c(ph);
    // Find matching main node (previous sibling)
    let mn = ts.previousElementSibling;
    while(mn && !mn.classList.contains('rg-main-node')) mn=mn.previousElementSibling;
    let mnCY = 0;
    if(mn){
      const mr = mn.getBoundingClientRect();
      mnCY = mr.top - wr.top + mr.height/2 + scrollTop;
    }

    ts.querySelectorAll('.rg-row').forEach(row=>{
      const rr = row.getBoundingClientRect();
      const rowMidY = rr.top - wr.top + rr.height/2 + scrollTop;

      // Vertical spine line from main node center to this row
      if(mn){
        const vl = document.createElementNS('http://www.w3.org/2000/svg','line');
        vl.setAttribute('x1',spineX); vl.setAttribute('y1',mnCY);
        vl.setAttribute('x2',spineX); vl.setAttribute('y2',rowMidY);
        vl.setAttribute('stroke',c); vl.setAttribute('stroke-width','2.5');
        vl.setAttribute('opacity','0.4'); svg.appendChild(vl);
      }

      // Horizontal lines: left topic → spine, spine → right topic
      row.querySelectorAll('.rg-side-l .rg-topic').forEach(t=>{
        const tr = t.getBoundingClientRect();
        const tx = tr.right - wr.left;
        const ty = tr.top - wr.top + tr.height/2 + scrollTop;
        const hl = document.createElementNS('http://www.w3.org/2000/svg','line');
        hl.setAttribute('x1',tx); hl.setAttribute('y1',ty);
        hl.setAttribute('x2',spineX); hl.setAttribute('y2',ty);
        hl.setAttribute('stroke',c); hl.setAttribute('stroke-width','1.5');
        hl.setAttribute('stroke-dasharray','5 4'); hl.setAttribute('opacity','0.45');
        svg.appendChild(hl);
        // Dot on spine
        const dot = document.createElementNS('http://www.w3.org/2000/svg','circle');
        dot.setAttribute('cx',spineX); dot.setAttribute('cy',ty);
        dot.setAttribute('r','4'); dot.setAttribute('fill',c); dot.setAttribute('opacity','0.6');
        svg.appendChild(dot);
      });
      row.querySelectorAll('.rg-side-r .rg-topic').forEach(t=>{
        const tr = t.getBoundingClientRect();
        const tx = tr.left - wr.left;
        const ty = tr.top - wr.top + tr.height/2 + scrollTop;
        const hl = document.createElementNS('http://www.w3.org/2000/svg','line');
        hl.setAttribute('x1',spineX); hl.setAttribute('y1',ty);
        hl.setAttribute('x2',tx); hl.setAttribute('y2',ty);
        hl.setAttribute('stroke',c); hl.setAttribute('stroke-width','1.5');
        hl.setAttribute('stroke-dasharray','5 4'); hl.setAttribute('opacity','0.45');
        svg.appendChild(hl);
        const dot = document.createElementNS('http://www.w3.org/2000/svg','circle');
        dot.setAttribute('cx',spineX); dot.setAttribute('cy',ty);
        dot.setAttribute('r','4'); dot.setAttribute('fill',c); dot.setAttribute('opacity','0.6');
        svg.appendChild(dot);
      });
    });
  });
}

async function pickTopic(el){
  document.querySelectorAll('.rg-topic').forEach(t=>{
    t.classList.remove('selected');
    t.style.borderColor=''; t.style.boxShadow='';
  });
  el.classList.add('selected');
  const {c,r} = ph2c(el.dataset.phase);
  el.style.borderColor=c; el.style.boxShadow=`0 0 16px rgba(${r},.3)`;

  const id=el.dataset.id, label=el.dataset.label, section=el.dataset.section, ph=el.dataset.phase;
  openPanel(); showLoading();
  document.getElementById('p-title').textContent=label;
  document.getElementById('p-meta').innerHTML=
    `<span class="p-badge" style="background:rgba(${ph2c(ph).r},.12);color:${ph2c(ph).c};border:1px solid rgba(${ph2c(ph).r},.25);">${section}</span>`;

  if(cache[id]){ renderPanel(cache[id],ph); return; }
  try{
    const res=await fetch(`/career/roadmap/${ROADMAP_ID}/explain-topic`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({topic:label,section,career:CAREER})
    });
    const d=await res.json();
    if(d.error) throw new Error(d.error);
    cache[id]=d; renderPanel(d,ph);
  }catch(e){ showErr(e.message); }
}

function openPanel(){ document.getElementById('guide-panel').classList.remove('closed'); }
function closePanel(){
  document.getElementById('guide-panel').classList.add('closed');
  document.querySelectorAll('.rg-topic').forEach(t=>{t.classList.remove('selected');t.style.borderColor='';t.style.boxShadow='';});
}
function showLoading(){
  document.getElementById('p-empty').style.display='none';
  document.getElementById('p-content').style.display='none';
  document.getElementById('p-loading').style.display='block';
}
function showErr(msg){
  document.getElementById('p-loading').style.display='none';
  document.getElementById('p-content').style.display='flex';
  document.getElementById('p-body').innerHTML=`<div style="color:#ef4444;font-size:.84rem">&#9888; ${msg||'Failed to load.'}</div>`;
}
function renderPanel(d,ph){
  document.getElementById('p-loading').style.display='none';
  const {c,r}=ph2c(ph);
  const meta=document.getElementById('p-meta');
  if(d.estimated_time) meta.innerHTML+=`<span class="p-time">&#128337; ${d.estimated_time}</span>`;
  const pc=document.getElementById('p-content');
  pc.style.display='flex';
  const ri={youtube:'&#9654;',course:'&#127891;',article:'&#128196;',docs:'&#128196;'};
  const rc={youtube:'ri-yt',course:'ri-co',article:'ri-ar',docs:'ri-do'};
  let h='';
  if(d.overview) h+=`<div><div class="p-sec-label">&#128218; Overview</div><p class="p-text">${d.overview}</p></div>`;
  if(d.why_it_matters) h+=`<div><div class="p-sec-label" style="color:${c}">&#9889; Why It Matters</div><p class="p-text">${d.why_it_matters}</p></div>`;
  if(d.how_to_learn?.length){
    const steps=d.how_to_learn.map((s,i)=>`<li><span class="p-step-n">${i+1}</span><span>${s}</span></li>`).join('');
    h+=`<div><div class="p-sec-label">&#127891; How to Learn</div><ul class="p-steps">${steps}</ul></div>`;
  }
  if(d.resources?.length){
    const items=d.resources.map(r=>`<a href="${r.url||'#'}" target="_blank" rel="noopener" class="p-res"><div class="p-res-icon ${rc[r.type]||'ri-ar'}">${ri[r.type]||'&#128196;'}</div><div><div class="p-res-name">${r.title}</div><div class="p-res-type">${r.type||'resource'}</div></div></a>`).join('');
    h+=`<div><div class="p-sec-label">&#128279; Free Resources</div><div class="p-res-list">${items}</div></div>`;
  }
  if(d.common_mistakes?.length){
    const ms=d.common_mistakes.map(m=>`<div class="p-mistake">${m}</div>`).join('');
    h+=`<div><div class="p-sec-label">&#9888; Common Mistakes</div><div class="p-mistakes">${ms}</div></div>`;
  }
  document.getElementById('p-body').innerHTML=h;
}

async function buildGuide(){
  const btn=document.getElementById('gen-btn');
  const st=document.getElementById('gen-status');
  btn.disabled=true; st.style.display='block';
  st.textContent='Generating knowledge map... (~8 seconds)';
  try{
    const r=await fetch(`/career/roadmap/${ROADMAP_ID}/guide/generate`,{method:'POST'});
    const d=await r.json();
    if(d.success) window.location.reload();
    else st.textContent='Error: '+(d.error||'Failed');
  }catch(e){ st.textContent='Network error. Please retry.'; btn.disabled=false; }
}

window.addEventListener('load',()=>{
  styleNodes();
  setTimeout(drawLines,200);
  lucide.createIcons();
});
window.addEventListener('resize',drawLines);
document.getElementById('guide-graph')?.addEventListener('scroll',drawLines);
</script>
{% endblock %}
"""
with open('templates/career/guide.html','w',encoding='utf-8') as f:
    f.write(html)
print('guide.html rewritten:',len(html.splitlines()),'lines')
