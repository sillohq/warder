import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwind from '@tailwindcss/vite'

// One JavaScript file and one stylesheet, deliberately.
//
// The admin is served under a prefix the application chooses, so a build with
// code-splitting would have to resolve chunk URLs against a base it cannot
// know until runtime. Inlining every dynamic import removes the question:
// there is nothing to resolve, the tags are emitted from the manifest with the
// right prefix, and the admin works under /admin, /ops or /internal/admin
// without a rebuild.
//
// It also happens to be right for the artefact: an admin is opened once and
// used all day, so one request that warms the cache beats six that split it.
export default defineConfig({
  plugins: [react(), tailwind()],
  build: {
    outDir: '../warder/static',
    emptyOutDir: true,
    manifest: 'manifest.json',
    target: 'es2022',
    rollupOptions: {
      input: 'src/main.tsx',
      output: {
        inlineDynamicImports: true,
        entryFileNames: 'warder.[hash].js',
        assetFileNames: 'warder.[hash][extname]',
      },
    },
  },
})
