---
agent_id: nextjs
---
# Next.js integration details

## API route handler
App Router:
```ts
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth);
```

Pages Router:
```ts
import { auth } from "@/lib/auth";
import { toNodeHandler } from "better-auth/node";

export const config = { api: { bodyParser: false } };
export default toNodeHandler(auth.handler);
```

## Server actions and RSC
Use `auth.api` with `headers()` to access the session.

```tsx
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

export async function ServerComponent() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) return <div>Not authenticated</div>;
  return <div>Welcome {session.user.name}</div>;
}
```

## Cookie handling in server actions
Add `nextCookies` as the last plugin so server actions set cookies:

```ts
import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";

export const auth = betterAuth({
  plugins: [nextCookies()],
});
```

## Middleware / proxy
For Next.js 16+ proxy, avoid full DB checks in edge paths unless you opt into Node runtime.

Cookie-only check:
```ts
import { NextResponse } from "next/server";
import { getSessionCookie } from "better-auth/cookies";

export async function proxy(request: Request) {
  const sessionCookie = getSessionCookie(request);
  if (!sessionCookie) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}
```
