import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Zap, Shield, User } from 'lucide-react';
import { API_URL } from '../api';
import { ServiceAvailabilityNotice } from './serviceAvailability';
import { isServiceUnavailable, useServiceStatuses } from './serviceStatus';
import './Login.css';

const Login = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [role, setRole] = useState(location.state?.authExpired ? 'admin' : 'user'); // 'user' or 'admin'
  const [formData, setFormData] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState(location.state?.authExpired ? 'Your admin session expired. Sign in again to continue.' : '');
  const { statuses: serviceStatuses, ready: servicesReady } = useServiceStatuses();
  const frontendUnavailable = servicesReady && isServiceUnavailable(serviceStatuses, 'frontend');
  const interactionsDisabled = !servicesReady;

  const handleRoleSelect = (selectedRole) => setRole(selectedRole);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
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
            body: JSON.stringify({ email: formData.email, password: formData.password })
          });
          const data = await res.json();
          if (!res.ok) {
            const message = res.status === 401
              ? 'Invalid admin credentials. Use the demo password “password”.'
              : data.detail || 'Admin sign-in failed.';
            throw new Error(message);
          }
          localStorage.setItem('adminToken', data.token);
          localStorage.setItem('currentUser', JSON.stringify({ email: formData.email, name: data.name, role: 'admin' }));
          navigate('/dashboard');
        } catch (err) {
          setError(err.message || 'Could not reach the AutoSRE backend.');
        }
        return;
      }
      localStorage.removeItem('adminToken');
      // Mock Login
      const users = JSON.parse(localStorage.getItem('users') || '[]');
      const user = users.find(u => u.email === formData.email && u.password === formData.password && u.role === role);
      
      if (user) {
        localStorage.setItem('currentUser', JSON.stringify(user));
        // Store users return to ShopSphere after sign-in.
        navigate('/');
      } else {
        setError('Invalid credentials or incorrect role selected.');
      }
    } else {
      if (role === 'admin') {
        setError('Admin accounts are provisioned for the demo. Sign in with the provided admin account.');
        return;
      }
      // Mock Signup
      const users = JSON.parse(localStorage.getItem('users') || '[]');
      if (users.find(u => u.email === formData.email)) {
        setError('Account already exists with this email.');
        return;
      }
      
      const newUser = { ...formData, role };
      users.push(newUser);
      localStorage.setItem('users', JSON.stringify(users));
      
      // Auto login after signup
      localStorage.setItem('currentUser', JSON.stringify(newUser));
      
      // New customer accounts start in ShopSphere.
      navigate('/');
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

        {isLogin && role === 'admin' && (
          <button
            type="button"
            className="demo-credential-button"
            onClick={() => {
              setFormData((current) => ({ ...current, email: 'admin@technogear.com', password: 'password' }));
              setError('');
            }}
          >
            Fill demo admin email and password
          </button>
        )}

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

          <button type="submit" className="login-submit">
            {isLogin ? 'Sign In' : 'Sign Up'}
          </button>
        </form>

        <div className="login-footer">
          <p>
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <span className="toggle-mode" onClick={() => setIsLogin(!isLogin)}>
              {isLogin ? 'Sign Up' : 'Sign In'}
            </span>
          </p>
        </div>
        
        <div className="login-demo-note">
          <p>Demo accounts:<br/>admin@technogear.com / password (Admin) | demo@shopsphere.in / password (User)</p>
          <button 
            type="button" 
            className="login-demo-inject"
            onClick={() => {
               localStorage.setItem('users', JSON.stringify([
                 {email: 'demo@shopsphere.in', password: 'password', role: 'user', name: 'Demo User'}
               ]));
               alert("Demo user account is ready. Admin sign-in is verified by the backend.");
            }}
          >
             Inject Demo Data
          </button>
        </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
