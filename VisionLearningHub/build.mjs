import { build } from 'esbuild';
import { mkdir, copyFile } from 'node:fs/promises';
await mkdir('dist', { recursive: true });
await build({ entryPoints: ['frontend/main.tsx'], bundle: true, minify: true, sourcemap: true, outfile: 'dist/app.js', define: { 'process.env.NODE_ENV': '"production"' }, target: ['es2022'] });
await copyFile('frontend/index.html', 'dist/index.html');
console.log('Built local frontend in dist/');
