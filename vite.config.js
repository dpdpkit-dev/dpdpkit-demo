// Builds the React demos into app/static/dist, which the FastAPI site serves.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  build: {
    outDir: "app/static/dist",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: { output: { entryFileNames: "[name].js" } },
    lib: { entry: { "fastapi-demo": "frontend/fastapi-demo.jsx", "client-demo": "frontend/client-demo.js" }, formats: ["es"], cssFileName: "fastapi-demo" },
  },
});
