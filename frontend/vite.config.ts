import { defineConfig, loadEnv, type PluginOption } from "vite";
import react from "@vitejs/plugin-react";
import mdx from "@mdx-js/rollup";
import rehypePrism from 'rehype-prism-plus';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

function docsVirtualModule() {
  return {
    name: 'virtual-docs-index',
    resolveId(id: string) {
      if (id === 'virtual:docs') return id;
      return null;
    },
    load(this: any, id: string) {
      if (id !== 'virtual:docs') return null;
      const rootDir = fileURLToPath(new URL('.', import.meta.url));
      const docRoot = path.resolve(rootDir, 'src', 'doc');
      const exists = fs.existsSync(docRoot);
      const locales = exists ? fs.readdirSync(docRoot).filter((d) => fs.statSync(path.join(docRoot, d)).isDirectory()) : [];
      const indexObj: Record<string, Record<string, string>> = {};
      const treeObj: Record<string, any> = {};
      for (const loc of locales) {
        const locDir = path.join(docRoot, loc);
        const files: string[] = [];
        const walk = (dir: string, prefix: string) => {
          const lst = fs.readdirSync(dir);
          for (const name of lst) {
            const full = path.join(dir, name);
            const stat = fs.statSync(full);
            if (stat.isDirectory()) {
              walk(full, path.posix.join(prefix, name));
            } else if (name.toLowerCase().endsWith('.mdx')) {
              const relNoExt = path.posix.join(prefix, name.slice(0, -4)).replace(/^\/+/, '');
              files.push(relNoExt);
            }
          }
        };
        walk(locDir, '');
        files.sort();
        const map: Record<string, string> = {};
        for (const rel of files) {
          // Vite import path should be absolute from /src
          const importPath = `/src/doc/${loc}/${rel}.mdx`;
          map[rel] = importPath;
        }
        indexObj[loc] = map;
        treeObj[loc] = buildTree(files);
      }
      const code = `
export const docsIndex = ${JSON.stringify(indexObj, null, 2)};
export const docsTree = ${JSON.stringify(treeObj, null, 2)};
`;
      return code;
    },
    configureServer(server: any) {
      const rootDir = fileURLToPath(new URL('.', import.meta.url));
      const docRoot = path.resolve(rootDir, 'src', 'doc');
      if (!fs.existsSync(docRoot)) return;
      const reload = () => {
        const mod = server.moduleGraph.getModuleById('virtual:docs');
        if (mod) server.moduleGraph.invalidateModule(mod);
        // trigger full reload so sidebar/index updates immediately
        server.ws.send({ type: 'full-reload' });
      };
      server.watcher.add(docRoot);
      server.watcher.on('add', (p: string) => { if (p.endsWith('.mdx')) reload(); });
      server.watcher.on('unlink', (p: string) => { if (p.endsWith('.mdx')) reload(); });
      server.watcher.on('change', (p: string) => { if (p.endsWith('.mdx')) reload(); });
    },
    handleHotUpdate(ctx: any) {
      const file = ctx.file || '';
      if (file.includes(`${path.sep}src${path.sep}doc${path.sep}`) && file.endsWith('.mdx')) {
        const mod = ctx.server.moduleGraph.getModuleById('virtual:docs');
        if (mod) ctx.server.moduleGraph.invalidateModule(mod);
        ctx.server.ws.send({ type: 'full-reload' });
        return [];
      }
      return null;
    }
  };
}

function buildTree(paths: string[]) {
  const root: any = { name: 'root', children: [] };
  for (const rel of paths) {
    const parts = rel.split('/');
    let cur = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]!;
      const isFile = i === parts.length - 1;
      if (isFile) {
        cur.children.push({ name: titleize(part), path: rel });
      } else {
        let nxt = (cur.children || []).find((c: any) => !c.path && c.name === titleize(part));
        if (!nxt) {
          nxt = { name: titleize(part), children: [] };
          cur.children.push(nxt);
        }
        cur = nxt;
      }
    }
  }
  sortNode(root);
  return root;
}

function sortNode(n: any) {
  if (!n.children) return;
  n.children.sort((a: any, b: any) => {
    const ad = a.path ? 1 : 0;
    const bd = b.path ? 1 : 0;
    if (ad !== bd) return ad - bd;
    return String(a.name).localeCompare(String(b.name));
  });
  n.children.forEach(sortNode);
}

function titleize(s: string) {
  return s.replace(/\.mdx$/i, '').replace(/(^|[-_\s])\w/g, (m) => m.toUpperCase());
}

function normalizeBaseUrl(value: string) {
  if (value.endsWith("/")) return value;
  return `${value}/`;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Allow Docker build-time env (process.env) to drive Vite base as well as .env files
  const baseFromEnv = process.env.FRONTEND_BASE_URL || env.FRONTEND_BASE_URL || "/";
  const baseUrl = normalizeBaseUrl(baseFromEnv);
  console.log("baseUrl is:", baseUrl)
  // Cast Rollup-only plugins to Vite's PluginOption to satisfy TS
  const mdxPlugin = mdx({
    providerImportSource: '@mdx-js/react',
    rehypePlugins: [rehypePrism]
  }) as unknown as PluginOption;
  const docsPlugin = docsVirtualModule() as unknown as PluginOption;
  return {
    base: baseUrl,
    plugins: [
      react(),
      mdxPlugin,
      docsPlugin,
    ] as PluginOption[],
    build: {
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (id.includes('src/doc/')) {
              // Put each doc file in its own chunk
              const match = /src\/doc\/(.*?)\.mdx/.exec(id);
              if (match?.[1]) return `doc-${match[1].replace(/\//g, '-')}`;
            }
          },
        },
      },
      chunkSizeWarningLimit: 1300,
    },
    define: {
      __APP_VERSION__: JSON.stringify(env.npm_package_version ?? "dev"),
    },
    server: {
      port: Number(env.FRONTEND_PORT ?? 5173),
      host: env.FRONTEND_HOST ?? "0.0.0.0",
    },
  };
});
