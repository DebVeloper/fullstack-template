import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "http://localhost:8000/openapi.json",
  output: "src/client",
  plugins: [
    "@hey-api/typescript",
    {
      name: "@hey-api/sdk",
      operations: {
        nesting: "id"
      },
      responseStyle: "data"
    },
    {
      name: "@hey-api/client-fetch",
      runtimeConfigPath: "../lib/api-client"
    }
  ]
})
