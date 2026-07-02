import { useCallback, useEffect, useState } from 'react';
import { adminGetModels, adminSetModels, signIn } from '../api';
import { useStore } from '../store';
import type { AdminModelsResp } from '../types';

// ADMIN-ONLY model control panel.
// ───────────────────────────────────────────────────────────────────────────
// This is the runtime half of the "两者结合" admin control: an admin signs in
// (the student app is otherwise anonymous), then toggles which models students may
// pick and/or FORCES one model on everyone ("强制分配").
//
// ⚠️  These controls must NEVER be reachable by a student. The gate is the backend
//     `require_admin` dependency on /admin/models — a non-admin token gets 403 and
//     this panel shows an error. The token is obtained via /auth/signin with an
//     account listed in ADMIN_USERNAMES (.env). See docs/MODELS_AND_PROVIDERS.md.
//
// The token is kept in localStorage so an admin stays signed in across reloads on
// their own machine; "退出管理" clears it. Students simply never sign in here.

const TOKEN_KEY = 'mt_admin_token';

export function AdminModels({ onClose }: { onClose: () => void }) {
  const { refreshModels } = useStore();
  const [token, setToken] = useState<string>(() => localStorage.getItem(TOKEN_KEY) || '');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [data, setData] = useState<AdminModelsResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const clearToken = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken('');
    setData(null);
  };

  const loadCatalogue = useCallback(async (tok: string) => {
    setErr(null);
    setBusy(true);
    try {
      setData(await adminGetModels(tok));
    } catch (e) {
      const msg = (e as Error).message;
      // 401/403 → the token is not an admin (or expired): drop it, show why.
      if (/40[13]/.test(msg)) {
        clearToken();
        setErr('该账号不是管理员，或登录已过期。请用管理员账号登录（ADMIN_USERNAMES）。');
      } else {
        setErr('加载失败：' + msg);
      }
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (token) void loadCatalogue(token);
  }, [token, loadCatalogue]);

  const doSignIn = async () => {
    setErr(null);
    setBusy(true);
    try {
      const { token: tok } = await signIn(username.trim(), password);
      localStorage.setItem(TOKEN_KEY, tok);
      setPassword('');
      setToken(tok);
    } catch (e) {
      setErr('登录失败：' + (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  // Apply one change, refresh the admin catalogue AND the student pool.
  const apply = async (body: Parameters<typeof adminSetModels>[1]) => {
    setBusy(true);
    setErr(null);
    try {
      setData(await adminSetModels(token, body));
      refreshModels();
    } catch (e) {
      setErr('保存失败：' + (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const toggle = (id: string, enabled: boolean) => apply({ enable: { [id]: enabled } });
  const setForced = (id: string) =>
    apply(id ? { forced_model: id } : { clear_forced: true });

  return (
    <div className="admin-overlay" role="dialog" aria-label="模型管理（管理员）">
      <div className="admin-panel">
        <div className="admin-head">
          <strong>模型管理 · 仅管理员</strong>
          <button className="btn-secondary admin-close" onClick={onClose}>关闭</button>
        </div>

        {!token ? (
          <div className="admin-signin">
            <p className="admin-hint">
              这里控制学生可选的模型池与强制分配，属于<strong>管理员专用</strong>权限。
              请用管理员账号登录（账号需在后端 <code>ADMIN_USERNAMES</code> 中）。
            </p>
            <input
              className="admin-input" placeholder="管理员用户名" value={username}
              onChange={(e) => setUsername(e.target.value)} autoComplete="username"
            />
            <input
              className="admin-input" placeholder="密码" type="password" value={password}
              onChange={(e) => setPassword(e.target.value)} autoComplete="current-password"
              onKeyDown={(e) => { if (e.key === 'Enter') void doSignIn(); }}
            />
            <button className="btn-primary" onClick={doSignIn} disabled={busy || !username.trim() || !password}>
              {busy ? '登录中…' : '登录'}
            </button>
          </div>
        ) : (
          <div className="admin-body">
            <div className="admin-forced">
              <label>强制分配（全体学生锁定为）：</label>
              <select
                className="pc-select" value={data?.forced_model || ''}
                onChange={(e) => setForced(e.target.value)} disabled={busy}
              >
                <option value="">不强制（学生可自选）</option>
                {(data?.models || []).filter((m) => m.usable).map((m) => (
                  <option key={m.id} value={m.id}>{m.label} · {m.provider_label}</option>
                ))}
              </select>
            </div>

            <table className="admin-table">
              <thead>
                <tr><th>可用</th><th>模型</th><th>提供商</th><th>已配置</th></tr>
              </thead>
              <tbody>
                {(data?.models || []).map((m) => (
                  <tr key={m.id} className={m.usable ? '' : 'admin-row-unusable'}>
                    <td>
                      <input
                        type="checkbox" checked={m.enabled} disabled={busy || !m.usable}
                        onChange={(e) => toggle(m.id, e.target.checked)}
                        title={m.usable ? '对学生开放/关闭' : '该提供商未在 .env 配置，无法启用'}
                      />
                    </td>
                    <td>{m.label} <span className="admin-mid">{m.id}</span></td>
                    <td>{m.provider_label}</td>
                    <td>{m.usable ? '✅' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="admin-foot">
              <span className="admin-hint">
                只有<strong>已配置（.env 有该提供商的 BASE_URL/API_KEY）</strong>的模型才能启用。
                学生只会看到「可用 ✔ 且已配置」的模型；强制分配后学生的选择被锁定。
              </span>
              <button className="btn-secondary" onClick={clearToken}>退出管理</button>
            </div>
          </div>
        )}

        {err ? <p className="select-err">{err}</p> : null}
      </div>
    </div>
  );
}
