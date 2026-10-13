"use strict";
(() => {
  const token=document.querySelector('meta[name="editor-token"]').content;
  const page=document.querySelector('meta[name="editor-page"]')?.content||'index.html';
  const pageLabels={'index.html':'Startseite','lerneinheiten/glasl.html':'Glasl','lerneinheiten/watzlawick.html':'Watzlawick','lerneinheiten/schulz-von-thun.html':'Schulz von Thun'};
  let version=document.querySelector('meta[name="editor-version"]').content;
  let selected=null, block=null, preview=false, undo=[], redo=[], typing=false, drag=null, busy=false, textRange=null;
  const toolbar=document.createElement('div'); toolbar.className='editor-toolbar'; toolbar.dataset.editor='toolbar';
  toolbar.innerHTML=`<div class="editor-row"><strong data-control="page-label">Seite bearbeiten</strong><button data-action="save" class="primary">Speichern</button><button data-action="preview">Vorschau</button><button data-action="undo">Rückgängig</button><button data-action="redo">Wiederholen</button><span class="editor-state" role="status" aria-live="polite">Unverändert</span></div>
  <div class="editor-row editor-tools"><button data-action="text">Text einfügen</button><button data-action="heading">Überschrift einfügen</button><button data-action="image">Bild einfügen</button><button data-action="up">Nach oben</button><button data-action="down">Nach unten</button><button data-action="delete">Element löschen</button><button data-action="bold" aria-pressed="false" title="Markierten Text fett formatieren; ohne Markierung das ganze Textfeld"><strong>Fett</strong></button>
  <label>Schrift <input data-control="font" type="number" min="10" max="60" step="1" aria-label="Schriftgröße in Pixeln"> px</label><label>Breite <input data-control="width" type="range" min="25" max="100" step="5" value="100" aria-label="Breite in Prozent"><output data-control="width-label">100 %</output></label><label>Feldhöhe <input data-control="height" type="number" min="0" max="1600" step="10" placeholder="Auto" aria-label="Mindesthöhe des Textfelds in Pixeln"> px</label><button data-action="size-auto">Feldgröße automatisch</button><label>Ausrichtung <select data-control="align"><option value="left">Links</option><option value="center">Mittig</option><option value="right">Rechts</option></select></label><button data-action="alt">Bildbeschreibung</button><input data-control="file" type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden></div>
  <nav class="editor-row" aria-label="Editorseiten"><a href="/editor">Startseite</a><a href="/lerneinheiten/glasl.html?editor=1">Glasl</a><a href="/lerneinheiten/watzlawick.html?editor=1">Watzlawick</a><a href="/lerneinheiten/schulz-von-thun.html?editor=1">Schulz von Thun</a></nav><details class="editor-service" data-editor="service"><summary>Lokaler Dienst</summary><p>Der Dienst muss laufen, damit der Editor unter seiner Adresse erreichbar bleibt. Schließen des Browser-Tabs beendet ihn nicht.</p><button data-action="stop">Lokalen Dienst ausschalten</button></details><p class="editor-help">Text anklicken und schreiben. Links zu anderen Seiten öffnen sich nur in der Vorschau. Markierten Text mit „Fett“ formatieren. Textfelder über Breite/Feldhöhe oder am Eckgriff vergrößern. Elemente mit den Pfeilen verschieben; Modulblöcke auch am Griff ziehen. Speichern legt vorher eine Sicherung an.</p>`;
  document.body.prepend(toolbar);
  toolbar.querySelector('[data-control="page-label"]').textContent=(pageLabels[page]||'Seite')+' bearbeiten';
  toolbar.querySelectorAll('nav a').forEach(a=>{if((page==='index.html'&&a.getAttribute('href')==='/editor')||a.getAttribute('href')==='/'+page+'?editor=1')a.setAttribute('aria-current','page');});
  const q=s=>toolbar.querySelector(s), status=message=>q('.editor-state').textContent=message;
  const areas=()=>[document.querySelector('.page-header'),document.querySelector('main'),document.querySelector('footer')].filter(Boolean);
  function clean(node){
    const clone=node.cloneNode(true);
    clone.querySelectorAll('[data-editor]').forEach(e=>e.remove());
    [clone,...clone.querySelectorAll('*')].forEach(e=>{
      e.removeAttribute('contenteditable');e.removeAttribute('draggable');e.classList.remove('editor-selected','editor-active','editor-preview');
      if(e.getAttribute('class')==='')e.removeAttribute('class');
      if(e.getAttribute('tabindex')==='-1')e.removeAttribute('tabindex');
    });
    clone.querySelectorAll("#lernangebot,#studienprojekt").forEach(e=>e.removeAttribute("hidden"));
    clone.querySelectorAll("details").forEach(e=>e.removeAttribute("open"));
    return clone;
  }
  const snapshot=()=>areas().map(a=>clean(a).innerHTML);
  const key=s=>JSON.stringify(s);
  let saved=key(snapshot());
  const dirty=()=>key(snapshot())!==saved;
  function controls(){
    q('[data-action="undo"]').disabled=undo.length===0||busy;
    q('[data-action="redo"]').disabled=redo.length===0||busy;
    ['up','down','delete','alt'].forEach(a=>q(`[data-action="${a}"]`).disabled=!selected||preview||busy);
    q('[data-action="alt"]').disabled=!selected||selected.tagName!=='IMG'||preview||busy;
    q('[data-control="font"]').disabled=!selected||selected.tagName==='IMG'||preview||busy;
    ['width','align'].forEach(c=>q(`[data-control="${c}"]`).disabled=!selected||preview||busy);
    q('[data-action="save"]').disabled=busy;
    const editable=selected&&selected.hasAttribute('contenteditable');
    q('[data-action="bold"]').disabled=!editable||preview||busy;
    q('[data-control="height"]').disabled=!editable||preview||busy;
    q('[data-action="size-auto"]').disabled=!editable||preview||busy;
  }
  function changed(){status(dirty()?'Ungespeicherte Änderungen':'Unverändert');controls();}
  function remember(){const s=snapshot();if(!undo.length||key(undo[undo.length-1])!==key(s))undo.push(s);if(undo.length>80)undo.shift();redo=[];}
  function restore(s){areas().forEach((a,i)=>a.innerHTML=s[i]);selected=block=null;typing=false;textRange=null;setup();window.dispatchEvent(new Event('hashchange'));changed();}
  function findBlock(element){
    const group=element.closest('.learning-area,.academic-modules article,figure'); if(group)return group;
    let current=element; while(current.parentElement&&!current.parentElement.matches('main,main > section,.stage-body,.page-header,footer'))current=current.parentElement;
    return current;
  }
  function select(element){
    document.querySelectorAll('[data-editor="resize"]').forEach(e=>e.remove());
    document.querySelectorAll('.editor-selected').forEach(e=>e.classList.remove('editor-selected'));
    if(selected!==element){textRange=null;q('[data-action="bold"]').setAttribute('aria-pressed','false');}
    selected=element;block=findBlock(element);element.classList.add('editor-selected');
    const font=parseFloat(getComputedStyle(element).fontSize);q('[data-control="font"]').value=Math.round(font);
    q('[data-control="width"]').value=parseFloat(element.style.width)||100;
    q('[data-control="width-label"]').textContent=q('[data-control="width"]').value+' %';
    q('[data-control="height"]').value=parseFloat(element.style.minHeight)||'';
    q('[data-control="align"]').value=element.style.textAlign||'left';controls();
    if(element.hasAttribute('contenteditable')&&!preview)addResizeHandle(element);
  }
  function captureRange(){
    const selection=window.getSelection();if(!selected||!selection.rangeCount)return;
    const range=selection.getRangeAt(0);
    if(selected.contains(range.startContainer)&&selected.contains(range.endContainer))textRange=range.collapsed?null:range.cloneRange();
  }
  function isBold(node){
    for(let e=node.parentElement;e;e=e.parentElement){
      if(e.style.fontWeight)return e.style.fontWeight==='bold'||Number(e.style.fontWeight)>=600;
      if(e.tagName==='STRONG'||e.tagName==='B')return true;
      if(e===selected)break;
    }
    const weight=getComputedStyle(node.parentElement).fontWeight;
    return weight==='bold'||Number(weight)>=600;
  }
  function toggleBold(){
    let range=textRange;
    if(!range||!selected.contains(range.startContainer)||!selected.contains(range.endContainer)){
      range=document.createRange();range.selectNodeContents(selected);
    }
    const walker=document.createTreeWalker(selected,NodeFilter.SHOW_TEXT);
    const parts=[];
    while(walker.nextNode()){
      const node=walker.currentNode;
      if(node.parentElement.closest('[data-editor]')||!range.intersectsNode(node))continue;
      const start=node===range.startContainer?range.startOffset:0;
      const end=node===range.endContainer?range.endOffset:node.length;
      if(end>start)parts.push({node,start,end,bold:isBold(node)});
    }
    if(!parts.length)return;
    remember();typing=false;
    const makeBold=!parts.every(part=>part.bold), formatted=[];
    parts.forEach(({node,start,end})=>{
      if(end<node.length)node.splitText(end);
      const piece=start?node.splitText(start):node;
      const wrapper=document.createElement(makeBold?'strong':'span');
      if(!makeBold)wrapper.style.fontWeight='400';
      piece.before(wrapper);wrapper.append(piece);formatted.push(piece);
    });
    const result=document.createRange();result.setStart(formatted[0],0);result.setEnd(formatted[formatted.length-1],formatted[formatted.length-1].length);
    const selection=window.getSelection();selection.removeAllRanges();selection.addRange(result);textRange=result.cloneRange();
    q('[data-action="bold"]').setAttribute('aria-pressed',String(makeBold));changed();
  }
  function addResizeHandle(element){
    const handle=document.createElement('button');handle.type='button';handle.className='editor-resize';handle.dataset.editor='resize';handle.contentEditable='false';handle.tabIndex=-1;
    handle.setAttribute('aria-label','Textfeldgröße durch Ziehen ändern');handle.title='Breite und Feldhöhe ziehen';element.append(handle);
    handle.addEventListener('pointerdown',event=>{
      event.preventDefault();event.stopPropagation();remember();typing=false;
      const rectangle=element.getBoundingClientRect(),parentWidth=element.parentElement.getBoundingClientRect().width;
      if(!parentWidth)return;
      const x=event.clientX,y=event.clientY;
      handle.setPointerCapture(event.pointerId);
      const move=pointer=>{
        const width=Math.min(100,Math.max(25,100*(rectangle.width+pointer.clientX-x)/parentWidth));
        const height=Math.min(1600,Math.max(0,rectangle.height+pointer.clientY-y));
        element.style.width=width.toFixed(1)+'%';element.style.maxWidth='100%';element.style.minHeight=Math.round(height)+'px';
        q('[data-control="width"]').value=width;q('[data-control="width-label"]').textContent=Math.round(width)+' %';q('[data-control="height"]').value=Math.round(height);
      };
      const finish=()=>{handle.removeEventListener('pointermove',move);handle.removeEventListener('pointerup',finish);handle.removeEventListener('pointercancel',finish);changed();};
      handle.addEventListener('pointermove',move);handle.addEventListener('pointerup',finish);handle.addEventListener('pointercancel',finish);
    });
  }
  function setup(){
    document.body.classList.toggle('editor-active',!preview);document.body.classList.toggle('editor-preview',preview);
    document.querySelectorAll('[data-editor="resize"]').forEach(e=>e.remove());
    areas().forEach(a=>{
      a.querySelectorAll('details').forEach(e=>e.open=!preview);
      a.querySelectorAll('p,h1,h2,h3,h4,summary,figcaption,li,.model-description,.model-open').forEach(e=>{if(preview)e.removeAttribute('contenteditable');else e.setAttribute('contenteditable','true');});
      a.querySelectorAll('.editor-grip').forEach(e=>e.remove());
      if(!preview)a.querySelectorAll('.learning-area,.academic-modules article,figure').forEach(e=>{
        const grip=document.createElement('button');grip.type='button';grip.className='editor-grip';grip.textContent='Block verschieben';grip.dataset.editor='grip';grip.draggable=true;
        grip.addEventListener('click',()=>select(e));
        grip.addEventListener('dragstart',event=>{drag=e;event.dataTransfer.setData('text/plain','block');event.dataTransfer.effectAllowed='move';});
        grip.addEventListener('dragend',()=>drag=null);e.prepend(grip);
      });
    });controls();
  }
  function exportHTML(){
    const clone=clean(document.documentElement);
    clone.querySelectorAll('meta[name^="editor-"],link[href="editor.css"],script[src="editor.js"]').forEach(e=>e.remove());
    clone.classList.remove('js-navigation');
    clone.querySelectorAll('main > section').forEach(e=>e.removeAttribute('hidden'));
    clone.querySelectorAll('.navigation a').forEach(e=>e.removeAttribute('aria-current'));
    return '<!doctype html>\n'+clone.outerHTML+'\n';
  }
  async function post(path,body,json=true){
    const response=await fetch(path,{method:'POST',headers:{'X-Editor-Token':token,...(json?{'Content-Type':'application/json'}:{})},body:json?JSON.stringify(body):body});
    const data=await response.json();if(!response.ok)throw new Error(data.error||'Speichern fehlgeschlagen.');return data;
  }
  function insert(element){
    const main=document.querySelector('main');
    const section=block&&main.contains(block)?block.parentElement:document.querySelector('main > section:not([hidden])')||main;
    if(block&&section.contains(block))block.after(element);else section.append(element);
    setup();select(element.matches('figure')?element.querySelector('img'):element);changed();
  }
  async function act(action){
    if(busy)return;
    if(action==='stop'){
      if(dirty()){status('Bitte zuerst speichern oder Änderungen rückgängig machen.');return;}
      if(!confirm('Lokalen Dienst wirklich ausschalten? Danach ist der Editor-Link nicht mehr erreichbar. Zum Neustarten musst du Startseite bearbeiten.cmd doppelt anklicken.'))return;
      try{await post('/api/stop',{});toolbar.querySelectorAll('button,input,select').forEach(e=>e.disabled=true);status('Lokaler Dienst ausgeschaltet. Zum erneuten Öffnen „Startseite bearbeiten.cmd“ doppelklicken.');}catch(error){status(error.message);}return;
    }
    if(action==='save'){
      const html=exportHTML(), state=key(snapshot());busy=true;controls();status('Speichert …');
      try{const data=await post('/api/save',{html,version,page});version=data.version;saved=state;status(dirty()?'Gespeichert; weitere Änderungen offen':'Gespeichert · Sicherung angelegt');}
      catch(error){status(error.message);}finally{busy=false;controls();}return;
    }
    if(action==='preview'){preview=!preview;document.querySelectorAll('.editor-selected').forEach(e=>e.classList.remove('editor-selected'));selected=block=null;setup();q('[data-action="preview"]').textContent=preview?'Weiter bearbeiten':'Vorschau';return;}
    if(action==='undo'&&undo.length){redo.push(snapshot());restore(undo.pop());return;}
    if(action==='redo'&&redo.length){undo.push(snapshot());restore(redo.pop());return;}
    if(preview)return;
    if(action==='image'){q('[data-control="file"]').click();return;}
    if(action==='text'||action==='heading'){remember();const e=document.createElement(action==='text'?'p':'h2');e.textContent=action==='text'?'Neuen Text hier eingeben':'Neue Überschrift';insert(e);e.focus();return;}
    if(!selected)return;
    if(action==='bold'){captureRange();toggleBold();return;}
    if(action==='size-auto'){remember();selected.style.removeProperty('width');selected.style.removeProperty('max-width');selected.style.removeProperty('min-height');q('[data-control="width"]').value=100;q('[data-control="width-label"]').textContent='100 %';q('[data-control="height"]').value='';typing=false;changed();return;}
    if(action==='alt'&&selected.tagName==='IMG'){const value=prompt('Bildbeschreibung (für Menschen, die das Bild nicht sehen):',selected.alt||'');if(value!==null){remember();selected.alt=value;changed();}return;}
    if(action==='up'&&block.previousElementSibling){remember();block.previousElementSibling.before(block);changed();}
    if(action==='down'&&block.nextElementSibling){remember();block.nextElementSibling.after(block);changed();}
    if(action==='delete'){
      remember();const target=selected.tagName==='SUMMARY'?selected.parentElement:selected.tagName==='IMG'?selected.closest('figure')||selected:selected;
      target.remove();selected=block=null;setup();changed();
    }
  }
  toolbar.addEventListener('click',event=>{const button=event.target.closest('[data-action]');if(button)act(button.dataset.action);});
  toolbar.addEventListener('mousedown',event=>{captureRange();if(event.target.closest('button'))event.preventDefault();});
  document.addEventListener('selectionchange',captureRange);
  areas().forEach(a=>{
    a.addEventListener('click',event=>{if(preview||event.target.closest('[data-editor]'))return;const anchor=event.target.closest('a[href]');if(anchor){event.preventDefault();const href=anchor.getAttribute('href');if(href.startsWith('#')&&!anchor.closest('[contenteditable]')){const target=document.getElementById(href.slice(1));if(target){target.scrollIntoView();const offset=getComputedStyle(toolbar).position==='sticky'?toolbar.getBoundingClientRect().height:0;window.scrollBy(0,-offset-16);}return;}}const e=event.target.closest('p,h1,h2,h3,h4,summary,figcaption,li,img,.model-description,.model-open');if(e&&a.contains(e))select(e);if(e&&e.tagName==='SUMMARY')event.preventDefault();});
    a.addEventListener('auxclick',event=>{if(!preview&&event.target.closest('a[href]'))event.preventDefault();});
    a.addEventListener('focusin',event=>{if(preview||!event.target.hasAttribute('contenteditable'))return;select(event.target);typing=false;});
    a.addEventListener('beforeinput',event=>{if(preview)return;if(!typing){remember();typing=true;} if(['insertParagraph','insertLineBreak'].includes(event.inputType)){event.preventDefault();document.execCommand('insertLineBreak');}});
    a.addEventListener('input',changed);
    a.addEventListener('paste',event=>{if(preview||!event.target.isContentEditable)return;event.preventDefault();if(!typing){remember();typing=true;}document.execCommand('insertText',false,event.clipboardData.getData('text/plain'));changed();});
    a.addEventListener('dragover',event=>{if(drag&&!preview){const target=event.target.closest('.learning-area,.academic-modules article,figure');if(target&&target.parentElement===drag.parentElement)event.preventDefault();}});
    a.addEventListener('drop',event=>{if(!drag||preview)return;const target=event.target.closest('.learning-area,.academic-modules article,figure');if(target&&target!==drag&&target.parentElement===drag.parentElement){event.preventDefault();remember();target.before(drag);changed();}drag=null;});
  });
  ['font','width','height','align'].forEach(control=>{
    const input=q(`[data-control="${control}"]`);
    input.addEventListener('change',()=>{
      if(!selected||preview)return;remember();
      if(control==='font'){const value=Math.min(60,Math.max(10,Number(input.value)||16));input.value=value;selected.style.fontSize=value+'px';}
      if(control==='width'){selected.style.width=input.value+'%';selected.style.maxWidth='100%';q('[data-control="width-label"]').textContent=input.value+' %';}
      if(control==='height'){const value=Math.min(1600,Math.max(0,Number(input.value)||0));if(value)selected.style.minHeight=value+'px';else selected.style.removeProperty('min-height');input.value=value||'';}
      if(control==='align'){selected.style.textAlign=input.value; if(selected.tagName==='IMG'){selected.style.display='block';selected.style.marginLeft=input.value==='left'?'0':'auto';selected.style.marginRight=input.value==='right'?'0':'auto';}}
      changed();
    });
  });
  q('[data-control="file"]').addEventListener('change',async event=>{
    const file=event.target.files[0];if(!file)return;event.target.value='';busy=true;controls();status('Bild wird eingefügt …');
    try{const data=await post('/api/image',file,false);remember();const figure=document.createElement('figure');figure.className='editor-image';const img=document.createElement('img');img.src=(page.startsWith('lerneinheiten/')?'../':'')+data.src;img.alt=file.name.replace(/\.[^.]+$/,'');img.style.width='100%';figure.append(img);const caption=document.createElement('figcaption');caption.textContent='Bildunterschrift';figure.append(caption);insert(figure);}
    catch(error){status(error.message);}finally{busy=false;controls();}
  });
  window.addEventListener('beforeunload',event=>{if(dirty()){event.preventDefault();event.returnValue='';}});
  setup();
})();
