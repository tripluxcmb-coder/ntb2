'use strict';

const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = value => Number(value ?? 0).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:Math.abs(Number(value))>0 && Math.abs(Number(value))<.01?8:2});
const sign = value => value === null ? '—' : `${value > 0 ? '+' : value < 0 ? '−' : ''}${fmt(Math.abs(value))}`;
const state = {customers:[], current:null, data:null, seq:0, movement:'mom', productCategory:'assets', productId:null, request:null};
const symbols = {
  assets:'<path d="M4 18V9l4-3 4 3 5-5M14 4h3v3M3 21h18M7 13v4M12 12v5M17 10v7"/>',
  liabilities:'<path d="m3 8 9-5 9 5M4 9h16M6 10v8M10 10v8M14 10v8M18 10v8M3 21h18M4 18h16"/>',
  contingent:'<path d="m12 3 8 3v5c0 5-4 8-8 10-4-2-8-5-8-10V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  payments:'<path d="M4 7h14M14 3l4 4-4 4M20 17H6M10 13l-4 4 4 4"/>'
};
const svg = body => `<svg viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;

function notice(message='') {
  $('notice').hidden = !message;
  $('notice').textContent = message;
}

async function jsonRequest(path, options={}) {
  const response = await fetch(path, {cache:'no-store', ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The customer view could not be refreshed.');
  return data;
}

function customerOptions(query='') {
  const matches = state.customers.filter(c => !query || c.cif.toLowerCase().startsWith(query.toLowerCase()));
  const placeholder = !matches.some(c => c.cif === state.current) ? '<option value="">Select a matching company</option>' : '';
  $('company-select').innerHTML = placeholder + matches.map(c => `<option value="${esc(c.cif)}">${esc(c.name)}</option>`).join('');
  if (matches.some(c => c.cif === state.current)) $('company-select').value = state.current;
  return matches;
}

async function loadCustomer(cif, {quiet=false}={}) {
  if (!cif) return;
  const seq = ++state.seq;
  if (state.request) state.request.abort();
  state.request = new AbortController();
  if (!quiet) $('dashboard').setAttribute('aria-busy','true');
  try {
    const data = await jsonRequest(`/api/customer/${encodeURIComponent(cif)}`, {signal:state.request.signal});
    if (seq !== state.seq) return;
    if (state.current !== cif) state.productId = null;
    state.current = cif;
    state.data = data;
    customerOptions($('cif-input').value.trim());
    renderDashboard(data);
    notice();
    $('dashboard').setAttribute('aria-busy','false');
    if (data.ai_available && data.priorities.origin !== 'ai') improvePriorities(seq, data.version, false);
  } catch(error) {
    if (error.name !== 'AbortError' && seq === state.seq) {
      notice(error.message);
      $('dashboard').setAttribute('aria-busy','false');
    }
  }
}

function renderDashboard(data) {
  const p = data.profile, c = data.company;
  $('company-name').textContent = c.display_name;
  $('company-cif').textContent = p.cif;
  $('company-mark').textContent = c.display_name.split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase();
  $('industry-chip').textContent = c.industry_label || 'Corporate banking';
  $('asof-top').textContent = p.reporting_label;
  $('unit-caption').textContent = `All amounts in ${p.unit}`;
  $('chart-unit').textContent = p.unit;
  $('company-description').textContent = c.description;
  $('company-links').innerHTML = c.links.map(link=>`<a class="source-link" href="${esc(link.url)}" target="_blank" rel="noopener noreferrer">${svg('<path d="M14 3h7v7M21 3 11 13M10 5H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/>')}${esc(link.label)}</a>`).join('');
  $('active-products').textContent = p.active_products;
  $('funding-role').textContent = p.funding_role.toUpperCase();
  $('net-funding').textContent = fmt(p.net_funding_mn);
  $('relationship-asof').textContent = p.reporting_label;
  const subtitles = {assets:'Funded lending & advances',liabilities:'Deposits & customer credit balances',contingent:'Guarantees & documentary credits',payments:'Remittances, shown separately'};
  $('metrics').innerHTML = ['assets','liabilities','contingent','payments'].map(key=>{
    const m = p.metrics[key];
    return `<article class="metric-card ${key}" data-category="${key}"><div class="metric-top"><span class="metric-name">${esc(m.title)}</span><span class="metric-icon">${svg(symbols[key])}</span></div><div class="metric-number" data-value="${key}">${esc(m.display)}<small>Mn</small></div><div class="metric-subtitle">${subtitles[key]}</div><div class="metric-movements"><div><small>MONTHLY · Mn</small><strong>${esc(m.mom.display)}</strong></div><div><small>YTD · Mn</small><strong>${esc(m.ytd.display)}</strong></div></div></article>`;
  }).join('');
  $('download-brief').href = `/brief/${encodeURIComponent(p.cif)}?download=1`;
  renderPriorities(data.priorities);
  drawCharts();
}

function renderPriorities(priorities) {
  const p = state.data.profile;
  const lookup = Object.fromEntries(p.facts.map(f=>[f.id,f]));
  $('visit-objective').textContent = priorities.objective;
  $('ai-status').textContent = priorities.origin === 'ai' ? 'AI-informed priorities' : 'Relationship priorities';
  $('ai-status').className = 'ai-pill' + (priorities.origin==='ai'?' ai':'');
  $('ai-refresh').disabled = false;
  $('recommendations').innerHTML = priorities.recommendations.map((r,i)=>{
    const evidence = r.evidence_ids.filter(id=>lookup[id]).slice(0,2).map(id=>{
      const f = lookup[id];
      return `${f.title}: ${f.display} Mn · YTD ${sign(f.ytd.amount_mn)} Mn`;
    }).join('<br>');
    // All evidence fragments are escaped, including dynamic labels.
    const safeEvidence = evidence.split('<br>').map(esc).join('<br>');
    return `<article class="recommendation"><div class="rec-head"><span class="rec-number">${String(i+1).padStart(2,'0')}</span><span class="rec-action">${esc(r.action)}</span></div><h3>${esc(r.name)}</h3><p class="why">${esc(r.why_now)}</p><div class="rec-evidence"><b>RELATIONSHIP EVIDENCE</b>${safeEvidence}</div><div class="rec-question"><small>ASK DURING THE VISIT</small><p>${esc(r.question)}</p></div><details><summary>Considerations before an offer</summary><ul>${r.checks.map(check=>`<li>${esc(check)}</li>`).join('')}</ul></details></article>`;
  }).join('');
}

async function improvePriorities(seq, version, refresh) {
  const cif = state.current;
  $('ai-status').textContent = 'Preparing priorities…';
  $('ai-status').className = 'ai-pill loading';
  $('ai-refresh').disabled = true;
  try {
    const result = await jsonRequest(`/api/customer/${encodeURIComponent(cif)}/recommendations`, {
      method:'POST', headers:{'Content-Type':'application/json','X-Requested-With':'RelationshipDashboard'},
      body:JSON.stringify({version, refresh})
    });
    if (seq === state.seq && state.data?.version === version && state.current === cif) {
      state.data.priorities = result;
      renderPriorities(result);
    }
  } catch(error) {
    if (seq === state.seq) renderPriorities(state.data.priorities);
  }
}

function drawCharts() {
  if (!state.data) return;
  const p = state.data.profile;
  const history = p.position_history;
  const css = getComputedStyle(document.documentElement);
  const blue = css.getPropertyValue('--brand-blue').trim() || '#2874C2';
  const pink = css.getPropertyValue('--brand-pink').trim() || '#D23B82';
  const chartText = '#2A4058';
  const ns = 'http://www.w3.org/2000/svg';
  const make = (tag, attrs={}, text='') => {
    const element = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([name,value])=>element.setAttribute(name,String(value)));
    if (text !== '') element.textContent = text;
    return element;
  };
  const addText = (parent, x, y, text, attrs={}) => parent.append(make('text',{x,y,fill:chartText,...attrs},text));
  const resetChart = (container, height, title) => {
    container.replaceChildren();
    container.style.minWidth = '0';
    container.style.height = `${height}px`;
    const width = Math.max(300,Math.round(container.getBoundingClientRect().width || container.parentElement?.getBoundingClientRect().width || 800));
    const chart = make('svg',{class:'native-chart plot-container',viewBox:`0 0 ${width} ${height}`,width:'100%',height:'100%',role:'img','aria-label':title});
    chart.append(make('title',{},title));
    container.append(chart);
    return {chart,width,compact:width<650};
  };
  const amountLabel = (value, compact=false) => {
    const number=Number(value || 0),absolute=Math.abs(number);
    if(!compact) return `${fmt(number)} Mn`;
    const digits=absolute>=100?0:absolute>=1?1:2;
    return number.toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
  };
  const monthLabel = (label,compact) => compact?String(label).split(' ')[0]:label;
  const truncate = (value,length) => String(value).length>length?`${String(value).slice(0,length-1)}…`:String(value);

  const positionHeight = window.innerWidth<650?330:390;
  const positionResult = resetChart($('position-chart'),positionHeight,'Bank assets and liabilities in millions by reporting month');
  const position=positionResult.chart,positionWidth=positionResult.width,positionCompact=positionResult.compact;
  const margin = positionCompact?{left:50,right:16,top:50,bottom:55}:{left:88,right:42,top:50,bottom:65};
  const plotWidth = positionWidth-margin.left-margin.right, plotHeight = positionHeight-margin.top-margin.bottom;
  const values = history.flatMap(item=>[item.assets,item.liabilities]);
  const rawMin = Math.min(0,...values), rawMax = Math.max(0,...values), span = Math.max(1,rawMax-rawMin);
  const min = rawMin-span*.16, max = rawMax+span*.19;
  const x = index => margin.left+(history.length===1?plotWidth/2:index*plotWidth/(history.length-1));
  const y = value => margin.top+(max-value)*plotHeight/(max-min);
  const grid = make('g',{class:'chart-grid'});
  for (let index=0;index<5;index++) {
    const value=min+(max-min)*index/4, py=y(value);
    grid.append(make('line',{x1:margin.left,y1:py,x2:positionWidth-margin.right,y2:py,stroke:'#E6EDF5','stroke-width':1}));
    const tick=make('g',{class:'ytick'});addText(tick,margin.left-9,py+4,amountLabel(value,true),{'text-anchor':'end'});grid.append(tick);
  }
  position.append(grid);
  const zeroY=y(0);
  position.append(make('line',{x1:margin.left,y1:zeroY,x2:positionWidth-margin.right,y2:zeroY,stroke:'#C8D7E6','stroke-width':1.2}));
  history.forEach((item,index)=>{
    const tick=make('g',{class:'xtick'});addText(tick,x(index),positionHeight-31,monthLabel(item.label,positionCompact),{'text-anchor':'middle'});position.append(tick);
  });
  addText(position,margin.left+plotWidth/2,positionHeight-8,'Reporting month',{'text-anchor':'middle',class:'axis-title'});
  const unitX=positionCompact?13:22;
  const unit=make('text',{x:unitX,y:margin.top+plotHeight/2,fill:chartText,class:'axis-title',transform:`rotate(-90 ${unitX} ${margin.top+plotHeight/2})`,'text-anchor':'middle'},p.unit);
  position.append(unit);
  ['assets','liabilities'].forEach((category,index)=>{
    const color=index===0?blue:pink;
    const points=history.map((item,i)=>`${x(i)},${y(item[category])}`).join(' ');
    position.append(make('polyline',{points,fill:'none',stroke:color,'stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round'}));
    history.forEach((item,i)=>position.append(make('circle',{cx:x(i),cy:y(item[category]),r:4,fill:color,stroke:'#fff','stroke-width':1.4})));
    const labels=make('g',{class:'textpoint-series'});
    history.forEach((item,i)=>{
      const above=index===0?item.assets>=item.liabilities:item.liabilities>item.assets;
      if(positionCompact && i!==0 && i!==history.length-1 && i%3!==0) return;
      const group=make('g',{class:'textpoint'});
      addText(group,x(i),y(item[category])+(above?-12:19),amountLabel(item[category],positionCompact),{
        'text-anchor':'middle',fill:index===0?'#175897':'#A52A64'
      });
      labels.append(group);
    });
    position.append(labels);
  });

  const key = state.movement;
  const products = p.products.filter(r=>r[key].amount_mn!==null).sort((a,b)=>Math.abs(b[key].amount_mn)-Math.abs(a[key].amount_mn)).slice(0,6).reverse();
  const movements = products.map(r=>r[key].amount_mn);
  const movementHeight=window.innerWidth<650?340:380;
  const movementResult=resetChart($('movement-chart'),movementHeight,'Product movement values in millions');
  const movement=movementResult.chart,movementWidth=movementResult.width,movementCompact=movementResult.compact;
  const movementMargin=movementCompact?{left:128,right:48,top:24,bottom:60}:{left:218,right:82,top:24,bottom:68};
  const movementPlotWidth=movementWidth-movementMargin.left-movementMargin.right;
  const movementPlotHeight=movementHeight-movementMargin.top-movementMargin.bottom;
  const rawLow=Math.min(0,...movements),rawHigh=Math.max(0,...movements),extent=Math.max(1,rawHigh-rawLow);
  const low=rawLow-extent*.24,high=rawHigh+extent*.24;
  const movementX=value=>movementMargin.left+(value-low)*movementPlotWidth/(high-low);
  for(let index=0;index<5;index++){
    const value=low+(high-low)*index/4,px=movementX(value);
    movement.append(make('line',{x1:px,y1:movementMargin.top,x2:px,y2:movementHeight-movementMargin.bottom,stroke:'#E6EDF5','stroke-width':1}));
    const tick=make('g',{class:'xtick'});addText(tick,px,movementHeight-35,amountLabel(value,true),{'text-anchor':'middle'});movement.append(tick);
  }
  movement.append(make('line',{x1:movementX(0),y1:movementMargin.top,x2:movementX(0),y2:movementHeight-movementMargin.bottom,stroke:'#BCCDDD','stroke-width':1.2}));
  const rowHeight=movementPlotHeight/Math.max(1,products.length);
  products.forEach((product,index)=>{
    const value=product[key].amount_mn,center=movementMargin.top+rowHeight*(index+.5),zero=movementX(0),end=movementX(value);
    const tick=make('g',{class:'ytick'});addText(tick,movementMargin.left-10,center+4,truncate(product.label,movementCompact?19:34),{'text-anchor':'end'});movement.append(tick);
    movement.append(make('rect',{x:Math.min(zero,end),y:center-11,width:Math.max(2,Math.abs(end-zero)),height:22,rx:5,fill:value<0?pink:blue}));
    addText(movement,end+(value<0?-7:7),center+4,movementCompact?product[key].display:`${product[key].display} Mn`,{
      class:'bartext','text-anchor':value<0?'end':'start'
    });
  });
  addText(movement,movementMargin.left+movementPlotWidth/2,movementHeight-8,`${key==='mom'?'Monthly':'Year-to-date'} change · ${p.unit}`,{'text-anchor':'middle',class:'axis-title'});

  const availableProducts=p.products.filter(product=>product.category===state.productCategory).sort((a,b)=>{
    const peak=product=>Math.max(...product.history.map(item=>Math.abs(item.amount_mn)));
    return peak(b)-peak(a);
  });
  if(!availableProducts.some(product=>product.id===state.productId)) state.productId=availableProducts[0]?.id || null;
  const selector=$('product-performance-select');
  selector.innerHTML=availableProducts.map(product=>`<option value="${esc(product.id)}">${esc(product.label)}</option>`).join('');
  selector.value=state.productId || '';
  document.querySelectorAll('[data-product-category]').forEach(button=>button.classList.toggle('selected',button.dataset.productCategory===state.productCategory));
  const selected=availableProducts.find(product=>product.id===state.productId);
  if(!selected){
    $('product-performance-caption').textContent=`No ${state.productCategory} products are available for this customer.`;
    $('product-performance-chart').replaceChildren();
    return;
  }
  $('product-performance-caption').textContent=`${selected.label} · monthly balance in ${p.unit}.`;
  const productHeight=window.innerWidth<650?320:370;
  const productResult=resetChart($('product-performance-chart'),productHeight,`${selected.label} monthly performance in millions`);
  const productChart=productResult.chart,productWidth=productResult.width,productCompact=productResult.compact;
  const productMargin=productCompact?{left:50,right:16,top:46,bottom:55}:{left:88,right:42,top:48,bottom:65};
  const productPlotWidth=productWidth-productMargin.left-productMargin.right,productPlotHeight=productHeight-productMargin.top-productMargin.bottom;
  const productValues=selected.history.map(item=>item.amount_mn);
  const productRawMin=Math.min(0,...productValues),productRawMax=Math.max(0,...productValues),productSpan=Math.max(1,productRawMax-productRawMin);
  const productMin=productRawMin-productSpan*.14,productMax=productRawMax+productSpan*.2;
  const productX=index=>productMargin.left+(selected.history.length===1?productPlotWidth/2:index*productPlotWidth/(selected.history.length-1));
  const productY=value=>productMargin.top+(productMax-value)*productPlotHeight/(productMax-productMin);
  for(let index=0;index<5;index++){
    const value=productMin+(productMax-productMin)*index/4,py=productY(value);
    productChart.append(make('line',{x1:productMargin.left,y1:py,x2:productWidth-productMargin.right,y2:py,stroke:'#E6EDF5','stroke-width':1}));
    const tick=make('g',{class:'ytick'});addText(tick,productMargin.left-9,py+4,amountLabel(value,true),{'text-anchor':'end'});productChart.append(tick);
  }
  selected.history.forEach((item,index)=>{
    const label=p.position_history.find(positionItem=>positionItem.month===item.month)?.label || item.month;
    const tick=make('g',{class:'xtick'});addText(tick,productX(index),productHeight-31,monthLabel(label,productCompact),{'text-anchor':'middle'});productChart.append(tick);
  });
  const productColor=state.productCategory==='assets'?blue:pink;
  productChart.append(make('polyline',{points:selected.history.map((item,index)=>`${productX(index)},${productY(item.amount_mn)}`).join(' '),fill:'none',stroke:productColor,'stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round'}));
  selected.history.forEach((item,index)=>{
    productChart.append(make('circle',{cx:productX(index),cy:productY(item.amount_mn),r:4,fill:productColor,stroke:'#fff','stroke-width':1.4}));
    if(productCompact && index!==0 && index!==selected.history.length-1 && index%2!==0) return;
    const group=make('g',{class:'product-point'});
    addText(group,productX(index),productY(item.amount_mn)-12,amountLabel(item.amount_mn,productCompact),{'text-anchor':'middle',fill:state.productCategory==='assets'?'#175897':'#A52A64'});
    productChart.append(group);
  });
  addText(productChart,productMargin.left+productPlotWidth/2,productHeight-8,'Reporting month',{'text-anchor':'middle',class:'axis-title'});
  const productUnitX=productCompact?13:22;
  productChart.append(make('text',{x:productUnitX,y:productMargin.top+productPlotHeight/2,fill:chartText,class:'axis-title',transform:`rotate(-90 ${productUnitX} ${productMargin.top+productPlotHeight/2})`,'text-anchor':'middle'},p.unit));
}

async function refreshAll() {
  $('refresh-button').disabled = true;
  try {
    const data = await jsonRequest('/api/customers');
    state.customers = data.customers;
    if (!state.customers.some(c=>c.cif===state.current)) state.current=data.default_cif;
    customerOptions($('cif-input').value.trim());
    await loadCustomer(state.current);
  } catch(error) {notice(error.message);}
  finally {$('refresh-button').disabled=false;}
}

document.addEventListener('DOMContentLoaded', async()=>{
  try {
    const data = await jsonRequest('/api/customers');
    state.customers = data.customers;
    state.current = data.default_cif;
    customerOptions();
    await loadCustomer(state.current);
  } catch(error) {notice(error.message);$('dashboard').setAttribute('aria-busy','false');}
  $('company-select').addEventListener('change',event=>loadCustomer(event.target.value));
  let filterTimer;
  $('cif-input').addEventListener('input',()=>{
    clearTimeout(filterTimer);
    filterTimer=setTimeout(()=>{
      const query=$('cif-input').value.trim();
      const matches=customerOptions(query);
      if (query && matches.length===1) loadCustomer(matches[0].cif);
      else if (query && matches.length===0) notice('No company matches that CIF.');
      else notice();
    },250);
  });
  $('cif-form').addEventListener('submit',event=>{
    event.preventDefault();clearTimeout(filterTimer);
    const query=$('cif-input').value.trim();
    const exact=state.customers.find(c=>c.cif===query);
    if(exact) {customerOptions(query);loadCustomer(exact.cif);}
    else notice('Enter a matching CIF or select a company from the list.');
  });
  $('refresh-button').addEventListener('click',refreshAll);
  $('ai-refresh').addEventListener('click',()=>{
    if (!state.data) return;
    if(state.data.ai_available) improvePriorities(state.seq,state.data.version,true);
    else loadCustomer(state.current,{quiet:true});
  });
  document.querySelectorAll('[data-movement]').forEach(button=>button.addEventListener('click',()=>{
    state.movement=button.dataset.movement;
    document.querySelectorAll('[data-movement]').forEach(b=>b.classList.toggle('selected',b===button));
    drawCharts();
  }));
  document.querySelectorAll('[data-product-category]').forEach(button=>button.addEventListener('click',()=>{
    state.productCategory=button.dataset.productCategory;
    state.productId=null;
    drawCharts();
  }));
  $('product-performance-select').addEventListener('change',event=>{
    state.productId=event.target.value;
    drawCharts();
  });
  $('presentation-button').addEventListener('click',()=>{
    const active=document.body.classList.toggle('presentation');
    $('presentation-button').textContent=active?'Exit presentation':'Present';
    window.scrollTo({top:0,behavior:'smooth'});setTimeout(drawCharts,80);
  });
  document.querySelectorAll('.nav-link').forEach(link=>link.addEventListener('click',()=>{
    document.querySelectorAll('.nav-link').forEach(a=>a.classList.toggle('active',a===link));
  }));
  let resizeTimer;
  window.addEventListener('resize',()=>{
    clearTimeout(resizeTimer);
    resizeTimer=setTimeout(drawCharts,120);
  });
  setInterval(async()=>{
    if(document.hidden || !state.current || !state.data) return;
    try {
      const data=await jsonRequest(`/api/customer/${encodeURIComponent(state.current)}`);
      if(data.version!==state.data.version) await loadCustomer(state.current,{quiet:true});
    } catch(error) { /* Keep the last rendered position until the next refresh. */ }
  },60000);
});
