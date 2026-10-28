// Pure helpers for the one-step generate card: what counts as a link or an audio file.
export const AUDIO_EXTENSIONS = [".mp3", ".wav", ".ogg", ".egg", ".flac", ".m4a"] as const;
export const AUDIO_ACCEPT = [...AUDIO_EXTENSIONS, "audio/*"].join(",");
export const AUDIO_HINT = "mp3, wav, ogg, flac or m4a";

/** True for an http(s) link; the server decides whether the host is YouTube. */
export function isLink(text: string): boolean {
  try {
    const url = new URL(text.trim());
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

/** True when the file has an audio type or a known audio extension. */
export function isAudioFile(file: { name: string; type: string }): boolean {
  const name = file.name.toLowerCase();
  return file.type.startsWith("audio/") || AUDIO_EXTENSIONS.some((ext) => name.endsWith(ext));
}

/** The id of the finished map in a generate job result, or null when it has none. */
export function resultMapId(result: Record<string, unknown> | null): string | null {
  const id = result?.["map_id"];
  return typeof id === "string" && id !== "" ? id : null;
}
