(function () {
  const TOKEN_KEY = 'ppt_agent_token';
  const USER_KEY = 'ppt_agent_user';

  function qs(id) {
    return document.getElementById(id);
  }

  function show(el, on) {
    if (!el) return;
    el.classList.toggle('hidden', !on);
  }

  function setText(el, txt) {
    if (!el) return;
    el.textContent = txt;
  }

  function setHtml(el, html) {
    if (!el) return;
    el.innerHTML = html;
  }

  function getToken() {
    try {
      return localStorage.getItem(TOKEN_KEY) || '';
    } catch (e) {
      return '';
    }
  }

  function setToken(token, username) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, username || '');
    } catch (e) {}
  }

  function clearAuth() {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch (e) {}
  }

  function getUsername() {
    try {
      return localStorage.getItem(USER_KEY) || '';
    } catch (e) {
      return '';
    }
  }

  async function apiFetch(path, options) {
    const opts = options || {};
    opts.headers = opts.headers || {};

    const token = getToken();
    if (token) {
      opts.headers['Authorization'] = 'Bearer ' + token;
    }

    const resp = await fetch(path, opts);
    if (!resp.ok) {
      let msg = '请求失败';
      try {
        const data = await resp.json();
        msg = data && (data.detail || data.message) ? (data.detail || data.message) : msg;
      } catch (e) {}
      const err = new Error(msg);
      err.status = resp.status;
      throw err;
    }

    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      return await resp.json();
    }
    return await resp.text();
  }

  function requireLoginOrRedirect() {
    const token = getToken();
    if (!token) {
      window.location.replace('/ui/login.html');
      return false;
    }
    return true;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function bootLogin() {
    const token = getToken();
    if (token) {
      window.location.replace('/ui/upload.html');
      return;
    }

    const form = qs('loginForm');
    const errBox = qs('loginError');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      show(errBox, false);

      const fd = new FormData(form);
      const username = String(fd.get('username') || '').trim();
      const password = String(fd.get('password') || '');

      if (!username || !password) {
        setText(errBox, '请填写用户名和密码');
        show(errBox, true);
        return;
      }

      try {
        const data = await apiFetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password }),
        });

        setToken(data.token, data.username);
        window.location.replace('/ui/upload.html');
      } catch (err) {
        setText(errBox, err.message || '登录失败');
        show(errBox, true);
      }
    });
  }

  async function bootRegister() {
    const form = qs('registerForm');
    const errBox = qs('registerError');
    const okBox = qs('registerOk');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      show(errBox, false);
      show(okBox, false);

      const fd = new FormData(form);
      const username = String(fd.get('username') || '').trim();
      const password = String(fd.get('password') || '');
      const password2 = String(fd.get('password2') || '');

      if (!username || !password) {
        setText(errBox, '请填写用户名和密码');
        show(errBox, true);
        return;
      }
      if (password.length < 6) {
        setText(errBox, '密码至少 6 位');
        show(errBox, true);
        return;
      }
      if (password !== password2) {
        setText(errBox, '两次输入的密码不一致');
        show(errBox, true);
        return;
      }

      try {
        await apiFetch('/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password }),
        });

        setText(okBox, '注册成功，请前往登录');
        show(okBox, true);
        setTimeout(() => window.location.replace('/ui/login.html'), 600);
      } catch (err) {
        setText(errBox, err.message || '注册失败');
        show(errBox, true);
      }
    });
  }

  async function bootUpload() {
    if (!requireLoginOrRedirect()) return;

    const logoutBtn = qs('logoutBtn');
    const userBadge = qs('userBadge');

    if (userBadge) {
      const u = getUsername();
      if (u) {
        setText(userBadge, '当前用户：' + u);
        show(userBadge, true);
      }
    }

    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        clearAuth();
        window.location.replace('/ui/login.html');
      });
    }

    const uploadError = qs('uploadError');
    const uploadOk = qs('uploadOk');

    const pptMeta = qs('pptMeta');
    const pptIdEl = qs('pptId');
    const pptSlidesEl = qs('pptSlides');

    const generateAllBtn = qs('generateAllBtn');
    const slidesList = qs('slidesList');

    const progressWrap = qs('progressWrap');
    const progressBar = qs('progressBar');
    const progressText = qs('progressText');
    const progressPct = qs('progressPct');

    const markdownRaw = qs('markdownRaw');
    const markdownView = qs('markdownView');
    const copyBtn = qs('copyBtn');
    const exportPdfBtn = qs('exportPdfBtn');
    const notesList = qs('notesList');

    const uploadTabFile = qs('uploadTabFile');
    const uploadTabUrl = qs('uploadTabUrl');
    const uploadPanelFile = qs('uploadPanelFile');
    const uploadPanelUrl = qs('uploadPanelUrl');

    const outputTabPreview = qs('outputTabPreview');
    const outputTabRaw = qs('outputTabRaw');
    const outputPanelPreview = qs('outputPanelPreview');
    const outputPanelRaw = qs('outputPanelRaw');

    const searchInput = qs('searchInput');
    const searchBtn = qs('searchBtn');
    const searchError = qs('searchError');
    const searchResults = qs('searchResults');

    let pptId = '';
    let slides = [];
    let notesByIndex = new Map();
    let selectedNoteIndex = null;

    function setTabActive(btn, active) {
      if (!btn) return;
      if (active) {
        btn.classList.remove('bg-white/10', 'hover:bg-white/15', 'border', 'border-white/10', 'text-slate-50');
        btn.classList.add('bg-white', 'text-slate-900');
      } else {
        btn.classList.remove('bg-white', 'text-slate-900');
        btn.classList.add('bg-white/10', 'hover:bg-white/15', 'border', 'border-white/10', 'text-slate-50');
      }
    }

    function setUploadMode(mode) {
      const isFile = mode === 'file';
      show(uploadPanelFile, isFile);
      show(uploadPanelUrl, !isFile);
      setTabActive(uploadTabFile, isFile);
      setTabActive(uploadTabUrl, !isFile);
    }

    function setOutputMode(mode) {
      const isPreview = mode === 'preview';
      show(outputPanelPreview, isPreview);
      show(outputPanelRaw, !isPreview);
      setTabActive(outputTabPreview, isPreview);
      setTabActive(outputTabRaw, !isPreview);
    }

    function setProgress(on, pct, text) {
      show(progressWrap, on);
      if (!on) return;
      const p = Math.max(0, Math.min(100, pct || 0));
      if (progressBar) progressBar.style.width = p + '%';
      setText(progressPct, p.toFixed(0) + '%');
      setText(progressText, text || '处理中…');
    }

    function renderMarkdown(md) {
      if (markdownRaw) markdownRaw.value = md || '';
      try {
        let html = '';
        if (window.marked) {
          // 兼容两种用法：marked.parse(md)（新版本）和 marked(md)（旧版本）
          if (typeof window.marked.parse === 'function') {
            html = window.marked.parse(md || '');
          } else if (typeof window.marked === 'function') {
            html = window.marked(md || '');
          } else {
            html = escapeHtml(md || '');
          }
        } else {
          html = escapeHtml(md || '');
        }
        setHtml(markdownView, html);
      } catch (e) {
        setHtml(markdownView, '<pre class="whitespace-pre-wrap text-sm">' + escapeHtml(md || '') + '</pre>');
      }
    }

    function renderNotesList() {
      if (!notesList) return;

      const keys = Array.from(notesByIndex.keys()).sort((a, b) => a - b);
      if (keys.length === 0) {
        setHtml(notesList, '<div class="text-xs text-slate-300 px-2 py-2">生成后的页面会出现在这里</div>');
        return;
      }

      const html = keys
        .map((idx) => {
          const n = notesByIndex.get(idx);
          const title = escapeHtml((n && n.title) ? n.title : '');
          const active = Number(idx) === Number(selectedNoteIndex);
          const cls = active
            ? 'w-full text-left rounded-xl bg-white text-slate-900 px-3 py-2 text-xs font-medium'
            : 'w-full text-left rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 px-3 py-2 text-xs text-slate-100';
          return (
            '<button data-note="' + idx + '" class="' + cls + '">' +
            '  <div class="truncate">第 ' + idx + ' 页</div>' +
            '  <div class="mt-0.5 text-[11px] opacity-80 truncate">' + title + '</div>' +
            '</button>'
          );
        })
        .join('');

      setHtml(notesList, html);
      notesList.querySelectorAll('button[data-note]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const idx = Number(btn.getAttribute('data-note') || '0');
          selectNote(idx);
        });
      });
    }

    function selectNote(idx) {
      if (!notesByIndex.has(idx)) return;
      selectedNoteIndex = idx;
      renderNotesList();
      const n = notesByIndex.get(idx);
      renderMarkdown((n && n.md) ? n.md : '');
    }

    function setNote(idx, title, expandedMarkdown) {
      const md = '# 第 ' + idx + ' 页：' + (title || '') + '\n\n' + (expandedMarkdown || '');
      notesByIndex.set(idx, { idx, title: title || '', md });
      if (selectedNoteIndex === null) {
        selectedNoteIndex = idx;
      }
      renderNotesList();
      selectNote(idx);
    }

    function resetNotes() {
      notesByIndex = new Map();
      selectedNoteIndex = null;
      renderNotesList();
      renderMarkdown('');
    }

    async function loadSlides() {
      slides = await apiFetch('/slides?ppt_id=' + encodeURIComponent(pptId));
      show(generateAllBtn, slides && slides.length > 0);
      renderSlidesList();
    }

    function renderSlidesList() {
      if (!slidesList) return;
      if (!slides || slides.length === 0) {
        setHtml(slidesList, '<div class="text-sm text-slate-400">请先上传 PPT</div>');
        return;
      }

      const items = slides
        .map((s) => {
          const title = escapeHtml(s.title || '');
          const idx = Number(s.index || 0);
          return (
            '<div class="rounded-xl bg-white/5 border border-white/10 p-4 flex items-start justify-between gap-4">' +
            '  <div class="min-w-0">' +
            '    <div class="text-sm font-semibold truncate">' + idx + '. ' + title + '</div>' +
            '    <div class="mt-1 text-xs text-slate-300">要点：' + escapeHtml((s.bullets || []).slice(0, 3).join(' / ') || '无') + '</div>' +
            '  </div>' +
            '  <div class="flex-shrink-0">' +
            '    <button data-expand="' + idx + '" class="rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 px-3 py-2 text-xs">生成该页</button>' +
            '  </div>' +
            '</div>'
          );
        })
        .join('');

      setHtml(slidesList, items);

      slidesList.querySelectorAll('button[data-expand]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const idx = Number(btn.getAttribute('data-expand') || '0');
          await expandOne(idx);
        });
      });
    }

    async function expandOne(idx) {
      show(uploadError, false);
      show(uploadOk, false);
      setProgress(true, 0, '正在生成第 ' + idx + ' 页…');

      try {
        const r = await apiFetch(
          '/expand?ppt_id=' + encodeURIComponent(pptId) + '&slide_index=' + encodeURIComponent(String(idx)) + '&use_wikipedia=true'
        );
        const title = (r && r.title) ? r.title : '';
        setNote(idx, title, r.expanded_markdown || '');
        setProgress(false);
      } catch (err) {
        setText(uploadError, err.message || '生成失败');
        show(uploadError, true);
        setProgress(false);
      }
    }

    async function expandAll() {
      if (!slides || slides.length === 0) return;

      resetNotes();
      setProgress(true, 1, '开始生成整份笔记…');

      for (let i = 0; i < slides.length; i++) {
        const s = slides[i];
        const idx = Number(s.index || 0);
        const pct = ((i) / slides.length) * 100;
        setProgress(true, pct, '正在生成第 ' + idx + ' / ' + slides.length + ' 页…');

        try {
          const r = await apiFetch(
            '/expand?ppt_id=' + encodeURIComponent(pptId) + '&slide_index=' + encodeURIComponent(String(idx)) + '&use_wikipedia=true'
          );
          const title = (r && r.title) ? r.title : (s.title || '');
          setNote(idx, title, r.expanded_markdown || '');
        } catch (err) {
          setNote(idx, s.title || '', '> 生成失败：' + (err.message || '未知错误'));
        }
      }

      setProgress(true, 100, '完成');
      setTimeout(() => setProgress(false), 600);
    }

    async function doSearch() {
      show(searchError, false);
      if (!pptId) {
        setText(searchError, '请先上传 PPT');
        show(searchError, true);
        return;
      }

      const q = String((searchInput && searchInput.value) || '').trim();
      if (!q) {
        setText(searchError, '请输入搜索关键词');
        show(searchError, true);
        return;
      }

      try {
        const hits = await apiFetch(
          '/search?ppt_id=' + encodeURIComponent(pptId) + '&q=' + encodeURIComponent(q) + '&top_k=5'
        );

        if (!searchResults) return;
        if (!hits || hits.length === 0) {
          setHtml(searchResults, '<div class="text-sm text-slate-400">未检索到结果</div>');
          return;
        }

        const html = hits
          .map((h) => {
            const idx = Number(h.slide_index || 0);
            return (
              '<div class="rounded-xl bg-white/5 border border-white/10 p-4">' +
              '  <div class="flex items-start justify-between gap-4">' +
              '    <div class="min-w-0">' +
              '      <div class="text-sm font-semibold truncate">第 ' + idx + ' 页：' + escapeHtml(h.title || '') + '</div>' +
              '      <div class="mt-2 text-xs text-slate-300">' + escapeHtml(h.snippet || '') + '</div>' +
              '    </div>' +
              '    <button data-expand-search="' + idx + '" class="flex-shrink-0 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 px-3 py-2 text-xs">生成该页</button>' +
              '  </div>' +
              '</div>'
            );
          })
          .join('');

        setHtml(searchResults, html);
        searchResults.querySelectorAll('button[data-expand-search]').forEach((btn) => {
          btn.addEventListener('click', async () => {
            const idx = Number(btn.getAttribute('data-expand-search') || '0');
            await expandOne(idx);
          });
        });
      } catch (err) {
        setText(searchError, err.message || '搜索失败');
        show(searchError, true);
      }
    }

    if (copyBtn) {
      copyBtn.addEventListener('click', async () => {
        try {
          const txt = (markdownRaw && markdownRaw.value) ? markdownRaw.value : '';
          await navigator.clipboard.writeText(txt);
          copyBtn.textContent = '已复制';
          setTimeout(() => (copyBtn.textContent = '复制'), 800);
        } catch (e) {
          copyBtn.textContent = '复制失败';
          setTimeout(() => (copyBtn.textContent = '复制'), 800);
        }
      });
    }

    if (exportPdfBtn) {
      exportPdfBtn.addEventListener('click', async () => {
        const md = (markdownRaw && markdownRaw.value) ? markdownRaw.value : '';
        if (!md.trim()) {
          exportPdfBtn.textContent = '内容为空';
          setTimeout(() => (exportPdfBtn.textContent = '导出 PDF'), 800);
          return;
        }

        if (!window.html2pdf) {
          exportPdfBtn.textContent = '浏览器不支持';
          setTimeout(() => (exportPdfBtn.textContent = '导出 PDF'), 1000);
          return;
        }

        exportPdfBtn.disabled = true;
        exportPdfBtn.textContent = '导出中…';

        try {
          // 构造一个临时的「白底黑字」容器，避免继承页面的深色主题样式
          const container = document.createElement('div');
          container.style.backgroundColor = '#ffffff';
          container.style.color = '#111827'; // 近似 slate-900
          container.style.padding = '24px';
          container.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif";
          container.style.lineHeight = '1.6';
          container.style.maxWidth = '800px';

          // 直接使用右侧预览区域的 HTML 内容："所见即所得"
          // 如果预览区为空，则退化为原始 markdown 文本
          if (markdownView && markdownView.innerHTML.trim()) {
            container.innerHTML = markdownView.innerHTML;
          } else {
            container.innerHTML = '<pre style="white-space: pre-wrap; font-size: 14px;">' + escapeHtml(md) + '</pre>';
          }
          document.body.appendChild(container);

          const opt = {
            // 外层 margin 设为 0，具体留白由 container 的 padding 控制，避免顶部大空白
            margin:       0,
            filename:     'ppt-notes.pdf',
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  {
              scale: 1.6,
              useCORS: true,
              scrollY: 0, // 避免受当前滚动位置影响
            },
            jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
          };

          await window.html2pdf().set(opt).from(container).save();

          // 清理临时节点
          document.body.removeChild(container);

          exportPdfBtn.textContent = '已导出';
          setTimeout(() => (exportPdfBtn.textContent = '导出 PDF'), 1000);
        } catch (e) {
          exportPdfBtn.textContent = '导出失败';
          setTimeout(() => (exportPdfBtn.textContent = '导出 PDF'), 1000);
        } finally {
          exportPdfBtn.disabled = false;
        }
      });
    }

    if (searchBtn) {
      searchBtn.addEventListener('click', doSearch);
    }

    if (uploadTabFile && uploadTabUrl) {
      uploadTabFile.addEventListener('click', () => setUploadMode('file'));
      uploadTabUrl.addEventListener('click', () => setUploadMode('url'));
      setUploadMode('file');
    }

    if (outputTabPreview && outputTabRaw) {
      outputTabPreview.addEventListener('click', () => setOutputMode('preview'));
      outputTabRaw.addEventListener('click', () => setOutputMode('raw'));
      setOutputMode('preview');
      window.__PPT_AGENT_UPLOAD_TABS_BOUND__ = true;
    }

    const uploadFileBtn = qs('uploadFileBtn');
    if (uploadFileBtn) {
      uploadFileBtn.addEventListener('click', async () => {
        show(uploadError, false);
        show(uploadOk, false);

        const fileInput = qs('pptFile');
        const f = fileInput && fileInput.files && fileInput.files[0];
        if (!f) {
          setText(uploadError, '请选择一个 .pptx 文件');
          show(uploadError, true);
          return;
        }

        const form = new FormData();
        form.append('file', f);

        try {
          setProgress(true, 5, '正在上传并解析…');
          const data = await apiFetch('/upload', { method: 'POST', body: form });
          pptId = data.ppt_id;
          setText(pptIdEl, pptId);
          setText(pptSlidesEl, String(data.num_slides || ''));
          show(pptMeta, true);

          resetNotes();

          setText(uploadOk, '上传成功，已解析并写入向量库');
          show(uploadOk, true);

          await loadSlides();
          setProgress(false);
        } catch (err) {
          setText(uploadError, err.message || '上传失败');
          show(uploadError, true);
          setProgress(false);
        }
      });
    }

    const uploadUrlBtn = qs('uploadUrlBtn');
    if (uploadUrlBtn) {
      uploadUrlBtn.addEventListener('click', async () => {
        show(uploadError, false);
        show(uploadOk, false);

        const url = String((qs('pptUrl') && qs('pptUrl').value) || '').trim();
        if (!url) {
          setText(uploadError, '请填写 URL');
          show(uploadError, true);
          return;
        }

        try {
          setProgress(true, 5, '正在从 URL 拉取并解析…');
          const data = await apiFetch('/upload_url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
          });

          pptId = data.ppt_id;
          setText(pptIdEl, pptId);
          setText(pptSlidesEl, String(data.num_slides || ''));
          show(pptMeta, true);

          resetNotes();

          setText(uploadOk, '上传成功，已解析并写入向量库');
          show(uploadOk, true);

          await loadSlides();
          setProgress(false);
        } catch (err) {
          setText(uploadError, err.message || 'URL 上传失败');
          show(uploadError, true);
          setProgress(false);
        }
      });
    }

    if (generateAllBtn) {
      generateAllBtn.addEventListener('click', expandAll);
    }

    renderSlidesList();
    resetNotes();
  }

  window.PPT_AGENT_BOOT = function () {
    const page = window.PPT_AGENT_PAGE;
    if (page === 'login') return bootLogin();
    if (page === 'register') return bootRegister();
    if (page === 'upload') return bootUpload();
  };
})();
