const IS_PRODUCTION = process.env.NODE_ENV === "production";

const ACCESS_TOKEN_MAX_AGE_SECONDS = 60 * 15;
const REFRESH_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

type CookieStore = Pick<
  Awaited<ReturnType<typeof import("next/headers").cookies>>,
  "set"
>;

interface AuthCookieOptions {
  httpOnly: true;
  secure: boolean;
  sameSite: "lax";
  path: string;
  maxAge: number;
}

const ACCESS_TOKEN_COOKIE_OPTIONS: AuthCookieOptions = {
  httpOnly: true,
  secure: IS_PRODUCTION,
  sameSite: "lax",
  path: "/",
  maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS
};

const REFRESH_TOKEN_COOKIE_OPTIONS: AuthCookieOptions = {
  httpOnly: true,
  secure: IS_PRODUCTION,
  sameSite: "lax",
  path: "/api",
  maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS
};

const CLEAR_ACCESS_TOKEN_COOKIE_OPTIONS: AuthCookieOptions = {
  ...ACCESS_TOKEN_COOKIE_OPTIONS,
  maxAge: 0
};

const CLEAR_REFRESH_TOKEN_COOKIE_OPTIONS: AuthCookieOptions = {
  ...REFRESH_TOKEN_COOKIE_OPTIONS,
  maxAge: 0
};

export function setAuthCookies(cookieStore: CookieStore, tokens: AuthTokens): void {
  cookieStore.set("access_token", tokens.access_token, ACCESS_TOKEN_COOKIE_OPTIONS);
  cookieStore.set("refresh_token", tokens.refresh_token, REFRESH_TOKEN_COOKIE_OPTIONS);
}

export function clearAuthCookies(cookieStore: CookieStore): void {
  cookieStore.set("access_token", "", CLEAR_ACCESS_TOKEN_COOKIE_OPTIONS);
  cookieStore.set("refresh_token", "", CLEAR_REFRESH_TOKEN_COOKIE_OPTIONS);
}
