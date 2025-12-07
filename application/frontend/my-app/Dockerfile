FROM oven/bun:1 AS base

WORKDIR /app

# Install dependencies
# We use package-lock.json if present, or bun.lockb
COPY package.json package-lock.json* bun.lockb* ./
RUN bun install --frozen-lockfile || bun install

# Copy source
COPY . .

# Build the app
RUN bun run build

# Production image
FROM oven/bun:1 AS runner
WORKDIR /app

ENV NODE_ENV=production

# Copy necessary files for running Next.js standalone or default
# For simplicity with bun, we'll just run next start from the build 
# (Note: standalone output is better for docker size but requires copy logic)
# Let's keep it simple: copy everything and run. 
# Optimization: In a real app we'd copy .next/standalone but that requires next.config.js output: 'standalone'
# To be safe with "Next.js starter", we just copy the build artifacts.

COPY --from=base /app/public ./public
COPY --from=base /app/.next ./.next
COPY --from=base /app/node_modules ./node_modules
COPY --from=base /app/package.json ./package.json

EXPOSE 3000

CMD ["bun", "run", "start"]
