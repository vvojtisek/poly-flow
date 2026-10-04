// Values are inlined at build time by next.config.ts (`env`), so they describe this frontend build.
export type BuildInfo = {
  version: string;
  prerelease: boolean;
  commit: string;
  branch: string;
  builtAt: string | null;
  devServer: boolean;
};

export function shortSha(sha: string): string {
  const dirty = sha.endsWith("-dirty");
  const head = dirty ? sha.slice(0, -"-dirty".length) : sha;
  if (!/^[0-9a-f]{7,}$/i.test(head)) return sha;
  return head.slice(0, 7) + (dirty ? "-dirty" : "");
}

export const buildInfo: BuildInfo = {
  version: process.env.NEXT_PUBLIC_APP_VERSION ?? "unknown",
  // SemVer: a hyphenated suffix (1.0.0-alpha.1) marks a pre-release.
  prerelease: (process.env.NEXT_PUBLIC_APP_VERSION ?? "-").includes("-"),
  commit: shortSha(process.env.NEXT_PUBLIC_GIT_SHA ?? "unknown"),
  branch: process.env.NEXT_PUBLIC_GIT_BRANCH ?? "unknown",
  builtAt: process.env.NEXT_PUBLIC_BUILD_TIME || null,
  devServer: process.env.NODE_ENV !== "production",
};
