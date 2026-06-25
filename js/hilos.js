// ── SISTEMA DE HILOS ─────────────────────────────────────────────────────────

// Modo doble: arrastre (drag) O clic-clic
// Estado global del hilo en progreso
let hiloEstado = {
  activo: false,       // ¿hay un hilo en construcción?
  origenId: null,      // data-chinche-id del origen
  origenEl: null,      // elemento DOM origen
  modoArrastre: false, // true=drag, false=click-click
  previewLine: null,   // línea SVG de preview
  chincheBajoCursor: null
};

function getSVG() {
  let svg = document.getElementById('hilo-svg');
  if (!svg) {
    const contenedor = document.getElementById('contenido-ficha');
    if (!contenedor) return null;
    svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.id = 'hilo-svg';
    svg.setAttribute('width','100%'); svg.setAttribute('height','100%');
    contenedor.appendChild(svg);
  }
  return svg;
}

function chincheCentro(el) {
  const svg = getSVG();
  if (!svg) return {x:0,y:0};
  const r1 = el.getBoundingClientRect();
  const r2 = svg.getBoundingClientRect();
  return {
    x: r1.left + r1.width/2  - r2.left,
    y: r1.top  + r1.height/2 - r2.top
  };
}

function crearPreviewLine(chinche) {
  const svg = getSVG(); if (!svg) return null;
  const c = chincheCentro(chinche);
  const line = document.createElementNS('http://www.w3.org/2000/svg','line');
  line.setAttribute('class','hilo-line preview');
  line.setAttribute('x1', c.x); line.setAttribute('y1', c.y);
  line.setAttribute('x2', c.x); line.setAttribute('y2', c.y);
  svg.appendChild(line);
  return line;
}

function iniciarHilo(chinche, esDrag) {
  // Si ya hay uno activo y no es drag, cancelar el anterior
  if (hiloEstado.activo && !esDrag) {
    cancelarHilo();
    return false;
  }
  hiloEstado.activo = true;
  hiloEstado.origenId = chinche.getAttribute('data-chinche-id');
  hiloEstado.origenEl = chinche;
  hiloEstado.modoArrastre = esDrag;
  hiloEstado.previewLine = crearPreviewLine(chinche);
  chinche.classList.add('activa');
  document.body.classList.add('modo-hilo');
  return true;
}

function confirmarHilo(destChinche) {
  if (!hiloEstado.activo || !hiloEstado.origenId) return;
  const destId = destChinche.getAttribute('data-chinche-id');
  if (destId === hiloEstado.origenId) { cancelarHilo(); return; }

  // Toggle: si ya existe este hilo, borrarlo; si no, crearlo
  const hilos = estado[fichaActual].hilos;
  const yaIdx = hilos.findIndex(
    h => (h.a === hiloEstado.origenId && h.b === destId) ||
         (h.b === hiloEstado.origenId && h.a === destId)
  );
  if (yaIdx >= 0) {
    hilos.splice(yaIdx, 1);
  } else {
    hilos.push({ a: hiloEstado.origenId, b: destId, origen: hiloEstado.origenId });
  }
  cancelarHilo();
  dibujarHilos(fichaActual);
}

function cancelarHilo() {
  if (hiloEstado.previewLine) { hiloEstado.previewLine.remove(); }
  if (hiloEstado.origenEl)    { hiloEstado.origenEl.classList.remove('activa'); }
  if (hiloEstado.chincheBajoCursor) {
    hiloEstado.chincheBajoCursor.classList.remove('hover-destino');
  }
  hiloEstado = { activo:false, origenId:null, origenEl:null, modoArrastre:false, previewLine:null, chincheBajoCursor:null };
  document.body.classList.remove('modo-hilo');
}

function moverPreview(clientX, clientY) {
  if (!hiloEstado.activo || !hiloEstado.previewLine) return;
  const svg = getSVG(); if (!svg) return;
  const r = svg.getBoundingClientRect();

  // Detectar chinche bajo cursor para snap
  const elBajo = document.elementFromPoint(clientX, clientY);
  const chincheBajo = elBajo ? elBajo.closest('.chinche') : null;

  // Quitar highlight anterior
  if (hiloEstado.chincheBajoCursor && hiloEstado.chincheBajoCursor !== chincheBajo) {
    hiloEstado.chincheBajoCursor.classList.remove('hover-destino');
  }

  if (chincheBajo && chincheBajo !== hiloEstado.origenEl) {
    hiloEstado.chincheBajoCursor = chincheBajo;
    chincheBajo.classList.add('hover-destino');
    const snap = chincheCentro(chincheBajo);
    hiloEstado.previewLine.setAttribute('x2', snap.x);
    hiloEstado.previewLine.setAttribute('y2', snap.y);
  } else {
    hiloEstado.chincheBajoCursor = null;
    hiloEstado.previewLine.setAttribute('x2', clientX - r.left);
    hiloEstado.previewLine.setAttribute('y2', clientY - r.top);
  }
}

// ── LISTENERS GLOBALES ────────────────────────────────────────────────────────

// MOUSEDOWN en chinche → iniciar drag (pero no si es doble clic)
let lastMouseDown = { time: 0, el: null };
document.addEventListener('mousedown', ev => {
  const chinche = ev.target.closest('.chinche');
  if (!chinche) return;
  ev.preventDefault();
  ev.stopPropagation();

  const now = Date.now();
  const esDobleClic = (now - lastMouseDown.time < 300 && lastMouseDown.el === chinche);
  lastMouseDown = { time: now, el: chinche };

  if (esDobleClic) {
    // doble clic detectado: no iniciar hilo, dejar que ondblclick lo maneje
    cancelarHilo();
    return;
  }

  iniciarHilo(chinche, true);
}, true);

// MOUSEMOVE → actualizar preview
document.addEventListener('mousemove', ev => {
  if (!hiloEstado.activo) return;
  moverPreview(ev.clientX, ev.clientY);
});

// MOUSEUP → si drag, intentar conectar
document.addEventListener('mouseup', ev => {
  if (!hiloEstado.activo || !hiloEstado.modoArrastre) return;
  const elSuelta = document.elementFromPoint(ev.clientX, ev.clientY);
  const chincheDest = elSuelta ? elSuelta.closest('.chinche') : null;
  if (chincheDest && chincheDest !== hiloEstado.origenEl) {
    confirmarHilo(chincheDest);
  } else {
    // Si soltó sin destino: convertir a modo click-click en vez de cancelar
    // (permite soltar y luego hacer clic en destino)
    hiloEstado.modoArrastre = false;
    if (hiloEstado.chincheBajoCursor) {
      hiloEstado.chincheBajoCursor.classList.remove('hover-destino');
      hiloEstado.chincheBajoCursor = null;
    }
  }
});

// CLICK en chinche → modo click-click
document.addEventListener('click', ev => {
  const chinche = ev.target.closest('.chinche');
  if (!chinche) {
    // Clic en otra cosa: cancelar si hay hilo activo en modo click-click
    if (hiloEstado.activo && !hiloEstado.modoArrastre) cancelarHilo();
    return;
  }
  ev.stopPropagation();

  if (!hiloEstado.activo) {
    // Primer clic: iniciar en modo click-click
    iniciarHilo(chinche, false);
  } else if (!hiloEstado.modoArrastre) {
    // Segundo clic: confirmar destino
    confirmarHilo(chinche);
  } else {
    // Estaba en drag pero hicieron click: confirmar igual
    confirmarHilo(chinche);
  }
}, true); // capture=true

// ESC cancela
document.addEventListener('keydown', ev => {
  if (ev.key === 'Escape') cancelarHilo();
});

// ── DIBUJAR HILOS ─────────────────────────────────────────────────────────────
function dibujarHilos(idx) {
  const svg = getSVG(); if (!svg) return;
  svg.querySelectorAll('.hilo-line:not(.preview)').forEach(l => l.remove());
  const hilos = (estado[idx] || {}).hilos || [];
  const verdes = (estado[idx] || {}).chinchesVerdes || new Set();
  hilos.forEach((h) => {
    const elA = document.querySelector(`[data-chinche-id="${h.a}"]`);
    const elB = document.querySelector(`[data-chinche-id="${h.b}"]`);
    if (!elA || !elB) return;
    const a = chincheCentro(elA);
    const b = chincheCentro(elB);
    const line = document.createElementNS('http://www.w3.org/2000/svg','line');
    line.setAttribute('x1', a.x); line.setAttribute('y1', a.y);
    line.setAttribute('x2', b.x); line.setAttribute('y2', b.y);
    // color del hilo basado en el ORIGEN
    const origenId = h.origen || h.a;
    const esVerde    = verdes.has(origenId);
    const esAmarillo = (estado[idx].chinchesAmarillos || new Set()).has(origenId);
    const esAzul     = (estado[idx].chinchesAzules || new Set()).has(origenId);
    const claseHilo = esVerde ? 'hilo-line verde' : esAmarillo ? 'hilo-line amarilla' : esAzul ? 'hilo-line azul' : 'hilo-line';
    line.setAttribute('class', claseHilo);
    line.style.pointerEvents = 'stroke';
    line.style.cursor = 'pointer';
    const hiloA = h.a, hiloB = h.b;
    line.addEventListener('dblclick', ev => {
      ev.stopPropagation();
      borrarHiloPorIds(idx, hiloA, hiloB);
    });
    svg.insertBefore(line, svg.firstChild);
  });
  actualizarChinchesConHilo(idx);
}

function actualizarChinchesConHilo(idx) {
  const hilos = (estado[idx] || {}).hilos || [];
  const verdes    = (estado[idx] || {}).chinchesVerdes    || new Set();
  const amarillos = (estado[idx] || {}).chinchesAmarillos || new Set();
  const azules    = (estado[idx] || {}).chinchesAzules    || new Set();
  // Solo los ORÍGENES de hilos se ponen rojos; los destinos se quedan como estaban
  const origenes = new Set(hilos.map(h => h.origen || h.a));
  document.querySelectorAll('.chinche').forEach(c => {
    const id = c.getAttribute('data-chinche-id');
    const esVerde    = verdes.has(id);
    const esAmarillo = amarillos.has(id);
    const esAzul     = azules.has(id);
    c.classList.remove('marcada-verde', 'marcada-amarilla', 'marcada-azul', 'tiene-hilo');
    if (esVerde) {
      c.classList.add('marcada-verde');
    } else if (esAmarillo) {
      c.classList.add('marcada-amarilla');
    } else if (esAzul) {
      c.classList.add('marcada-azul');
    } else {
      c.classList.toggle('tiene-hilo', origenes.has(id));
    }
  });
}

function borrarHilo(idx, hiloIdx) {
  estado[idx].hilos.splice(hiloIdx, 1);
  dibujarHilos(idx);
}

function borrarHiloPorIds(idx, a, b) {
  estado[idx].hilos = estado[idx].hilos.filter(
    h => !((h.a === a && h.b === b) || (h.a === b && h.b === a))
  );
  dibujarHilos(idx);
}

// Redibujar al resize
window.addEventListener('resize', () => {
  if (fichaActual !== undefined) dibujarHilos(fichaActual);
});

function borrarTodosLosHilosDe(chincheId) {
  estado[fichaActual].hilos =
    (estado[fichaActual].hilos || []).filter(h => h.a !== chincheId && h.b !== chincheId);
  dibujarHilos(fichaActual);
}

function toggleVerdeYDesconectar(chincheId) {
  if (!estado[fichaActual]) return;
  if (!estado[fichaActual].chinchesVerdes)    estado[fichaActual].chinchesVerdes    = new Set();
  if (!estado[fichaActual].chinchesAmarillos) estado[fichaActual].chinchesAmarillos = new Set();
  if (!estado[fichaActual].chinchesAzules)    estado[fichaActual].chinchesAzules    = new Set();
  const verdes    = estado[fichaActual].chinchesVerdes;
  const amarillos = estado[fichaActual].chinchesAmarillos;
  const azules    = estado[fichaActual].chinchesAzules;

  if (verdes.has(chincheId)) {
    // verde → amarillo (sin tocar hilos)
    verdes.delete(chincheId);
    amarillos.add(chincheId);
  } else if (amarillos.has(chincheId)) {
    // amarillo → azul (sin tocar hilos)
    amarillos.delete(chincheId);
    azules.add(chincheId);
  } else if (azules.has(chincheId)) {
    // azul → apagado (sin tocar hilos)
    azules.delete(chincheId);
  } else {
    // apagado/roja → verde (sin tocar hilos, solo cambia el color)
    verdes.add(chincheId);
  }
  dibujarHilos(fichaActual);
}

function bindChinches() {
  document.querySelectorAll('.chinche').forEach(el => {
    el.addEventListener('dragstart', e => e.preventDefault());

    // doble clic → verde / des-verde y desconectar
    el.ondblclick = (e) => {
      e.stopPropagation();
      e.preventDefault();
      cancelarHilo(); // cancelar cualquier hilo en curso
      toggleVerdeYDesconectar(el.getAttribute('data-chinche-id'));
    };

    // ── TOUCH: toque = seleccionar/conectar (click-click), doble toque = verde ──
    // Se maneja todo directamente con eventos touch (sin depender del click
    // sintético del navegador): preventDefault() en touchstart puede bloquear
    // ese click sintético y eso rompía la confirmación del segundo toque.
    let lastTap = 0;
    let touchMovido = false;

    el.addEventListener('touchstart', e => {
      touchMovido = false;
      e.preventDefault(); // evita zoom/scroll/selección sobre la chinche
    }, { passive: false });

    el.addEventListener('touchmove', () => {
      touchMovido = true; // fue un deslizamiento, no un toque
    }, { passive: true });

    el.addEventListener('touchend', e => {
      e.preventDefault();
      e.stopPropagation();
      if (touchMovido) return;

      const now = Date.now();
      const delta = now - lastTap;
      lastTap = now;

      if (delta < 300 && delta > 0) {
        // doble toque → verde / des-verde y desconectar
        lastTap = 0;
        cancelarHilo();
        toggleVerdeYDesconectar(el.getAttribute('data-chinche-id'));
        return;
      }

      // toque simple → modo click-click
      if (!hiloEstado.activo) {
        // primer toque: marca el origen A
        iniciarHilo(el, false);
      } else {
        // segundo toque: crea (o quita, si ya existía) el segmento A-B
        confirmarHilo(el);
      }
    }, { passive: false });
  });
}

// Touch move → actualizar preview en móvil
document.addEventListener('touchmove', ev => {
  if (!hiloEstado.activo) return;
  const t = ev.touches[0];
  moverPreview(t.clientX, t.clientY);
}, { passive: true });

// Touch end → confirmar si hay destino bajo el dedo
document.addEventListener('touchend', ev => {
  if (!hiloEstado.activo || !hiloEstado.modoArrastre) return;
  const t = ev.changedTouches[0];
  const elSuelta = document.elementFromPoint(t.clientX, t.clientY);
  const chincheDest = elSuelta ? elSuelta.closest('.chinche') : null;
  if (chincheDest && chincheDest !== hiloEstado.origenEl) {
    confirmarHilo(chincheDest);
  } else {
    hiloEstado.modoArrastre = false;
    if (hiloEstado.chincheBajoCursor) {
      hiloEstado.chincheBajoCursor.classList.remove('hover-destino');
      hiloEstado.chincheBajoCursor = null;
    }
  }
}, { passive: true });
