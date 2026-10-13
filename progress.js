"use strict";
(() => {
  // Content weights are estimated effort units; unfinished placeholders do not count.
  // Participant persistence will be provided by the future authenticated server.
  const percentage = items => {
    const valid = items.filter(item => Number.isFinite(item.weight) && item.weight > 0);
    const total = valid.reduce((sum, item) => sum + item.weight, 0);
    const done = valid.reduce((sum, item) => sum + (item.complete ? item.weight : 0), 0);
    const value = total ? done / total * 100 : 0;
    // Show 100 only when every weighted content item is complete.
    return value === 100 ? 100 : Math.min(99, Math.round(value));
  };
  function refresh() {
    document.querySelectorAll('.learning-area[data-module]').forEach(module => {
      const items = [...module.querySelectorAll('[data-content-id][data-progress-weight]')].map(content => ({
        weight: Number(content.dataset.progressWeight), complete: content.dataset.completed === 'true'
      }));
      const value = percentage(items);
      const progress = module.querySelector('.module-progress progress');
      const label = module.querySelector('.module-progress-value');
      if (!progress || !label) return;
      progress.value = value;
      progress.setAttribute('aria-valuetext', value + ' Prozent abgeschlossen' + (items.length ? '' : '; Inhalte in Vorbereitung'));
      label.textContent = value + ' %';
    });
  }
  document.addEventListener('change', event => {
    if (document.querySelector('meta[name="editor-token"]')) return;
    const checkbox = event.target.closest('input[type="checkbox"][data-completion-toggle]');
    const content = checkbox && checkbox.closest('[data-content-id]');
    if (content) { content.dataset.completed = String(checkbox.checked); refresh(); }
  });
  // Future content pages/server adapters update completion then emit this event.
  document.addEventListener('learning-progress-changed', refresh);
  refresh();
})();
