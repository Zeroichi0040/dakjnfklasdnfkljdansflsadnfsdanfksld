// Enhancement only: all shopping forms work with JavaScript disabled.
document.addEventListener('submit', (event) => {
  const form = event.target;
  if (form.dataset.busy) {
    form.setAttribute('aria-busy', 'true');
    const feedback = form.querySelector('.submit-feedback');
    if (feedback) feedback.textContent = form.dataset.busy;
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;
  }
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('form[aria-busy]').forEach((form) => {
    form.removeAttribute('aria-busy');
    form.querySelectorAll('button').forEach((button) => { button.disabled = false; });
    const feedback = form.querySelector('.submit-feedback');
    if (feedback) feedback.textContent = '';
  });
});
