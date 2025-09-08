/*! GharFix Always-Visible Chatbot Widget v1.0.0 */
(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    API_BASE: 'https://gharfix-chatbot.onrender.com',
    API_ENDPOINT: '/chat',
    TITLE: '🏠 GharFix Assistant',
    SUBTITLE: 'Always here to help',
    STORAGE_KEY: 'gfc_conversation_id',
    MINIMIZED_KEY: 'gfc_minimized_state',
    WELCOME_MESSAGE: `Welcome to GharFix! I'm here 24/7 to help you with:
    
🔧 Plumbing & Electrical
🧹 Cleaning Services
👗 Tailoring Services
🍳 Chef Services
💆 Massage & Wellness
🏠 And much more!

What service do you need today?`,
    QUICK_ACTIONS: ['Our Services','Book Now','Pricing','Emergency Help']
  };

  // State
  let conversationId = getOrCreateConversationId();
  let isTyping = false;
  let isMinimized = localStorage.getItem(CONFIG.MINIMIZED_KEY)==='true';
  let elements = {};

  // Helpers
  function getOrCreateConversationId(){
    let id=localStorage.getItem(CONFIG.STORAGE_KEY);
    if(!id){
      id='cid-'+Date.now()+'-'+Math.floor(Math.random()*1000);
      localStorage.setItem(CONFIG.STORAGE_KEY,id);
    }
    return id;
  }
  function createEl(tag,attrs={},kids=[]){
    const e=document.createElement(tag);
    Object.entries(attrs).forEach(([k,v])=>{
      if(k==='className') e.className=v;
      else e.setAttribute(k,v);
    });
    (Array.isArray(kids)?kids:[kids]).forEach(c=>{
      if(typeof c==='string') e.appendChild(document.createTextNode(c));
      else if(c) e.appendChild(c);
    });
    return e;
  }

  // Build widget DOM
  function buildWidget(){
    // Minimize button
    const minBtn=createEl('button',{id:'gfc-minimize',type:'button',title:'Minimize chat'},['−']);
    // Header
    const hdr=createEl('div',{id:'gfc-header'},[
      createEl('h3',{},[CONFIG.TITLE]),
      createEl('p',{},[CONFIG.SUBTITLE]),
      minBtn
    ]);
    // Messages
    const msgs=createEl('div',{id:'gfc-messages'});
    // Quick actions
    const qa=createEl('div',{className:'gfc-quick-actions'});
    CONFIG.QUICK_ACTIONS.forEach(a=>{
      const b=createEl('button',{className:'gfc-quick-btn',type:'button'},[a]);
      b.onclick=()=>handleQuick(a);
      qa.appendChild(b);
    });
    // Input
    const inp=createEl('input',{id:'gfc-input',type:'text',placeholder:'Type your message...',autocomplete:'off'});
    const send=createEl('button',{id:'gfc-send',type:'submit'},['Send']);
    const bar=createEl('form',{id:'gfc-inputbar',autocomplete:'off'},[inp,send]);
    // Container
    const w= createEl('div',{id:'gfc-always-chat',className:isMinimized?'minimized':''},[hdr,msgs,qa,bar]);
    return {widget:w,header:hdr,messages:msgs,input:inp,sendBtn:send,minBtn: minBtn,bar:bar};
  }

  // Message utils
  function addMessage(text,who){
    const b=createEl('div',{className:'gfc-bubble'});
    b.innerHTML=text.replace(/\n/g,'<br>');
    const m=createEl('div',{className:`gfc-msg gfc-${who}`},[b]);
    elements.messages.appendChild(m);
    elements.messages.scrollTop=elements.messages.scrollHeight;
  }
  function showTyping(){
    const dots=[createEl('span',{className:'dot'}),createEl('span',{className:'dot'}),createEl('span',{className:'dot'})];
    const t=createEl('div',{className:'gfc-typing'},['Assistant is typing',...dots]);
    const b=createEl('div',{className:'gfc-bubble'},[t]);
    const m=createEl('div',{className:'gfc-msg gfc-bot',id:'gfc-typing'},[b]);
    elements.messages.appendChild(m); elements.messages.scrollTop=elements.messages.scrollHeight;
  }
  function hideTyping(){
    const e=document.getElementById('gfc-typing'); if(e) e.remove();
  }

  // Send to API
  async function sendMessage(text){
    if(isTyping) return;
    isTyping=true; elements.sendBtn.disabled=true; showTyping();
    try{
      const res=await fetch(CONFIG.API_BASE+CONFIG.API_ENDPOINT,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:text,conversation_id:conversationId})
      });
      hideTyping();
      if(!res.ok) throw new Error(res.status);
      const d=await res.json();
      addMessage(d.response||'Sorry, try again.','bot');
    }catch(e){
      hideTyping();
      console.error(e);
      addMessage("Error connecting. Please try later.",'bot');
    }finally{
      isTyping=false; elements.sendBtn.disabled=false;
    }
  }

  // Event handlers
  function handleMin(){
    isMinimized=!isMinimized;
    localStorage.setItem(CONFIG.MINIMIZED_KEY,isMinimized);
    elements.widget.classList.toggle('minimized',isMinimized);
    elements.minBtn.textContent=isMinimized?'+':'−';
    if(!isMinimized) elements.input.focus();
  }
  function handleQuick(a){
    if(isMinimized) handleMin();
    addMessage(a,'user'); sendMessage(a);
  }
  function handleSubmit(e){
    e.preventDefault();
    if(isMinimized){handleMin(); return;}
    const v=elements.input.value.trim(); if(!v) return;
    addMessage(v,'user'); elements.input.value=''; sendMessage(v);
  }

  // Init
  function init(){
    elements=buildWidget();
    document.body.appendChild(elements.widget);
    elements.minBtn.addEventListener('click',handleMin);
    elements.bar.addEventListener('submit',handleSubmit);
    if(!isMinimized){
      setTimeout(()=>{addMessage(CONFIG.WELCOME_MESSAGE,'bot');},500);
    }
    elements.minBtn.textContent=isMinimized?'+':'−';
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
  else init();

})();
