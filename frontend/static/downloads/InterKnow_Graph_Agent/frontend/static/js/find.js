(() => {
  const HISTORY_KEY = 'find_history_v1';

  function $(id){ return document.getElementById(id); }

  function loadHistory(){
    try{ return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }catch(e){ return []; }
  }

  function saveHistory(list){ localStorage.setItem(HISTORY_KEY, JSON.stringify(list)); }

  function renderHistory(){
    const list = loadHistory();
    const container = $('historyList');
    container.innerHTML = '';
    if(list.length===0){ container.innerHTML = '<li style="padding:8px; text-align:center; opacity:0.8;">暂无历史</li>'; return; }
    list.slice().reverse().forEach((item, idx)=>{
      const li = document.createElement('li');
      li.style.padding='8px';
      li.style.borderBottom='1px solid rgba(255,255,255,0.06)';
      li.style.cursor='pointer';
      li.textContent = item.title || ('查询 ' + new Date(item.t||Date.now()).toLocaleString());
      li.addEventListener('click', ()=> loadConversation(item));
      container.appendChild(li);
    });
  }

  function loadConversation(item){
    if(!item || !item.conversation) return;
    renderChat(item.conversation);
  }

  function renderChat(conv){
    const disp = $('chatDisplay');
    disp.innerHTML = '';
    conv.forEach(msg=>{
      const msgEl = document.createElement('div');
      msgEl.style.margin='8px 0';
      msgEl.style.padding='8px';
      msgEl.style.borderRadius='6px';
      msgEl.style.maxWidth='90%';
      msgEl.style.whiteSpace='pre-wrap';
      if(msg.role==='user'){
        msgEl.style.background='rgba(255,255,255,0.1)';
        msgEl.style.alignSelf='flex-end';
        msgEl.style.marginLeft='20%';
      } else {
        msgEl.style.background='rgba(0,0,0,0.15)';
        msgEl.style.alignSelf='flex-start';
        msgEl.style.marginRight='20%';
      }
      msgEl.textContent = msg.text;
      disp.appendChild(msgEl);
    });
    if($('autoScroll').checked) disp.scrollTop = disp.scrollHeight;
  }

  function appendMessage(role, text){
    const disp = $('chatDisplay');
    const msgEl = document.createElement('div');
    msgEl.style.margin='8px 0';
    msgEl.style.padding='8px';
    msgEl.style.borderRadius='6px';
    msgEl.style.maxWidth='90%';
    msgEl.style.whiteSpace='pre-wrap';
    if(role==='user'){
      msgEl.style.background='rgba(255,255,255,0.1)';
      msgEl.style.alignSelf='flex-end';
      msgEl.style.marginLeft='20%';
    } else {
      msgEl.style.background='rgba(0,0,0,0.15)';
      msgEl.style.alignSelf='flex-start';
      msgEl.style.marginRight='20%';
    }
    msgEl.textContent = text;
    disp.appendChild(msgEl);
    if($('autoScroll').checked) disp.scrollTop = disp.scrollHeight;
  }

  function getCurrentConversation(){
    const disp = $('chatDisplay');
    const nodes = Array.from(disp.children || []);
    return nodes.map((el,i)=>{
      const isUser = el.style.alignSelf==='flex-end';
      return { role: isUser? 'user':'assistant', text: el.textContent };
    });
  }

  function addToHistory(title){
    const list = loadHistory();
    const item = { t: Date.now(), title: title || ('查询 ' + new Date().toLocaleString()), conversation: getCurrentConversation() };
    list.push(item);
    saveHistory(list);
    renderHistory();
  }

  function clearHistory(){ localStorage.removeItem(HISTORY_KEY); renderHistory(); }

  async function callBackend(userText){
    const controller = new AbortController();
    const timeout = setTimeout(()=>controller.abort(), 120000);
    const payload = { message: userText, history: getCurrentConversation() };
    try{
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      clearTimeout(timeout);
      if(!res.ok) throw new Error('后端响应异常');
      const data = await res.json();
      if(data.error) throw new Error(data.error);
      const reply = data.reply || data.answer || '（未返回内容）';
      return reply;
    } catch(err){
      clearTimeout(timeout);
      throw err;
    }
  }

  function bind(){
    $('sendBtn').addEventListener('click', async ()=>{
      const txt = $('userInput').value.trim();
      if(!txt) return alert('请输入内容');
      appendMessage('user', txt);
      $('userInput').value = '';
      appendMessage('assistant', '正在生成回复...');
      const disp = $('chatDisplay');
      addToHistory(txt);

      try{
        const reply = await callBackend(txt);
        if(disp.lastChild && disp.lastChild.textContent==='正在生成回复...') disp.removeChild(disp.lastChild);
        appendMessage('assistant', reply);
      }catch(err){
        if(disp.lastChild && disp.lastChild.textContent==='正在生成回复...') disp.removeChild(disp.lastChild);
        appendMessage('assistant', '后端调用失败：' + err.message);
      }
    });

    $('saveHistoryBtn').addEventListener('click', ()=>{
      addToHistory(null);
      alert('已保存到历史');
    });

    $('clearHistoryBtn').addEventListener('click', ()=>{
      if(confirm('确定清除所有历史吗？')) clearHistory();
    });

    // 按 Enter 发送（Shift+Enter 换行）
    $('userInput').addEventListener('keydown', (e)=>{
      if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); $('sendBtn').click(); }
    });
  }

  window.addEventListener('DOMContentLoaded', ()=>{
    renderHistory();
    bind();
  });

})();
