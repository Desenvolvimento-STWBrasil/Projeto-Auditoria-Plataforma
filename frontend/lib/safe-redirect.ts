export function getSafeRedirectPath(
    value: string | null,
    fallbackPath: string,
): string {
    if (!value) return fallbackPath;
    if (!value.startsWith("/")) return fallbackPath;
    if (value.startsWith("//")) return fallbackPath;
    if (value.includes("://")) return fallbackPath;
    return value;
}