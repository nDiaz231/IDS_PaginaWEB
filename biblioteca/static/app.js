// Mejora progresiva: la navegación y los formularios funcionan sin JavaScript.
document.querySelectorAll('form[data-confirm]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});
const error = document.querySelector('[data-error]');
if (error) error.focus();

// Actualiza favoritos en el sitio, conservando el scroll, los filtros y el foco.
const favoriteStatus = document.createElement('div');
favoriteStatus.className = 'favorite-status';
favoriteStatus.setAttribute('role', 'status');
favoriteStatus.setAttribute('aria-live', 'polite');
document.body.append(favoriteStatus);
let favoriteStatusTimer;
document.querySelectorAll('form[data-favorite]').forEach((form) => {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button');
    if (form.dataset.pending) return;
    form.dataset.pending = 'true';
    button.setAttribute('aria-disabled', 'true');
    button.setAttribute('aria-busy', 'true');
    let message;
    try {
      const response = await fetch(form.getAttribute('action'), {
        method: 'POST', body: new FormData(form),
        headers: { Accept: 'application/json' }, credentials: 'same-origin',
      });
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('No se pudo actualizar');
      }
      const result = await response.json();
      const label = result.favorite ? 'Quitar de favoritos' : 'Agregar a favoritos';
      form.elements.action.value = result.favorite ? 'remove' : 'add';
      const star = button.querySelector('.favorite-star');
      star.classList.toggle('is-favorite', result.favorite);
      button.replaceChildren(star, document.createTextNode(` ${label}`));
      button.setAttribute('aria-label', `${label}: ${form.dataset.title}`);
      message = result.message;
    } catch {
      message = 'No pudimos confirmar el cambio. Inténtalo de nuevo; si tu sesión venció, recarga la página.';
    } finally {
      delete form.dataset.pending;
      button.removeAttribute('aria-disabled');
      button.removeAttribute('aria-busy');
      clearTimeout(favoriteStatusTimer);
      favoriteStatus.textContent = message;
      favoriteStatusTimer = setTimeout(() => { favoriteStatus.textContent = ''; }, 6000);
    }
  });
});

const collection = document.getElementById('collection_id');
const duration = document.getElementById('requested_days');
if (collection && duration) {
  const updateDuration = () => {
    const maximum = collection.value === 'alta_demanda' ? 14 : 30;
    duration.max = String(maximum);
    document.getElementById('duration-help').textContent = `Máximo: ${maximum} días para la colección seleccionada.`;
  };
  collection.addEventListener('change', updateDuration);
  updateDuration();
}
