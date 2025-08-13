(function(){
  const API_URL = window.DIGIJORDII_API || "http://localhost:8787/ask";

  function el(tag, cls, html){ const e = document.createElement(tag); if(cls) e.className = cls; if(html) e.innerHTML = html; return e; }
  function addMsg(container, text, who){
    const m = el("div","dj-msg " + (who==="user"?"dj-user":"dj-bot"));
    m.textContent = text; container.appendChild(m); container.scrollTop = container.scrollHeight;
  }

  const btn = el("button", null, "Chat with DigiJordii"); btn.id="dj-launcher";
  const panel = el("div"); panel.id="dj-panel";
  const header = el("div", null, `<span>DigiJordii</span><button id="dj-close" style="background:none;border:none;color:#fff;font-size:18px;cursor:pointer;">×</button>`); header.id="dj-header";
  const messages = el("div"); messages.id="dj-messages";
  const inputbar = el("div"); inputbar.id="dj-inputbar";
  const input = el("input"); input.type="text"; input.placeholder="Ask me anything about this site…"; input.id="dj-input";
  const send = el("button", null, "Send"); send.id="dj-send";
  const sources = el("div"); sources.id="dj-sources";

  inputbar.appendChild(input); inputbar.appendChild(send);
  panel.appendChild(header); panel.appendChild(messages); panel.appendChild(sources); panel.appendChild(inputbar);
  document.addEventListener("DOMContentLoaded", function(){
    document.body.appendChild(btn); document.body.appendChild(panel);
  });

  btn.onclick = ()=> { panel.style.display = "flex"; input.focus(); };
  panel.addEventListener("click", (e)=>{
    if(e.target && e.target.id === "dj-close") panel.style.display = "none";
  });
  send.onclick = submit;
  input.addEventListener("keydown", (e)=>{ if(e.key==="Enter") submit(); });

  function submit(){
    const q = input.value.trim();
    if(!q) return;
    addMsg(messages, q, "user");
    input.value = ""; sources.textContent = "Thinking…";
    fetch(API_URL, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ question: q, page_context: location.href })
    })
    .then(r => r.json())
    .then(d => {
      addMsg(messages, d.answer || "Sorry, I couldn’t get that.", "bot");
      if(d.sources && d.sources.length){
        try {
          const parts = d.sources.map(s => { try { return new URL(s).pathname } catch(e){ return s } });
          sources.textContent = "Sources: " + parts.join(" · ");
        } catch(_) { sources.textContent = ""; }
      } else {
        sources.textContent = "";
      }
    })
    .catch(()=>{
      addMsg(messages, "Server error. Please try again.", "bot");
      sources.textContent = "";
    });
  }
})();
