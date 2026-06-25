function volverInicio() {
  FICHAS = [];
  estado = {};
  fichaActual = 0;
  document.getElementById('pantalla-juego').style.display = 'none';
  document.getElementById('ornamento-pie').style.display = 'none';
  document.getElementById('pantalla-carga').style.display = 'flex';
  document.getElementById('pie-info').textContent = '';
  document.getElementById('contenido-ficha').innerHTML = '';
  // limpiar btn-ficha del nav para próxima vez
  document.getElementById('nav-fichas').querySelectorAll('.btn-ficha').forEach(b => b.remove());
  // resetear input file por si quieren cargar el mismo archivo
  document.getElementById('input-json').value = '';
  // detener la música: en la pantalla inicial no debe sonar
  controlarAudioNoir();
}

// ── CONSTANTES ──────────────────────────────────────────────────────────────
const NOMBRES = {
  1:"El Notario", 2:"La Aprendiz", 3:"El Carnicero",
  4:"El Coronel", 5:"La Vidente", 6:"El Médico",
  7:"El Heredero", 8:"El Crupier", 9:"El Vagabundo"
};
const EMOJIS = { 1:"📜", 2:"🔍", 3:"🔪", 4:"⭐", 5:"🔮", 6:"⚕", 7:"💰", 8:"🂡", 9:"🎩" };

// Ruta base de assets — busca pj_1.png, pj_2.png … en carpeta assets/
const ASSETS_PATH = 'assets/';

const NOIR_STORAGE_KEY = 'codigo_omerta_noir_level';
let noirLevel = Math.min(4, Math.max(1, parseInt(localStorage.getItem(NOIR_STORAGE_KEY) || '1', 10) || 1));
let noirAudio = null;

let FICHAS = [];
let fichaActual = 0;
let GENERADO_ACTUAL = null; // timestamp del JSON cargado
// estado por ficha: { seleccion, inocentes:Set, marcasVM:{cartaId:'v'|'m'|null}, resuelta, correcto }
let estado = {};
// caché de URLs de imágenes individuales { sid: url|null }
const imgCache = {};

// ── CARGA DE IMÁGENES INDIVIDUALES ──────────────────────────────────────────
// Intenta cargar assets/pj_{distrito_id}_{sid}.png. Si no existe, usa emoji.
// El distrito_id varía la skin del personaje según el distrito de la ficha actual.
function urlImagenSospechoso(sid, distritoId) {
  return `${ASSETS_PATH}pj_${distritoId}_${sid}.png`;
}

// En el caso final (distrito_id 3), cada sospechoso arrastra su distrito_origen
// (el distrito del caso donde apareció originalmente) y ese es el prefijo de
// imagen a usar, para mantener su skin habitual en vez de una skin "distrito 3".
function distritoImagenSospechoso(sid, f) {
  if (esFichaFinal(f)) {
    const decl = (f.declaraciones || []).find(d => d.sospechoso_id === sid);
    if (decl && decl.distrito_origen != null) return decl.distrito_origen;
  }
  return f.distrito_id;
}

function precargarImagen(sid, distritoId) {
  const key = `${distritoId}:${sid}`;
  if (key in imgCache) return;
  imgCache[key] = null; // marca como "intentado"
  const url = urlImagenSospechoso(sid, distritoId);
  const img = new Image();
  img.onload  = () => { imgCache[key] = url; actualizarAvatares(sid, distritoId); };
  img.onerror = () => { imgCache[key] = null; };
  img.src = url;
}

function imagenCacheada(sid, distritoId) {
  return imgCache[`${distritoId}:${sid}`] || null;
}

function actualizarAvatares(sid, distritoId) {
  document.querySelectorAll(`[data-sosp-id="${sid}"][data-distrito-id="${distritoId}"] .avatar-wrap`).forEach(wrap => {
    const url = imagenCacheada(sid, distritoId);
    if (url) {
      wrap.innerHTML = `<img src="${url}" alt="${NOMBRES[sid]||''}">`;
    } else {
      wrap.innerHTML = `<div class="avatar-emoji">${EMOJIS[sid]||'?'}</div>`;
    }
  });
}

// ── CARGA DE ARCHIVO JSON ────────────────────────────────────────────────────
document.getElementById('input-json').addEventListener('change', e => {
  if (e.target.files[0]) leerJSON(e.target.files[0]);
});
const dropZona = document.getElementById('zona-drop');
dropZona.addEventListener('dragover', e => { e.preventDefault(); dropZona.style.borderColor='var(--oro-viejo)'; });
dropZona.addEventListener('dragleave', () => { dropZona.style.borderColor=''; });
dropZona.addEventListener('drop', e => { e.preventDefault(); dropZona.style.borderColor='';
  if (e.dataTransfer.files[0]) leerJSON(e.dataTransfer.files[0]); });

function leerJSON(file) {
  const r = new FileReader();
  r.onload = e => {
    try { iniciarJuego(JSON.parse(e.target.result)); }
    catch { alert('Archivo JSON inválido.'); }
  };
  r.readAsText(file);
}

function cargarJSON(url) {
  fetch(url)
    .then(r => {
      if (!r.ok) throw new Error(`No se pudo cargar ${url}`);
      return r.json();
    })
    .then(datos => iniciarJuego(datos))
    .catch(() => alert(`No se encontró el archivo:\n${url}`));
}

function aplicarTemaNoir() {
  document.body.classList.remove('noir-1', 'noir-2', 'noir-3', 'noir-4');
  document.body.classList.add(`noir-${noirLevel}`);
  const noirNum = document.getElementById('noir-num');
  if (noirNum) noirNum.textContent = String(noirLevel);
  const btnMenos = document.getElementById('noir-menos');
  const btnMas = document.getElementById('noir-mas');
  if (btnMenos) btnMenos.disabled = noirLevel <= 1;
  if (btnMas) btnMas.disabled = noirLevel >= 4;
  try { localStorage.setItem(NOIR_STORAGE_KEY, String(noirLevel)); } catch {}
  controlarAudioNoir();
}

function controlarAudioNoir() {
  const audio = document.getElementById('noir-audio');
  if (!audio) return;

  // La música solo suena dentro de un caso (pantalla de juego).
  // En la pantalla inicial se mantiene en silencio aunque el nivel noir sea 3 o 4.
  const pantallaJuego = document.getElementById('pantalla-juego');
  const enJuego = !!pantallaJuego && getComputedStyle(pantallaJuego).display !== 'none';
  if (!enJuego) {
    audio.pause?.();
    try {
      audio.removeAttribute('src');
      audio.load?.();
      audio.currentTime = 0;
    } catch {}
    return;
  }

  // Niveles 1, 2: sin música
  if (noirLevel < 3) {
    audio.pause?.();
    try {
      audio.removeAttribute('src');
      audio.load?.();
      audio.currentTime = 0;
    } catch {}
    return;
  }

  // Nivel 3: noir_omerta.mp3 / Nivel 4: noir_omerta_n.mp3
  const baseNombre = noirLevel === 4 ? 'noir_omerta_n' : 'noir_omerta';

  const candidatos = [
    `${ASSETS_PATH}${baseNombre}.mp3`,
    `${ASSETS_PATH}${baseNombre}.ogg`,
    `${ASSETS_PATH}${baseNombre}.wav`,
    `${ASSETS_PATH}${baseNombre}.mid`,
    `${ASSETS_PATH}${baseNombre}.midi`
  ];

  const mime = {
    '.mp3': 'audio/mpeg',
    '.ogg': 'audio/ogg',
    '.wav': 'audio/wav',
    '.mid': 'audio/midi',
    '.midi': 'audio/midi'
  };

  // Guardar estado del intento para evitar listeners duplicados
  const st = audio._noirState || (audio._noirState = {});
  if (st.onError) {
    audio.removeEventListener('error', st.onError);
  }

  const elegirSiguiente = () => {
    const i = typeof st.i === 'number' ? st.i + 1 : 0;
    const src = candidatos[i];
    if (!src) {
      console.warn('No hay formato de audio compatible para Noir.');
      return false;
    }

    st.i = i;
    const ext = src.slice(src.lastIndexOf('.')).toLowerCase();
    const support = audio.canPlayType?.(mime[ext] || '') || '';
    const puedeIntentarse = support !== '' || ext === '.mid' || ext === '.midi';

    if (!puedeIntentarse) {
      return elegirSiguiente();
    }

    const abs = new URL(src, location.href).href;
    if (audio.src !== abs) {
      audio.src = src;
    }
    audio.volume = 0.6;
    audio.loop = true;
    audio.load?.();

    audio.play?.().catch(() => {});
    return true;
  };

  st.onError = () => {
    elegirSiguiente();
  };

  audio.addEventListener('error', st.onError);

  st.i = -1;
  elegirSiguiente();
}

function ajustarNoir(delta) {
  const nuevo = Math.max(1, Math.min(4, noirLevel + delta));
  if (nuevo === noirLevel) return;
  noirLevel = nuevo;
  aplicarTemaNoir();
}

document.addEventListener('click', (ev) => {
  const btn = ev.target.closest?.('#noir-menos, #noir-mas');
  if (!btn) return;
  ev.preventDefault();
  ajustarNoir(btn.id === 'noir-mas' ? 1 : -1);
});

// Aplicar tema inicial
aplicarTemaNoir();

