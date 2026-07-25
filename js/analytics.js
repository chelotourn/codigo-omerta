// ============================================================
// Tracking propio (reemplazo/complemento de Umami)
// Envía eventos directamente a Supabase, sin depender de scripts
// de terceros que los bloqueadores de rastreadores suelen frenar.
// ============================================================

// 1. Completá estos dos valores con los de TU proyecto Supabase
//    (Project Settings → API → "Project URL" y "anon public" key)
const SUPABASE_URL = 'https://bpempqucqtitqzaihtoc.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwZW1wcXVjcXRpdHF6YWlodG9jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ5MzA1MDMsImV4cCI6MjEwMDUwNjUwM30.jBqIkYfGOaYtI2gjQKbUbGhfzhjawPgfq4EpVo_K_Go';

/**
 * Envía un evento a la tabla eventos_omerta.
 * No bloquea ni interrumpe el juego si falla (fire-and-forget).
 * @param {'dificultad_click'|'acusacion'} tipo
 * @param {{dificultad?: string, caso?: number, acierto?: boolean}} datos
 */
function trackEvento(tipo, datos = {}) {
  try {
    fetch(`${SUPABASE_URL}/rest/v1/eventos_omerta`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({ tipo, ...datos }),
      keepalive: true, // permite que el request termine aunque cambies de pantalla
    }).catch(() => {}); // si falla (sin conexión, etc.) no rompemos el juego
  } catch (err) {
    // silencioso: el tracking nunca debe afectar la experiencia de juego
  }
}
