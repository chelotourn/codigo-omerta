// ============================================================
// Tracking propio (reemplazo/complemento de Umami)
// Envía eventos directamente a Supabase, sin depender de scripts
// de terceros que los bloqueadores de rastreadores suelen frenar.
// ============================================================

// 1. Completá estos dos valores con los de TU proyecto Supabase
//    (Project Settings → API → "Project URL" y "anon public" key)
const SUPABASE_URL = 'https://bpempqucqtitqzaihtoc.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwZW1wcXVjcXRpdHF6YWlodG9jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ5MzA1MDMsImV4cCI6MjEwMDUwNjUwM30.jBqIkYfGOaYtI2gjQKbUbGhfzhjawPgfq4EpVo_K_Go';

const VISITANTE_STORAGE_KEY = 'codigo_omerta_visitante_id';

/**
 * Devuelve un ID random para este navegador. Se genera una sola vez
 * y se guarda en localStorage, así el mismo visitante (mismo navegador,
 * mismo dispositivo) mantiene el mismo ID entre visitas.
 * No identifica a la persona: es un ID anónimo local al dispositivo.
 */
function obtenerVisitanteId() {
  try {
    let id = localStorage.getItem(VISITANTE_STORAGE_KEY);
    if (!id) {
      id = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2));
      localStorage.setItem(VISITANTE_STORAGE_KEY, id);
    }
    return id;
  } catch (err) {
    return null; // ej: localStorage bloqueado por el navegador
  }
}

/**
 * Envía un evento a la tabla eventos_omerta.
 * No bloquea ni interrumpe el juego si falla (fire-and-forget).
 * Agrega automáticamente datos del navegador/dispositivo a cada evento.
 * @param {'dificultad_click'|'acusacion'} tipo
 * @param {{dificultad?: string, caso?: number, acierto?: boolean}} datos
 */
function trackEvento(tipo, datos = {}) {
  try {
    const cuerpo = {
      tipo,
      ...datos,
      visitante_id: obtenerVisitanteId(),
      user_agent: navigator.userAgent || null,
      idioma: navigator.language || null,
      pantalla: `${screen.width}x${screen.height}`,
    };

    fetch(`${SUPABASE_URL}/rest/v1/eventos_omerta`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify(cuerpo),
      keepalive: true, // permite que el request termine aunque cambies de pantalla
    }).catch(() => {}); // si falla (sin conexión, etc.) no rompemos el juego
  } catch (err) {
    // silencioso: el tracking nunca debe afectar la experiencia de juego
  }
}
