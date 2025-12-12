import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000, // Porta per lo sviluppo (cambia questo valore se necessario)
    strictPort: false, // Se la porta è occupata, prova la successiva
  },
  preview: {
    port: 4173, // Porta per il preview (build di produzione)
    strictPort: false,
  },
})
