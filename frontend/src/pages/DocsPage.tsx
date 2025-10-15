import { Suspense, useEffect, useMemo, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { TitleCard } from '../components/TitleCard';
import { MDXProvider } from '@mdx-js/react';
import { docsIndex as _docsIndex, docsTree as _docsTree } from 'virtual:docs';
import { CaretDownIcon, CaretRightIcon } from '@radix-ui/react-icons';
import { Pre } from '../components/Pre';


type Node = { name: string; path?: string; children?: Node[] };

export function DocsPage() {
  const { i18n } = useTranslation();
  const lang = (i18n.language || 'en').split('-')[0] as 'en' | 'zh' | string;
  const location = useLocation();
  const base = '/docs';
  const current = decodeURIComponent(location.pathname.replace(/^.*?\/docs\/?/, '')).replace(/^\/+|\/+$/g, '');

  const docsIndex = _docsIndex as Record<string, Record<string, string>>;
  const docsTree = _docsTree as any;
  const entries = useMemo(() => {
    const map = docsIndex[lang] || docsIndex['en'] || {};
    return Object.keys(map).sort().map((rel) => ({ full: map[rel], rel }));
  }, [docsIndex, lang]);

  const tree: Node = useMemo(() => docsTree[lang] || docsTree['en'] || { name: 'root', children: [] }, [docsTree, lang]);
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set());
  const toggle = (key: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const currentPath = current && entries.some((e) => e.rel === current) ? current : (entries[0]?.rel || '');
  const modKey = useMemo(() => {
    const map = docsIndex[lang] || docsIndex['en'] || {};
    return map[currentPath];
  }, [docsIndex, lang, currentPath]);

  const Comp = useMdxComponent(modKey);

  return (
    <div className="scroll-panel" style={{ height: '100%', overflow: 'auto' }}>
      <TitleCard title={lang === 'zh' ? '文档' : 'Documentation'} />
      <div className="tab-layout">
        <nav className="tab-nav" style={{ gap: '0.25rem' }}>
          <div className="card" style={{ padding: '0.5rem 0.6rem', gap: '0.25rem' }}>
            <Sidebar tree={tree} base={base} current={currentPath} collapsed={collapsed} onToggle={toggle} />
          </div>
        </nav>
        <section>
          <div className="card scroll-panel" style={{ maxWidth: 960 }}>
            <MDXProvider components={{ pre: Pre }}>
              <Suspense fallback={<div style={{ color: 'var(--muted)' }}>Loading…</div>}>
                <article className="doc-body">
                  {Comp ? <Comp /> : <div style={{ color: '#94a3b8' }}>No document.</div>}
                </article>
              </Suspense>
            </MDXProvider>
          </div>
        </section>
      </div>
    </div>
  );
}

function Sidebar({ tree, base, current, collapsed, onToggle, prefix = '', level = 0 }: { tree: Node; base: string; current: string; collapsed: Set<string>; onToggle: (k: string) => void; prefix?: string; level?: number }) {
  const children = tree.children || [];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
      {children.map((node) => {
        const href = node.path ? `${base}/${encodeURI(node.path)}` : undefined;
        const isActive = !!node.path && node.path === current;
        const linkStyle: React.CSSProperties = {
          display: 'block',
          padding: '0.3rem 0.4rem',
          borderRadius: 8,
          color: isActive ? 'var(--text)' : 'var(--muted)',
          background: isActive ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.18), rgba(99, 102, 241, 0.18))' : 'transparent',
          textDecoration: 'none',
          marginLeft: level > 0 ? level * 8 : 0,
        };
        const keyPath = prefix ? `${prefix}/${node.name}` : node.name;
        const isDir = !node.path;
        const isCollapsed = isDir && collapsed.has(keyPath);
        return (
          <div key={(node.path || node.name) + prefix}>
            {node.path ? (
              <Link to={href!} className="doc-nav-item" style={linkStyle}>{node.name}</Link>
            ) : (
              <div
                className="doc-nav-item"
                style={{ ...linkStyle, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}
                onClick={() => onToggle(keyPath)}
                role="button"
                aria-label={isCollapsed ? 'Expand' : 'Collapse'}
              >
                {isCollapsed ? <CaretRightIcon /> : <CaretDownIcon />}
                <span>{node.name}</span>
              </div>
            )}
            {node.children && node.children.length > 0 && !isCollapsed && (
              <Sidebar tree={node} base={base} current={current} collapsed={collapsed} onToggle={onToggle} prefix={prefix + '/' + node.name} level={(level || 0) + 1} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function buildTree(paths: string[]): Node {
  const root: Node = { name: 'root', children: [] };
  for (const rel of paths) {
    const parts = rel.split('/');
    let cur = root;
    for (let i = 0; i < parts.length; i += 1) {
      const part = parts[i]!;
      const isFile = i === parts.length - 1;
      if (isFile) {
        const name = part.replace(/\.mdx$/i, '').replace(/(^|-)\w/g, (s) => s.toUpperCase());
        cur.children = cur.children || [];
        cur.children.push({ name, path: rel });
      } else {
        cur.children = cur.children || [];
        let nxt = cur.children.find((c) => !c.path && c.name === part);
        if (!nxt) {
          nxt = { name: part, children: [] };
          cur.children.push(nxt);
        }
        cur = nxt;
      }
    }
  }
  // sort: directories (no path) first, then files
  const sortNode = (n: Node) => {
    if (!n.children) return;
    n.children.sort((a, b) => {
      const ad = a.path ? 1 : 0;
      const bd = b.path ? 1 : 0;
      if (ad !== bd) return ad - bd;
      return a.name.localeCompare(b.name);
    });
    n.children.forEach(sortNode);
  };
  sortNode(root);
  return root;
}

function useMdxComponent(key?: string) {
  const [Comp, setComp] = useState<any>(null);
  useEffect(() => {
    let active = true;
    if (!key) {
      setComp(null);
      return;
    }
    import(/* @vite-ignore */ key).then((mod) => {
      if (!active) return;
      setComp(() => mod.default);
    });
    return () => { active = false; };
  }, [key]);
  return Comp;
}

// copy button removed per request
