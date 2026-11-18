/** Сторінка 4.8 «Вхід для адміністратора»: перевірка ключа доступу. */

import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAdmin } from '../api/admin.js';
import { api } from '../api/client.js';
import { Icon } from '../components/Icon.jsx';
import './AdminPage.css';

const KEY_PATTERN = /^[\x21-\x7e]+$/;

export function AdminLoginPage() {
  const { isAdmin, login } = useAdmin();
  const navigate = useNavigate();
  const [key, setKey] = useState('');
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (isAdmin) {
    return <Navigate to="/admin" replace />;
  }

  const submit = async (event) => {
    event.preventDefault();
    const value = key.trim();
    if (!value) {
      setError('Введіть ключ доступу');
      return;
    }
    if (!KEY_PATTERN.test(value)) {
      setError('Неправильний ключ доступу');
      return;
    }
    setBusy(true);
    try {
      await api.adminLog(value);
      login(value);
      navigate('/admin');
    } catch (failure) {
      setError(failure.status === 401 ? 'Неправильний ключ доступу' : 'Сервер недоступний');
      setBusy(false);
    }
  };

  return (
    <div className="page login">
      <form className="panel login-form" onSubmit={submit} noValidate>
        <div className="login-heading">
          <h1 className="page-title">Вхід для адміністратора</h1>
          <p className="label muted">Введіть ключ доступу, щоб керувати оновленням даних.</p>
        </div>
        <div className="login-field">
          <label htmlFor="admin-key">Ключ доступу</label>
          <div className={`login-input${error ? ' login-input-error' : ''}`}>
            <input
              id="admin-key"
              type={visible ? 'text' : 'password'}
              value={key}
              autoComplete="off"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'admin-key-error' : undefined}
              onChange={(event) => {
                setKey(event.target.value);
                setError('');
              }}
            />
            <button type="button" className="login-toggle" onClick={() => setVisible(!visible)}>
              <Icon name={visible ? 'eyeOff' : 'eye'} />
              {visible ? 'Сховати' : 'Показати'}
            </button>
          </div>
          {error && (
            <span id="admin-key-error" className="login-error" role="alert">
              <Icon name="alert" size={16} />
              {error}
            </span>
          )}
        </div>
        <button type="submit" className="btn btn-primary login-submit" disabled={busy}>
          Увійти
        </button>
        <Link to="/" className="login-back">
          Повернутися до каталогу
        </Link>
      </form>
    </div>
  );
}
