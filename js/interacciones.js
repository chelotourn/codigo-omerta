// ── INTERACCIONES ─────────────────────────────────────────────────────────────
function clickSosp(idx, sid) {
  const e = estado[idx];
  if (e.resuelta || e.inocentes.has(sid)) return;

  // Si ya estaba sospechado, desmarcar
  if (e.seleccion === sid) {
    e.seleccion = null;
  } else {
    e.seleccion = sid;
  }
  actualizarCartas(idx);
  actualizarBotonAcusar(idx);
}

function toggleInocente(idx, sid) {
  const e = estado[idx];
  if (e.resuelta) return;
  if (e.inocentes.has(sid)) {
    e.inocentes.delete(sid);
  } else {
    e.inocentes.add(sid);
    if (e.seleccion === sid) e.seleccion = null; // limpiar acusación si lo marcamos inocente
  }
  actualizarCartas(idx);
  actualizarBotonAcusar(idx);
}

function cambiarAcusacion(idx, sid, delta) {
  const e = estado[idx];
  if (e.resuelta) return;
  if (!e.acusaciones) e.acusaciones = {};
  const actual = e.acusaciones[sid] || 0;
  const nuevo = Math.max(0, actual + delta);
  e.acusaciones[sid] = nuevo;

  // Actualizar número
  const numEl = document.getElementById(`acus-num-${sid}`);
  if (numEl) numEl.textContent = nuevo;

  // Actualizar puntitos con animación
  const dotsEl = document.getElementById(`acus-dots-${sid}`);
  if (dotsEl) {
    dotsEl.innerHTML = Array.from({length: nuevo}, () => `<span class="acus-dot"></span>`).join('');
  }
}

function marcarVM(idx, cartaId, vm) {
  const e = estado[idx];
  if (e.resuelta) return;

  // Ciclo de 3 estados: null → vm → 'amarillo' → null
  const actual = e.marcasVM[cartaId];
  if (actual === null || actual === undefined) {
    e.marcasVM[cartaId] = vm;
  } else if (actual === vm) {
    e.marcasVM[cartaId] = vm + '_amarillo';
  } else if (actual === vm + '_amarillo') {
    e.marcasVM[cartaId] = null;
  } else {
    // estaba en el otro color o amarillo del otro → ir directo a este color
    e.marcasVM[cartaId] = vm;
  }

  const marca = e.marcasVM[cartaId];
  // Actualizar solo los botones de esa fila sin re-render total
  document.querySelectorAll(`.btn-vm[data-carta="${cartaId}"]`).forEach(btn => {
    const esEste = btn.dataset.vm === vm;
    const esOtro = btn.dataset.vm !== vm;
    btn.classList.remove('activo', 'amarillo');
    if (marca === vm && esEste) {
      btn.classList.add('activo');
    } else if (marca === vm + '_amarillo' && esEste) {
      btn.classList.add('amarillo');
    }
    // El otro botón se limpia siempre
  });
}

// Doble clic en V o M → marcar AMBOS (V y M de la misma declaración) en amarillo
function marcarAmbosAmarillo(idx, cartaId) {
  const e = estado[idx];
  if (e.resuelta) return;

  e.marcasVM[cartaId] = 'ambos_amarillo';

  document.querySelectorAll(`.btn-vm[data-carta="${cartaId}"]`).forEach(btn => {
    btn.classList.remove('activo');
    btn.classList.add('amarillo');
  });
}

function actualizarCartas(idx) {
  const e = estado[idx];
  const f = FICHAS[idx];
  document.querySelectorAll('.carta-sospechoso').forEach(card => {
    const sid = parseInt(card.dataset.sospId);
    card.classList.remove('sospechado','inocente-marcado');
    if (e.inocentes.has(sid))  card.classList.add('inocente-marcado');
    else if (e.seleccion===sid) card.classList.add('sospechado');

    // actualizar texto del botón toggle
    const btn = card.querySelector('.btn-toggle-inocente');
    if (btn) btn.textContent = e.inocentes.has(sid) ? '↩ Quitar inocente' : '✕ Marcar inocente';
  });

  // Sincronizar translucidez de nombres en declaraciones
  document.querySelectorAll('.decl-nombre[data-sosp-id]').forEach(el => {
    const sid = parseInt(el.dataset.sospId);
    el.classList.toggle('inocente-decl', e.inocentes.has(sid));
  });

  const txtSel = document.getElementById('txt-seleccion');
  if (txtSel) {
    txtSel.textContent = e.seleccion
      ? `→ ${NOMBRES[e.seleccion]||e.seleccion}`
      : 'Seleccioná un sospechoso para acusar.';
  }
}

function actualizarBotonAcusar(idx) {
  const e = estado[idx];
  const btn = document.getElementById('btn-acusar');
  if (!btn) return;
  if (e.seleccion && !e.resuelta) btn.classList.add('visible');
  else btn.classList.remove('visible');
}

function acusar(idx) {
  const e = estado[idx];
  const f = FICHAS[idx];
  if (!e.seleccion || e.resuelta) return;

  e.resuelta = true;
  e.correcto = (e.seleccion === f.culpable_id);

  // Registrar en historial de progreso
  if (f.dificultad) {
    guardarResultadoHistorial(f.dificultad, f.ficha_id, e.correcto, e.seleccion, GENERADO_ACTUAL);
  }

  // Umami: registrar tarea completada cuando el jugador acierta al sospechoso
  if (e.correcto && typeof umami !== 'undefined') {
    umami.track('Tarea Completada');
  }

  // Tracking propio: registrar cada acusación formal (acierte o no)
  if (typeof trackEvento === 'function') {
    trackEvento('acusacion', {
      dificultad: f.dificultad || null,
      caso: f.ficha_id,
      acierto: e.correcto,
    });
  }

  mostrarFicha(idx);
  renderNav();

  setTimeout(() => {
    document.getElementById('resultado')?.scrollIntoView({ behavior:'smooth', block:'nearest' });
  }, 80);
}

