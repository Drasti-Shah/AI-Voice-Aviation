// Demo-grade client-side auth. NOT secure — swap for real backend auth
// (JWT/session) before any production use. Credentials are hardcoded here.
const AUTH_KEY = "aviation_auth";

// Default demo credentials. Override via NEXT_PUBLIC_LOGIN_USER / _PASS.
const USER = process.env.NEXT_PUBLIC_LOGIN_USER ?? "admin";
const PASS = process.env.NEXT_PUBLIC_LOGIN_PASS ?? "admin123";

export function login(username: string, password: string): boolean {
  if (username === USER && password === PASS) {
    if (typeof window !== "undefined") localStorage.setItem(AUTH_KEY, "1");
    return true;
  }
  return false;
}

export function logout(): void {
  if (typeof window !== "undefined") localStorage.removeItem(AUTH_KEY);
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(AUTH_KEY) === "1";
}
