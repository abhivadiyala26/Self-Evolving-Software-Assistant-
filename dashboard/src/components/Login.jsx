import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Zap, Shield, User } from 'lucide-react';
import { API_URL } from '../api';
import { ServiceAvailabilityNotice } from './serviceAvailability';
import { isServiceUnavailable, useServiceStatuses } from './serviceStatus';
import './Login.css';

const saveAuthenticatedUser = (data) => {
  const userId = data.user.id;
  if (data.user.role === 'user' && userId) {
    for (const key of ['shopsphereCart', 'shopsphereWishlist', 'shopsphereRecent']) {
      const accountKey = `${key}:${userId}`;
      const guestData = localStorage.getItem(`${key}:guest`) || localStorage.getItem(key);
      if (!localStorage.getItem(accountKey) && guestData) localStorage.setItem(accountKey, guestData);
    }
  }
  localStorage.setItem(data.user.role === 'admin' ? 'adminToken' : 'userToken', data.token);
  localStorage.setItem('currentUser', JSON.stringify(data.user));
};

const clearLegacyUser = (email) => {
  try {
    const legacyUsers = JSON.parse(localStorage.getItem('users') || '[]');
    if (!Array.isArray(legacyUsers)) return;
    const remainingUsers = legacyUsers.filter((user) => user.email?.trim().toLowerCase() !== email.trim().toLowerCase());
    if (remainingUsers.length) localStorage.setItem('users', JSON.stringify(remainingUsers));
    else localStorage.removeItem('users');
  } catch {
    // A malformed legacy value should not prevent the user from signing in.
    return;
  }
};

const migrateLegacyUser = async ({ email, password }) => {
  let legacyUser;
  try {
    const legacyUsers = JSON.parse(localStorage.getItem('users') || '[]');
    legacyUser = Array.isArray(legacyUsers) && legacyUsers.find((user) =>
      user.role === 'user'
      && user.email?.trim().toLowerCase() === email.trim().toLowerCase()
      && user.password === password
    );
  } catch {
    return null;
  }
  if (!legacyUser) return null;

  let response = await fetch(`${API_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: legacyUser.name || 'ShopSphere User', email: legacyUser.email, password })
  });
  let data = await response.json();
  if (response.status === 409) {
    // The account may already have been migrated from another browser/device.
    response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, role: 'user' })
    });
    data = await response.json();
  }
  if (!response.ok) return null;
  clearLegacyUser(email);
  return data;
};

const Login = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [role, setRole] = useState(location.state?.authExpired ? 'admin' : 'user'); // 'user' or 'admin'
  const [formData, setFormData] = useState({ name: '', email: '', password: '', confirmPassword: '' });
  const [error, setError] = useState(location.state?.authExpired ? 'Your admin session expired. Sign in again to continue.' : '');
  const [notice, setNotice] = useState('');
  const [demoInfo, setDemoInfo] = useState(null);
  const { statuses: serviceStatuses, ready: servicesReady } = useServiceStatuses();
  const frontendUnavailable = servicesReady && isServiceUnavailable(serviceStatuses, 'frontend');
  const interactionsDisabled = !servicesReady;

  useEffect(() => {
    let active = true;
    fetch(`${API_URL}/auth/demo-info`)
      .then((response) => response.ok ? response.json() : null)
      .then((data) => { if (active && data) setDemoInfo(data); })
      .catch(() => { if (active) setDemoInfo(null); });
    return () => { active = false; };
  }, []);

  const handleRoleSelect = (selectedRole) => setRole(selectedRole);

  const selectDemoAccount = (selectedRole) => {
    const credentials = demoInfo?.public_demo_accounts?.[selectedRole];
    if (!credentials) return;
    setIsLogin(true);
    setRole(selectedRole);
    setFormData({ name: '', email: credentials.email, password: credentials.password, confirmPassword: '' });
    setError('');
    setNotice('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setNotice('');
    if (!servicesReady) {
      setError('Checking service availability. Please try again shortly.');
      return;
    }
    if (frontendUnavailable && role !== 'admin') {
      setError('Frontend service is temporarily unavailable.');
      return;
    }

    if (isLogin) {
      if (role === 'admin') {
        try {
          const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: formData.email, password: formData.password, role })
          });
          const data = await res.json();
          if (!res.ok) {
            const message = data.detail || 'Sign-in failed.';
            throw new Error(message);
          }
          localStorage.removeItem('userToken');
          saveAuthenticatedUser(data);
          navigate(data.user.role === 'admin' ? '/dashboard' : '/');
        } catch (err) {
          setError(err.message || 'Could not reach the AutoSRE backend.');
        }
        return;
      }
      localStorage.removeItem('adminToken');
      try {
        const res = await fetch(`${API_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: formData.email, password: formData.password, role: 'user' })
        });
        let data = await res.json();
        if (!res.ok && res.status === 401) {
          const migratedAccount = await migrateLegacyUser(formData);
          if (migratedAccount) data = migratedAccount;
        }
        if (data.persistence === 'temporary' && !data.token) {
          clearLegacyUser(formData.email);
          setIsLogin(true);
          setFormData((current) => ({ ...current, name: '', password: '', confirmPassword: '' }));
          setNotice(`${data.message || 'Temporary demo account created.'} Sign in with the email and password you just used.`);
          return;
        }
        if (!res.ok && !data?.token) throw new Error(data.detail || 'Invalid email or password.');
        localStorage.removeItem('adminToken');
        clearLegacyUser(formData.email);
        saveAuthenticatedUser(data);
        navigate(location.state?.from || '/');
      } catch (err) {
        setError(err.message || 'Could not reach the AutoSRE backend.');
      }
    } else {
      if (role === 'admin') {
        setError('Admin accounts are provisioned by the backend environment and cannot sign up here.');
        return;
      }
      if (formData.password.length < 8) {
        setError('Password must be at least 8 characters.');
        return;
      }
      if (formData.password !== formData.confirmPassword) {
        setError('Passwords do not match.');
        return;
      }
      if (!formData.name.trim()) {
        setError('Enter your name.');
        return;
      }
      try {
        const res = await fetch(`${API_URL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: formData.name, email: formData.email, password: formData.password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Could not create the account.');
        if (data.persistence === 'temporary') {
          setIsLogin(true);
          setFormData((current) => ({ ...current, name: '', password: '', confirmPassword: '' }));
          setNotice(`${data.message || 'Temporary demo account created.'} Sign in with the email and password you just used.`);
          return;
        }
        localStorage.removeItem('adminToken');
        clearLegacyUser(formData.email);
        saveAuthenticatedUser(data);
        navigate(location.state?.from || '/');
      } catch (err) {
        setError(err.message || 'Could not reach the AutoSRE backend.');
      }
    }
  };

  return (
    <div className="login-root">
      <div className="login-container animate-fade-in">
        <div className="login-header">
          <Zap size={28} />
          <h2>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
          <p>Sign in to ShopSphere or open the AutoSRE admin console.</p>
        </div>

        {error && <div className="login-error">{error}</div>}
        {notice && <div className="login-notice" role="status">{notice}</div>}
        <ServiceAvailabilityNotice services={frontendUnavailable ? ['frontend'] : []} />

        <div className="login-interactions" inert={interactionsDisabled}>
        <div className="role-selector">
          <button 
            type="button"
            className={`role-btn ${role === 'user' ? 'active user-btn' : ''}`}
            onClick={() => handleRoleSelect('user')}
          >
            <User size={18} /> User
          </button>
          <button 
            type="button"
            className={`role-btn ${role === 'admin' ? 'active admin-btn' : ''}`}
            onClick={() => handleRoleSelect('admin')}
          >
            <Shield size={18} /> Admin
          </button>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {!isLogin && (
            <div className="form-group">
              <label>Full Name</label>
              <input 
                type="text" 
                placeholder="John Doe" 
                required 
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
              />
            </div>
          )}
          
          <div className="form-group">
            <label>Email Address</label>
            <input 
              type="email" 
              placeholder="user@technogear.com" 
              required 
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              placeholder="••••••••" 
              required 
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label>Confirm Password</label>
              <input
                type="password"
                placeholder="Re-enter your password"
                required
                autoComplete="new-password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
              />
            </div>
          )}

          <button type="submit" className="login-submit">
            {isLogin ? 'Sign In' : 'Sign Up'}
          </button>
        </form>

        <div className="login-footer">
          <p>
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button type="button" className="toggle-mode" onClick={() => { setIsLogin(!isLogin); setError(''); }}>
              {isLogin ? 'Sign Up' : 'Sign In'}
            </button>
          </p>
        </div>
        
        {isLogin && demoInfo?.public_demo_accounts && (
          <div className="login-demo-note login-demo-suggestions">
            <p>Try a demo account</p>
            <div className="login-demo-actions">
              <button type="button" className="demo-credential-button" onClick={() => selectDemoAccount('user')}>
                Demo User
              </button>
              <button type="button" className="demo-credential-button" onClick={() => selectDemoAccount('admin')}>
                Demo Admin
              </button>
            </div>
          </div>
        )}
        </div>
      </div>
    </div>
  );
};

export default Login;
