import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { loginSuccess, setAuthError, setAuthLoading, clearAuthError } from '../../features/auth/authSlice';
import { login, signup } from '../../services/api';
import './LoginPage.css';

function LoginPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error } = useSelector((state) => state.auth);
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
  });

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    dispatch(clearAuthError());

    try {
      dispatch(setAuthLoading(true));

      if (mode === 'signup') {
        if (!form.name.trim()) {
          dispatch(setAuthError('Name is required for sign up.'));
          return;
        }

        await signup({
          name: form.name.trim(),
          email: form.email.trim(),
          password: form.password,
        });
      }

      const loginResponse = await login({
        email: form.email.trim(),
        password: form.password,
      });

      dispatch(
        loginSuccess({
          token: loginResponse.data.access_token,
          user: {
            email: form.email.trim(),
            name: form.name.trim() || 'User',
          },
        })
      );

      navigate('/chat');
    } catch (err) {
      dispatch(
        setAuthError(
          err?.response?.data?.detail || err?.message || 'Authentication failed. Please try again.'
        )
      );
    } finally {
      dispatch(setAuthLoading(false));
    }
  };

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-header">
          <div className="logo-badge">C</div>
          <div>
            <p className="eyebrow">Welcome back</p>
            <h1>ChatAI</h1>
          </div>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={mode === 'login' ? 'tab active' : 'tab'}
            onClick={() => setMode('login')}
          >
            Login
          </button>
          <button
            type="button"
            className={mode === 'signup' ? 'tab active' : 'tab'}
            onClick={() => setMode('signup')}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'signup' && (
            <label className="field">
              <span>Name</span>
              <input
                type="text"
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder="Your name"
              />
            </label>
          )}

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="you@example.com"
              required
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="••••••••"
              required
            />
          </label>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create account'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
