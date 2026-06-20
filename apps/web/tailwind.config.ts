import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0a0e1a",
        panel: "#111726",
        accent: "#5b8cff",
      },
    },
  },
  plugins: [],
};

export default config;
