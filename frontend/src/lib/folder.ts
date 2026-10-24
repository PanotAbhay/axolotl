// Copied from is_ignored in backend/app/ingestion/safety.py, which stays the source of truth.
// The server drops these paths too, but filtering here keeps secrets such as .env on this
// machine, and keeps virtualenvs out of the 50 MB limit, which the server counts before dropping.
const IGNORED_DIRECTORIES = new Set([
  '.git', '.hg', '.svn', '__pycache__', 'node_modules', '.venv', 'venv', 'env', '.tox', '.mypy_cache',
  '.pytest_cache', '.ruff_cache', 'dist', 'build', '.idea', '.vscode', '.eggs', 'site-packages',
]);
const IGNORED_FILENAMES = new Set(['.env', '.env.local', '.DS_Store', 'Thumbs.db', 'id_rsa', 'id_ed25519']);
const IGNORED_SUFFIXES = new Set([
  '.pyc', '.pyo', '.so', '.dll', '.dylib', '.exe', '.bin', '.zip', '.tar', '.gz', '.whl', '.jpg', '.jpeg',
  '.png', '.gif', '.pdf', '.mp4', '.sqlite', '.db', '.pem', '.key', '.p12', '.pfx',
]);

export function isIgnored(path: string) {
  const dirs = path.split('/');
  const name = dirs.pop() ?? '';
  const dot = name.lastIndexOf('.');
  // Python's PurePosixPath.suffix: a leading or trailing dot is not a suffix.
  const suffix = dot > 0 && dot < name.length - 1 ? name.slice(dot) : '';
  return (
    dirs.some((d) => IGNORED_DIRECTORIES.has(d)) ||
    IGNORED_FILENAMES.has(name) ||
    IGNORED_SUFFIXES.has(suffix.toLowerCase()) ||
    (name.startsWith('.') && suffix !== '')
  );
}

export type FolderFile = { path: string; file: File };

/** A folder picked with <input webkitdirectory>: each file's path inside the folder, minus what the backend drops. */
export function readFolder(list: ArrayLike<File>) {
  const all = Array.from(list, (file) => ({ path: file.webkitRelativePath.replace(/^[^/]*\//, ''), file }));
  const files: FolderFile[] = all.filter((f) => !isIgnored(f.path));
  return {
    name: all[0]?.file.webkitRelativePath.split('/')[0] ?? '',
    files,
    skipped: all.length - files.length,
    bytes: files.reduce((sum, f) => sum + f.file.size, 0),
  };
}
