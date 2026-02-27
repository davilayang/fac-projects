import { z } from "zod";

const envSchema = z.object({
  VITE_AGENT_NAME: z.string().min(1),
  VITE_APIVIDEO_API_KEY: z.string().min(1),
});

const rawConfigs = {
  VITE_AGENT_NAME: import.meta.env.VITE_AGENT_NAME,
  VITE_APIVIDEO_API_KEY: import.meta.env.VITE_APIVIDEO_API_KEY,
};

function parseEnv() {
  const result = envSchema.safeParse(rawConfigs);

  if (!result.success) {
    const missing = result.error.issues.map((issue) => issue.path.join("."));
    throw new Error(
      "[eva:config] Missing or invalid environment variables:\n" +
        missing.map((v) => `  • ${v}`).join("\n") +
        "\n  Add them to your .env.local file.",
    );
  }

  return result.data;
}

export const env = parseEnv();
