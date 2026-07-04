/* SENAI CRM — Criador de Agentes (tela mocada) */

function handleFileSelect(input) {
  const label = document.getElementById('upload-label');
  if (input.files && input.files.length > 0) {
    label.textContent = input.files[0].name;
  } else {
    label.textContent = 'Clique para selecionar um arquivo .csv';
  }
}

function mockAction(message) {
  showSuccess(message);
}

function handleCreateAgent(event) {
  event.preventDefault();
  showSuccess('Agente criado com sucesso (simulacao). Nenhum dado foi enviado a um servidor real.');
  event.target.reset();
  document.getElementById('upload-label').textContent = 'Clique para selecionar um arquivo .csv';
  document.getElementById('temp-value').textContent = '0.7';
  return false;
}

function showSuccess(message) {
  const el = document.getElementById('create-success');
  if (!el) return;
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(showSuccess._t);
  showSuccess._t = setTimeout(() => el.classList.remove('show'), 4000);
}
