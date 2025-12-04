import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '')
  const agentUrl = env.VITE_AGENT_URL || 'http://localhost:5000'

  return {
    server: {
      host: true, // Listen on all addresses
      port: 5173,
      proxy: {
        '/api': {
          target: agentUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        },
        // Proxy other endpoints if they are not under /api but directly on root in the current agent setup
        '/health': agentUrl,
        '/login': agentUrl,
        '/register': agentUrl,
        '/chat': agentUrl,
        '/instance': agentUrl,
        '/reset': agentUrl
      }
    }
  }
})
