import { describe, expect, it } from 'vitest';

import { isIgnored, readFolder } from './folder';

const file = (webkitRelativePath: string, size = 10) => ({ webkitRelativePath, size }) as File;

describe('readFolder', () => {
  it('drops the top folder from each path and skips what the backend would', () => {
    const folder = readFolder([
      file('chess/setup.py'),
      file('chess/local_chess/board.py', 30),
      file('chess/.env'),
      file('chess/local_chess/__pycache__/board.cpython-312.pyc'),
      file('chess/.venv/lib/site.py'),
      file('chess/keys/server.PEM'),
    ]);
    expect(folder.name).toBe('chess');
    expect(folder.files.map((f) => f.path)).toEqual(['setup.py', 'local_chess/board.py']);
    expect(folder.skipped).toBe(4);
    expect(folder.bytes).toBe(40);
  });
});

describe('isIgnored', () => {
  it('matches safety.py on hidden files and suffixes', () => {
    expect(isIgnored('.hidden.py')).toBe(true);
    expect(isIgnored('.gitignore')).toBe(false);
    expect(isIgnored('.github/workflows/ci.yml')).toBe(false);
    expect(isIgnored('README.md')).toBe(false);
  });
});
