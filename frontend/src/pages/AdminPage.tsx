import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../store/auth';
import { adminGetStats, adminListSimulations, adminListUsers, adminUpdateUserRole } from '../api/admin';
import { AppSelect } from '../components/AppSelect';
import { BarChartIcon, ChevronDownIcon, ChevronUpIcon } from '@radix-ui/react-icons';

export function AdminPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const isAdmin = String((user as any)?.role || '') === 'admin';

  if (!isAdmin) {
    return (
      <div className="panel">
        <div className="panel-title">{t('admin.title')}</div>
        <div className="card" style={{ color: '#f87171' }}>{t('admin.noAccess')}</div>
      </div>
    );
  }

  return (
    <div className="panel" style={{ gap: '0.75rem' }}>
      <div className="panel-title">{t('admin.title')}</div>
      <UsersCard />
      <SimulationsCard />
      <StatsCard />
    </div>
  );
}

function UsersCard() {
  const { t } = useTranslation();
  const [q, setQ] = useState('');
  const [org, setOrg] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [sort, setSort] = useState('created_desc');

  const query = useQuery({
    queryKey: ['admin-users', q, org, from, to, sort],
    queryFn: () => adminListUsers({ q, org, created_from: from, created_to: to, sort }),
  });

  return (
    <div className="card" style={{ display: 'grid', gap: '0.5rem' }}>
      <div className="panel-subtitle">{t('admin.users.title')}</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem' }}>
        <label style={{ display: 'grid', gap: 4 }}>
          {t('admin.users.name')}
          <input className="input small" value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          {t('admin.users.organization')}
          <input className="input small" value={org} onChange={(e) => setOrg(e.target.value)} />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          {t('admin.common.from')}
          <input className="input small" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          {t('admin.common.to')}
          <input className="input small" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </div>
      <div className="card" style={{ padding: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr 1fr 0.8fr 0.8fr', gap: '0.35rem', padding: '0.5rem 0.6rem', color: 'var(--muted)', fontSize: '0.85rem', borderBottom: '1px solid var(--border)' }}>
          <div style={{ cursor: 'pointer' }} onClick={() => setSort(sort === 'name_asc' ? 'name_desc' : 'name_asc')}>
            {t('admin.users.columns.name')} {sort.startsWith('name_') ? (sort.endsWith('asc') ? <ChevronUpIcon /> : <ChevronDownIcon />) : null}
          </div>
          <div>{t('admin.users.columns.email')}</div>
          <div style={{ cursor: 'pointer' }} onClick={() => setSort(sort === 'org_asc' ? 'org_desc' : 'org_asc')}>
            {t('admin.users.columns.organization')} {sort.startsWith('org_') ? (sort.endsWith('asc') ? <ChevronUpIcon /> : <ChevronDownIcon />) : null}
          </div>
          <div style={{ cursor: 'pointer' }} onClick={() => setSort(sort === 'created_asc' ? 'created_desc' : 'created_asc')}>
            {t('admin.users.columns.created')} {sort.startsWith('created_') ? (sort.endsWith('asc') ? <ChevronUpIcon /> : <ChevronDownIcon />) : null}
          </div>
          <div>{t('admin.users.columns.status')}</div>
          <div>{t('admin.users.columns.role') || 'Role'}</div>
        </div>
        <div>
          {(query.data || []).map((u, idx, arr) => (
            <div key={u.id} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr 1fr 0.8fr 0.8fr', gap: '0.35rem', padding: '0.5rem 0.6rem', borderBottom: idx === arr.length - 1 ? 'none' : '1px solid var(--border)' }}>
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{u.full_name || u.username}</div>
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{u.email}</div>
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{u.organization || '-'}</div>
              <div>{new Date(u.created_at).toLocaleString()}</div>
              <div>{u.is_active ? t('admin.common.active') : t('admin.common.disabled')}</div>
              <div>
                <AppSelect
                  value={String((u as any).role || 'user')}
                  size="small"
                  options={[{ value: 'user', label: 'user' }, { value: 'admin', label: 'admin' }]}
                  onChange={async (val) => {
                    await adminUpdateUserRole(u.id, val as 'user' | 'admin');
                    query.refetch();
                  }}
                />
              </div>
            </div>
          ))}
          {query.isLoading && <div style={{ padding: '0.5rem 0.6rem', color: 'var(--muted)' }}>{t('common.loading')}</div>}
          {query.error && <div style={{ padding: '0.5rem 0.6rem', color: '#f87171' }}>{t('admin.common.fetchError')}</div>}
        </div>
      </div>
    </div>
  );
}

function SimulationsCard() {
  const { t } = useTranslation();
  const [userQ, setUserQ] = useState('');
  const [scene, setScene] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [sort, setSort] = useState('created_desc');
  const query = useQuery({
    queryKey: ['admin-sims', userQ, scene, from, to, sort],
    queryFn: () => adminListSimulations({ user: userQ, scene_type: scene, created_from: from, created_to: to, sort }),
  });

  return (
    <div className="card" style={{ display: 'grid', gap: '0.5rem' }}>
      <div className="panel-subtitle">{t('admin.sims.title')}</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
        <label style={{ display: 'grid', gap: 4 }}>
          {t('admin.sims.username')}
          <input className="input small" value={userQ} onChange={(e) => setUserQ(e.target.value)} />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          {t('admin.sims.scene')}
          <input className="input small" value={scene} onChange={(e) => setScene(e.target.value)} />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          {t('admin.common.from')}
          <input className="input small" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          {t('admin.common.to')}
          <input className="input small" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </div>
      <div className="card" style={{ padding: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0.35rem', padding: '0.5rem 0.6rem', color: 'var(--muted)', fontSize: '0.85rem', borderBottom: '1px solid var(--border)' }}>
          <div style={{ cursor: 'pointer' }} onClick={() => setSort(sort === 'username_asc' ? 'username_desc' : 'username_asc')}>
            {t('admin.sims.columns.user')} {sort.startsWith('username_') ? (sort.endsWith('asc') ? <ChevronUpIcon /> : <ChevronDownIcon />) : null}
          </div>
          <div>{t('admin.sims.columns.name')}</div>
          <div style={{ cursor: 'pointer' }} onClick={() => setSort(sort === 'scene_asc' ? 'scene_desc' : 'scene_asc')}>
            {t('admin.sims.columns.scene')} {sort.startsWith('scene_') ? (sort.endsWith('asc') ? <ChevronUpIcon /> : <ChevronDownIcon />) : null}
          </div>
          <div style={{ cursor: 'pointer' }} onClick={() => setSort(sort === 'created_asc' ? 'created_desc' : 'created_asc')}>
            {t('admin.sims.columns.created')} {sort.startsWith('created_') ? (sort.endsWith('asc') ? <ChevronUpIcon /> : <ChevronDownIcon />) : null}
          </div>
        </div>
        <div>
          {(query.data || []).map((s, idx, arr) => (
            <div key={s.id} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0.35rem', padding: '0.5rem 0.6rem', borderBottom: idx === arr.length - 1 ? 'none' : '1px solid var(--border)' }}>
              <div>{s.owner_username || s.owner_id}</div>
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.name}</div>
              <div>{s.scene_type}</div>
              <div>{new Date(s.created_at).toLocaleString()}</div>
            </div>
          ))}
          {query.isLoading && <div style={{ padding: '0.5rem 0.6rem', color: 'var(--muted)' }}>{t('common.loading')}</div>}
          {query.error && <div style={{ padding: '0.5rem 0.6rem', color: '#f87171' }}>{t('admin.common.fetchError')}</div>}
        </div>
      </div>
    </div>
  );
}

function StatsCard() {
  const { t } = useTranslation();
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('day');
  const query = useQuery({ queryKey: ['admin-stats', period], queryFn: () => adminGetStats(period) });
  const stats = query.data;
  const toTotal = (arr?: { date: string; count: number }[]) => (arr || []).reduce((a, b) => a + Number(b.count || 0), 0);

  return (
    <div className="card" style={{ display: 'grid', gap: '0.5rem' }}>
      <div className="panel-subtitle" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <BarChartIcon /> {t('admin.stats.title')}
      </div>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <span style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>{t('admin.stats.period')}</span>
        <AppSelect
          value={period}
          onChange={(v) => setPeriod(v as any)}
          size="small"
          options={[
            { value: 'day', label: t('admin.stats.day') },
            { value: 'week', label: t('admin.stats.week') },
            { value: 'month', label: t('admin.stats.month') },
          ]}
        />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
        <div className="card" style={{ padding: '0.6rem' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{t('admin.stats.simRuns')}</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>{toTotal(stats?.sim_runs)}</div>
        </div>
        <div className="card" style={{ padding: '0.6rem' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{t('admin.stats.userVisits')}</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>{toTotal(stats?.user_visits)}</div>
        </div>
        <div className="card" style={{ padding: '0.6rem' }}>
          <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{t('admin.stats.userSignups')}</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>{toTotal(stats?.user_signups)}</div>
        </div>
      </div>
      {query.isLoading && <div style={{ color: 'var(--muted)' }}>{t('common.loading')}</div>}
      {query.error && <div style={{ color: '#f87171' }}>{t('admin.common.fetchError')}</div>}
    </div>
  );
}
