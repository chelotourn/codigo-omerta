// ── INICIAR JUEGO ────────────────────────────────────────────────────────────
function iniciarJuego(datos) {
  FICHAS = datos.fichas || [];
  if (!FICHAS.length) { alert('Sin fichas.'); return; }

  const generadoActual = datos.generado || null;
  GENERADO_ACTUAL = generadoActual;
  estado = {};
  FICHAS.forEach((f, i) => {
    const dif = f.dificultad || '';
    const casos = casosHistorial(dif, generadoActual);
    const entrada = casos.find(r => r.fichaId === f.ficha_id);
    estado[i] = {
      seleccion:   entrada ? (entrada.seleccionId || null) : null,
      inocentes:   new Set(),
      marcasVM:    {},
      resuelta:    entrada ? true : false,
      correcto:    entrada ? entrada.correcto : null,
      acusaciones: {},
      hilos:       [],
      chinchesVerdes:    new Set(),
      chinchesAmarillos: new Set(),
      chinchesAzules:    new Set()
    };
  });

  // Precargar imágenes de todos los personajes involucrados, por distrito de cada ficha
  // (en el caso final, cada sospechoso usa su distrito_origen como prefijo de imagen)
  const combos = new Set();
  FICHAS.forEach(f => {
    f.sospechosos_ids.forEach(sid => {
      const distritoId = distritoImagenSospechoso(sid, f);
      combos.add(`${distritoId}:${sid}`);
    });
  });
  combos.forEach(key => {
    const [distritoId, sid] = key.split(':').map(Number);
    precargarImagen(sid, distritoId);
  });

  document.getElementById('pantalla-carga').style.display = 'none';
  document.getElementById('pantalla-juego').style.display = 'block';
  document.getElementById('ornamento-pie').style.display = 'block';
  document.getElementById('pie-info').textContent =
    `${FICHAS.length} caso${FICHAS.length>1?'s':''} cargado${FICHAS.length>1?'s':''}`;

  aplicarTemaNoir();
  renderNav();
  mostrarFicha(0);
}

// ── CASO FINAL (Operación Código Omertá) ────────────────────────────────────
// El caso final se identifica por distrito_id === 3. Sólo se desbloquea
// cuando todos los demás casos de la tanda fueron resueltos correctamente.
function esFichaFinal(f) {
  return f && f.distrito_id === 3;
}

function casoFinalDesbloqueado(idx) {
  // Todas las fichas que no son el caso final deben estar resueltas y correctas.
  return FICHAS.every((f, i) => {
    if (i === idx) return true;
    if (esFichaFinal(f)) return true; // si hubiera más de un "caso final", no se exige entre sí
    return estado[i] && estado[i].resuelta && estado[i].correcto;
  });
}

// ── NAV ──────────────────────────────────────────────────────────────────────
function renderNav() {
  const nav = document.getElementById('nav-fichas');
  nav.querySelectorAll('.btn-ficha, .nav-sep, .btn-reset-nav').forEach(b => b.remove());
  nav.style.display = 'flex';
  if (FICHAS.length <= 1) return;
  const sep = document.createElement('span');
  sep.className = 'nav-sep';
  sep.style.cssText = 'width:1px;height:1.2rem;background:rgba(184,147,58,.2);align-self:center;';
  nav.appendChild(sep);

  FICHAS.forEach((f, i) => {
    const btn = document.createElement('button');
    const dif = f.dificultad || '';
    const casos = casosHistorial(dif, GENERADO_ACTUAL);
    const entrada = casos.find(r => r.fichaId === f.ficha_id);

    let clases = 'btn-ficha';
    if (i === fichaActual) clases += ' activo';
    if (estado[i].resuelta) {
      clases += estado[i].correcto ? ' hist-exito' : ' hist-fracaso';
    } else if (entrada) {
      clases += entrada.correcto ? ' hist-exito' : ' hist-fracaso';
    }

    const esCasoFinal = esFichaFinal(f);
    const bloqueada = esCasoFinal && !casoFinalDesbloqueado(i);
    if (esCasoFinal) clases += ' caso-final';
    if (bloqueada) clases += ' bloqueado';

    btn.className = clases;
    btn.textContent = bloqueada
      ? `🔒 Caso #${String(f.ficha_id).padStart(2,'0')}`
      : `Caso #${String(f.ficha_id).padStart(2,'0')}`;
    btn.disabled = bloqueada;
    btn.title = bloqueada ? 'Este es el caso Final. Tendrás que resolver todos los casos y poner bajo custoria a los sospechosos para desenmascarar a la mente maestra en las sombras.' : '';
    btn.onclick = () => {
      if (bloqueada) {
        alert('Este caso permanece bloqueado. Resolvé correctamente todos los casos anteriores para acceder a él.');
        return;
      }
      mostrarFicha(i);
    };
    nav.appendChild(btn);
  });

  // Botón reset al final
  const btnReset = document.createElement('button');
  btnReset.className = 'btn-reset-nav';
  btnReset.textContent = '↺';
  btnReset.title = 'Reiniciar historial';
  btnReset.onclick = resetHistorial;
  nav.appendChild(btnReset);
}

// ── RENDER PRINCIPAL ─────────────────────────────────────────────────────────
function mostrarFicha(idx) {
  const fSolicitada = FICHAS[idx];
  if (esFichaFinal(fSolicitada) && !casoFinalDesbloqueado(idx)) {
    alert('Este caso permanece bloqueado. Resolvé correctamente todos los casos anteriores para acceder a él.');
    renderNav();
    return;
  }
  fichaActual = idx;
  const f = FICHAS[idx];
  const e = estado[idx];
  renderNav();

  const dif = {urbano:'Urbano', metropoli:'Metrópoli', omerta:'Omertá'}[f.dificultad] || f.dificultad;

  document.getElementById('contenido-ficha').innerHTML = `
    <div class="ficha-header">
      <div class="ficha-numero">${String(f.ficha_id).padStart(2,'0')}</div>
      <div class="ficha-meta">
        <div class="ficha-titulo">TELEGRAMA DEL COMISIONADO</div>
        <div class="ficha-distrito">${f.distrito_nombre || ''}</div>
        <div class="ficha-tags">
          <span class="tag tag-dificultad">Dificultad ${dif}</span>
          <span class="tag tag-info">${f.n_sospechosos} sospechosos</span>
          <span class="tag tag-info">${f.cantidad} verdad${f.cantidad>1?'es':''} en juego</span>
        </div>
      </div>
    </div>

    <div class="seccion-titulo">Sospechosos</div>
    <div class="grid-sospechosos" id="grid-sosp">
      ${f.sospechosos_ids.map(sid => htmlCartaSosp(sid, e, f)).join('')}
    </div>

    <div class="seccion-titulo">Declaraciones</div>
    <div class="lista-declaraciones" id="lista-decl">
      ${f.declaraciones.map(d => htmlDeclaracion(d, e)).join('')}
    </div>

    <div class="zona-accion">
      <div class="accion-pregunta">¿Quién cometió el crimen?</div>
      <div class="accion-seleccion" id="txt-seleccion">
        ${e.seleccion ? `→ ${NOMBRES[e.seleccion]||e.seleccion}` : 'Seleccioná un sospechoso para acusar.'}
      </div>
      <button class="btn-acusar ${e.seleccion && !e.resuelta ? 'visible':''}"
              id="btn-acusar" onclick="acusar(${idx})">
        ◆ Acusar formalmente
      </button>
    </div>

    <div class="resultado ${e.resuelta?(e.correcto?'correcto':'incorrecto'):''}"
         id="resultado" style="${e.resuelta?'display:block':'display:none'}">
      <div class="resultado-titulo ${e.correcto && esFichaFinal(f) ? 'titulo-omerta-roto' : ''}">${e.correcto ? (esFichaFinal(f) ? 'El Omertá se ha Roto' : 'Buen Trabajo Detective') : 'Acusación incorrecta'}</div>
      <div class="resultado-detalle">${e.resuelta?htmlResultado(f,e):''}</div>
    </div>

    ${e.resuelta
      ? `<div class="acciones-post-resultado">
           ${idx < FICHAS.length-1 ? `<button class="btn-sec" onclick="mostrarFicha(${idx+1})">Siguiente caso →</button>` : ''}
           <button class="btn-sec btn-reiniciar-caso" onclick="reiniciarCasoActual(${idx})">↺ Reiniciar Caso</button>
         </div>`
      : ''}
  `;

  // Aplicar imágenes ya cacheadas
  f.sospechosos_ids.forEach(sid => {
    const distritoId = distritoImagenSospechoso(sid, f);
    if (imagenCacheada(sid, distritoId)) actualizarAvatares(sid, distritoId);
  });

  // Bind de eventos (sólo si no está resuelta)
  if (!e.resuelta) {
    document.querySelectorAll('.carta-sospechoso').forEach(card => {
      card.addEventListener('click', ev => {
        // no propagar si clic viene del botón interno, chinche o acusaciones
        if (ev.target.closest('.btn-toggle-inocente')) return;
        if (ev.target.closest('.chinche')) return;
        if (ev.target.closest('.acusaciones-wrap')) return;
        clickSosp(idx, parseInt(card.dataset.sospId));
      });
    });
    document.querySelectorAll('.btn-toggle-inocente').forEach(btn => {
      btn.addEventListener('click', ev => {
        ev.stopPropagation();
        toggleInocente(idx, parseInt(btn.dataset.sid));
      });
    });
    document.querySelectorAll('.btn-acus-mas').forEach(btn => {
      btn.addEventListener('click', ev => {
        ev.stopPropagation();
        cambiarAcusacion(idx, parseInt(btn.dataset.sid), 1);
      });
    });
    document.querySelectorAll('.btn-acus-menos').forEach(btn => {
      btn.addEventListener('click', ev => {
        ev.stopPropagation();
        cambiarAcusacion(idx, parseInt(btn.dataset.sid), -1);
      });
    });
    document.querySelectorAll('.btn-vm').forEach(btn => {
      btn.addEventListener('click', () => {
        // Guarda anti-doble-disparo: algunos navegadores móviles emiten
        // dos eventos 'click' para un mismo toque (ghost click / doble-tap-zoom).
        // Sin esto, el ciclo null→v→amarillo→null podía "saltarse" el null
        // (amarillo→null→v en el mismo toque) y dar la sensación de que
        // el botón nunca vuelve a gris.
        // También actúa como guarda frente al doble clic real de mouse: el
        // segundo 'click' de un dblclick cae dentro de la ventana y se ignora,
        // dejando que sea el evento 'dblclick' quien decida el resultado final.
        const ahora = Date.now();
        if (btn._ultimoToqueVM && ahora - btn._ultimoToqueVM < 350) return;
        btn._ultimoToqueVM = ahora;
        marcarVM(idx, parseInt(btn.dataset.carta), btn.dataset.vm);
      });
      // Doble clic en V o en M → ambos (V y M de esa misma declaración) a amarillo
      btn.addEventListener('dblclick', ev => {
        ev.preventDefault();
        ev.stopPropagation();
        btn._ultimoToqueVM = Date.now(); // evita que un click residual reabra el ciclo normal
        marcarAmbosAmarillo(idx, parseInt(btn.dataset.carta));
      });
    });
    // Clic en nombre del personaje en declaraciones = ciclo 3 estados: normal → inocente → culpable → normal
    document.querySelectorAll('.decl-nombre[data-sosp-id]').forEach(el => {
      el.addEventListener('click', ev => {
        ev.stopPropagation();
        const sid = parseInt(el.dataset.sospId);
        const e = estado[idx];
        const esInocente = e.inocentes.has(sid);
        const esCulpable = e.culpables && e.culpables.has(sid);

        if (!esInocente && !esCulpable) {
          // normal → inocente
          e.inocentes.add(sid);
          if (e.seleccion === sid) e.seleccion = null;
          actualizarCartas(idx);
          actualizarBotonAcusar(idx);
        } else if (esInocente) {
          // inocente → culpable
          e.inocentes.delete(sid);
          if (!e.culpables) e.culpables = new Set();
          e.culpables.add(sid);
          actualizarCartas(idx);
          actualizarBotonAcusar(idx);
        } else {
          // culpable → normal
          e.culpables.delete(sid);
        }

        // Sincronizar clases en todos los decl-nombre de este sospechoso
        document.querySelectorAll(`.decl-nombre[data-sosp-id="${sid}"]`).forEach(n => {
          n.classList.remove('inocente-decl', 'culpable-decl');
          if (estado[idx].inocentes.has(sid)) n.classList.add('inocente-decl');
          else if (estado[idx].culpables && estado[idx].culpables.has(sid)) n.classList.add('culpable-decl');
        });
      });
    });
  }

  // Siempre: bind chinches y dibujar hilos guardados
  bindChinches();
  // Pequeño delay para que el DOM esté listo antes de calcular coordenadas
  setTimeout(() => dibujarHilos(idx), 30);
}

// ── HTML CARTA SOSPECHOSO ────────────────────────────────────────────────────
function htmlCartaSosp(sid, e, f) {
  let cls = 'carta-sospechoso';
  let badge = '';
  let bloq = '';

  if (e.resuelta) {
    cls += sid === f.culpable_id ? ' culpable-revelado bloqueada' : ' inocente-revelado bloqueada';
    if (sid === f.culpable_id) badge = '<div class="badge-culpable">Culpable</div>';
    bloq = 'bloqueada';
  } else {
    if (e.inocentes.has(sid))  cls += ' inocente-marcado';
    else if (e.seleccion===sid) cls += ' sospechado';
  }

  const sosp = f.declaraciones.find(d => d.sospechoso_id===sid) || {};
  const distritoImg = distritoImagenSospechoso(sid, f);
  const avatarUrl = imagenCacheada(sid, distritoImg);
  const avatarInner = avatarUrl
    ? `<img src="${avatarUrl}" alt="${NOMBRES[sid]||''}">`
    : `<div class="avatar-emoji">${EMOJIS[sid]||'?'}</div>`;

  const btnInocente = (!e.resuelta)
    ? `<button class="btn-toggle-inocente" data-sid="${sid}">
         ${e.inocentes.has(sid) ? '↩ Quitar inocente' : '✕ Marcar inocente'}
       </button>` : '';

  const acusCount = (e.acusaciones && e.acusaciones[sid]) || 0;
  const dots = Array.from({length: acusCount}, () => `<span class="acus-dot"></span>`).join('');
  const acusaciones = (!e.resuelta)
    ? `<div class="acusaciones-wrap">
         <div class="acusaciones-label">Acusaciones</div>
         <div class="acusaciones-ctrl">
			<button class="btn-acus btn-acus-menos" data-sid="${sid}">−</button>
            <div class="acusaciones-num" id="acus-num-${sid}">${acusCount}</div>
            <button class="btn-acus btn-acus-mas" data-sid="${sid}">+</button>
		</div>
         <div class="acusaciones-dots" id="acus-dots-${sid}">${dots}</div>
       </div>` : '';

  return `
    <div class="${cls}" data-sosp-id="${sid}" data-distrito-id="${distritoImg}">
      ${badge}
      <div class="chinche-bar">
        <span class="chinche-bar-label">${NOMBRES[sid]||''}</span>
        <div class="chinche-row">
          <div class="chinche" data-chinche-id="s${sid}-0" title="Conectar hilo"></div>

        </div>
        <div class="chinche-row">

          <div class="chinche" data-chinche-id="s${sid}-3" title="Conectar hilo"></div>
        </div>
      </div>
      <div class="avatar-wrap">${avatarInner}</div>
      ${acusaciones}
      ${btnInocente}
    </div>`;
}

// ── RESALTAR PALABRA "OMERTÁ" ────────────────────────────────────────────────
function resaltarOmerta(texto) {
  if (!texto) return texto;
  // Coincide con Omertá / Omerta / OMERTÁ / omertá, etc. (con o sin tilde, cualquier capitalización)
  return texto.replace(/omert[áa]/gi, (match) => `<span style="color:#9b2020; font-weight:600;">${match}</span>`);
}

// ── HTML DECLARACIÓN ─────────────────────────────────────────────────────────
function htmlDeclaracion(d, e) {
  let cls = 'declaracion';
  let marcadorHTML = '';

  if (e.resuelta) {
    // revelación final
    if (d.silenciada) {
      cls += ' silenciada-revelada';
      marcadorHTML = `<div class="decl-vm-resultado s" title="Silenciada por Omertá">·</div>`;
    } else {
      cls += d.es_verdad ? ' verdad-revelada' : ' mentira-revelada';
      const vm = d.es_verdad ? 'v' : 'm';
      marcadorHTML = `<div class="decl-vm-resultado ${vm}">${vm.toUpperCase()}</div>`;
    }
  } else {
    // botones interactivos V / M
    const marcaActual = e.marcasVM[d.carta_id] || null;
    const ambosAmarillo = marcaActual === 'ambos_amarillo';
    const vCls = ambosAmarillo ? 'amarillo' : (marcaActual === 'v' ? 'activo' : (marcaActual === 'v_amarillo' ? 'amarillo' : ''));
    const mCls = ambosAmarillo ? 'amarillo' : (marcaActual === 'm' ? 'activo' : (marcaActual === 'm_amarillo' ? 'amarillo' : ''));
    marcadorHTML = `
      <div class="decl-marcador">
        <button class="btn-vm v-btn ${vCls}"
                data-carta="${d.carta_id}" data-vm="v" title="Marcar verdad">V</button>
        <button class="btn-vm m-btn ${mCls}"
                data-carta="${d.carta_id}" data-vm="m" title="Marcar mentira">M</button>
      </div>`;
  }

  return `
    <div class="${cls}">
		 
      <div>
		  <div class="decl-id">#${String(d.carta_id).padStart(2,'0')}</div>
	      <div style="margin-left: 5px;" class="chinche" data-chinche-id="d${d.carta_id}-4" title="Conectar hilo"></div>
	  </div>

      <div class="decl-cuerpo">
        <div class="decl-topbar">
          <div>
            <div class="decl-persona">
             <div class="decl-nombre${e.inocentes && e.inocentes.has(d.sospechoso_id) ? ' inocente-decl' : ''}" data-sosp-id="${d.sospechoso_id}">${d.sospechoso}</div>
			 <span class="decl-atrib">${d.edad || ''},</span>
             <span class="decl-atrib">${d.clase || ''}</span>

            </div>
            <div class="decl-cat">${d.carta_categoria}</div>
          </div>
          <div class="decl-chinches-bar">
            <div class="chinche" data-chinche-id="d${d.carta_id}-0" title="Conectar hilo"></div>
            <div class="chinche" data-chinche-id="d${d.carta_id}-1" title="Conectar hilo"></div>
            <div class="chinche" data-chinche-id="d${d.carta_id}-2" title="Conectar hilo"></div>
           </div>
        </div>
        <div class="decl-texto">"${resaltarOmerta(d.carta_texto)}"</div>
      </div>
      ${marcadorHTML}
    </div>`;
}

// ── HTML RESULTADO ───────────────────────────────────────────────────────────
function htmlResultado(f, e) {
  const vm = f.declaraciones
    .map(d => {
      const etiqueta = d.silenciada ? '<span style="opacity:.45" title="Silenciada por Omertá">·</span>' : (d.es_verdad ? 'V' : 'M');
      return `<strong>${d.sospechoso.split(' ').pop()}</strong>: ${etiqueta}`;
    })
    .join(' &nbsp;·&nbsp; ');
  if (e.correcto) {
    return esFichaFinal(f)
      ? `${f.culpable_nombre} era la mano que movía los hilos: &nbsp; ${vm}`
      : `${f.culpable_nombre} esta bajo custodia: &nbsp; ${vm}`;
  }
  return `El culpable era <strong>${f.culpable_nombre}</strong>. Acusaste a ${NOMBRES[e.seleccion]||'?'}. &nbsp; ${vm}`;
}

