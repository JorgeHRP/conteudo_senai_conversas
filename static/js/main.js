/* CNC CRM — main.js */

/* ---- Modal de conversa ---- */
function openConversation(telefone, nome) {
  const overlay = document.getElementById('modal-overlay');
  const nameEl  = document.getElementById('modal-name');
  const phoneEl = document.getElementById('modal-phone');
  const chat    = document.getElementById('chat-wrap');

  nameEl.textContent  = nome     || 'Conversa';
  phoneEl.textContent = telefone || '';
  chat.innerHTML = `
    <div class="loading-dots">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    </div>`;

  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';

  fetch('/api/conversation/' + encodeURIComponent(telefone))
    .then(r => r.json())
    .then(msgs => {
      if (!msgs.length) {
        chat.innerHTML = '<p class="chat-empty">Nenhuma mensagem registrada.</p>';
        return;
      }
      chat.innerHTML = msgs.map(m => `
        <div class="bubble ${escHtml(m.type)}">${escHtml(m.content)}</div>
      `).join('');
      chat.scrollTop = chat.scrollHeight;
    })
    .catch(() => {
      chat.innerHTML = '<p class="chat-empty">Erro ao carregar a conversa.</p>';
    });
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = String(str || '');
  return d.innerHTML;
}

/* ---- Filtros da tabela ---- */
function filterTable() {
  const search = (document.getElementById('search-input')?.value || '').toLowerCase();
  const status = document.getElementById('status-filter')?.value || '';
  const follow  = document.getElementById('follow-filter')?.value || '';
  const rows   = document.querySelectorAll('#tbody tr');
  let visible  = 0;

  rows.forEach(row => {
    const txt    = row.textContent.toLowerCase();
    const rowSt  = row.dataset.status  || '';
    const rowFol = row.dataset.follow  || '';

    const ok = (!search || txt.includes(search))
            && (!status || rowSt === status)
            && (!follow  || rowFol === follow);

    row.style.display = ok ? '' : 'none';
    if (ok) visible++;
  });

  const countEl = document.getElementById('count-label');
  if (countEl) countEl.textContent = `${visible} registro${visible !== 1 ? 's' : ''}`;
}

/* ---- Init ---- */
document.addEventListener('DOMContentLoaded', () => {
  /* close modal on backdrop click */
  const overlay = document.getElementById('modal-overlay');
  if (overlay) {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) closeModal();
    });
  }

  /* ESC to close */
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
  });

  /* initial count label */
  filterTable();
});
