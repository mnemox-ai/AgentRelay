export const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`);
  if (!res.ok) {
    const error = new Error(`API error: ${res.status} ${res.statusText}`);
    throw error;
  }
  return res.json();
}
