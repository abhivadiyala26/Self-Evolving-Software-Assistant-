import React, { useState, useEffect, useRef } from 'react';
import {
  ShoppingBag, Search, User, Heart, Star, Truck, ShieldCheck,
  MapPin, X, ArrowRight, CheckCircle, CreditCard, Clock,
  Sparkles, Filter, ChevronRight, LayoutDashboard, ShoppingCart, RefreshCw, AlertCircle,
  Bell, LogIn, Package, BookmarkCheck, Wallet, Headphones, Tag
} from 'lucide-react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { MOCK_PRODUCTS, CATEGORIES } from '../data/products';
import { API_URL } from '../api';
import { ServiceAvailabilityNotice } from './serviceAvailability';
import { isServiceUnavailable, useServiceStatuses } from './serviceStatus';
import './ShopSphere.css';

const readSaved = (key, fallback) => {
  try { return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback)); }
  catch { return fallback; }
};
const readUserSaved = (key, fallback, scope) => {
  const scopedKey = `${key}:${scope}`;
  try {
    const scopedValue = localStorage.getItem(scopedKey);
    if (scopedValue !== null) return JSON.parse(scopedValue);
    if (scope === 'guest') {
      const legacyValue = localStorage.getItem(key);
      if (legacyValue !== null) {
        localStorage.setItem(scopedKey, legacyValue);
        return JSON.parse(legacyValue);
      }
    }
    return fallback;
  } catch {
    return fallback;
  }
};
const formatINR = (value) => new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 0
}).format(value || 0);

const ShopSphere = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [currentUser, setCurrentUser] = useState(() => readSaved('currentUser', null));
  const userScope = currentUser?.id || currentUser?.email || 'guest';
  const orderIdempotencyKey = useRef(null);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [cart, setCart] = useState(() => readUserSaved('shopsphereCart', [], userScope));
  const [wishlist, setWishlist] = useState(() => readUserSaved('shopsphereWishlist', [], userScope));
  const [recentlyViewed, setRecentlyViewed] = useState(() => readUserSaved('shopsphereRecent', [], userScope));
  const [detailQuantity, setDetailQuantity] = useState(1);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [deliveryPincode, setDeliveryPincode] = useState('400050');
  const [selectedBrand, setSelectedBrand] = useState('all');
  const [maxPrice, setMaxPrice] = useState('');
  const [minimumRating, setMinimumRating] = useState('all');
  const [minimumDiscount, setMinimumDiscount] = useState('all');
  const [availability, setAvailability] = useState('all');
  const [sortBy, setSortBy] = useState('popular');
  const [searchFocused, setSearchFocused] = useState(false);

  // Modals & Drawers
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isWishlistOpen, setIsWishlistOpen] = useState(false);
  const [isOrdersOpen, setIsOrdersOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [profileSection, setProfileSection] = useState('Personal Information');
  const [checkoutStep, setCheckoutStep] = useState('cart'); // 'cart', 'address', 'payment', 'confirmation'

  // Checkout Form State
  const [selectedAddress, setSelectedAddress] = useState('home');
  const [selectedDelivery, setSelectedDelivery] = useState('standard');
  const [selectedPayment, setSelectedPayment] = useState('upi');
  const [placedOrders, setPlacedOrders] = useState([]);
  const [activeOrder, setActiveOrder] = useState(null);

  // Toast & Telemetry State
  const [toastMsg, setToastMsg] = useState(null);
  const [systemMetrics, setSystemMetrics] = useState(null);
  const { statuses: serviceStatuses, ready: servicesReady } = useServiceStatuses();
  const frontendUnavailable = servicesReady && isServiceUnavailable(serviceStatuses, 'frontend');
  const frontendInteractionsDisabled = !servicesReady || frontendUnavailable;
  const productUnavailable = !servicesReady || isServiceUnavailable(serviceStatuses, 'productcatalogservice');
  const cartUnavailable = !servicesReady || isServiceUnavailable(serviceStatuses, 'cartservice');
  const orderUnavailable = !servicesReady || isServiceUnavailable(serviceStatuses, 'checkoutservice');
  const paymentUnavailable = !servicesReady || isServiceUnavailable(serviceStatuses, 'paymentservice');
  const unavailableServiceIds = servicesReady
    ? ['frontend', 'productcatalogservice', 'cartservice', 'checkoutservice', 'paymentservice']
      .filter((serviceId) => isServiceUnavailable(serviceStatuses, serviceId))
    : [];
  const checkoutUnavailable = frontendUnavailable || orderUnavailable || paymentUnavailable || Boolean(
    systemMetrics?.paymentservice?.error_rate > 20
    || systemMetrics?.paymentservice?.latency_p95_ms > 1000
    || systemMetrics?.checkoutservice?.error_rate > 20
  );
  useEffect(() => {
    localStorage.setItem(`shopsphereCart:${userScope}`, JSON.stringify(cart));
  }, [cart, userScope]);
  useEffect(() => {
    localStorage.setItem(`shopsphereWishlist:${userScope}`, JSON.stringify(wishlist));
  }, [wishlist, userScope]);

  const routeProduct = location.pathname.startsWith('/product/')
    ? MOCK_PRODUCTS.find((item) => item.id === location.pathname.split('/').pop()) || null
    : null;
  const selectedProduct = routeProduct;
  const selectedImage = selectedProduct?.images?.[selectedImageIndex] || selectedProduct?.images?.[0];
  const cartDialogOpen = isCartOpen || location.pathname === '/cart' || location.pathname === '/checkout';
  const ordersDialogOpen = isOrdersOpen || location.pathname === '/orders';
  const profileDialogOpen = isProfileOpen || (location.pathname === '/profile' && Boolean(currentUser));
  const activeCheckoutStep = location.pathname === '/checkout' && checkoutStep === 'cart' ? 'address' : checkoutStep;

  // Poll live metrics and order history; service state comes from /api/services.
  useEffect(() => {
    const pollBackend = async () => {
      try {
        const [metricsRes, ordersRes] = await Promise.all([
          fetch(`${API_URL}/metrics`),
          !currentUser || frontendInteractionsDisabled || orderUnavailable ? Promise.resolve(null) : fetch(`${API_URL}/orders`, {
            headers: { 'x-auth-token': localStorage.getItem('userToken') || localStorage.getItem('adminToken') || '' }
          })
        ]);
        if (metricsRes.ok) {
          const mData = await metricsRes.json();
          setSystemMetrics(mData);
        }
        if (ordersRes?.ok) {
          const oData = await ordersRes.json();
          setPlacedOrders(oData);
        } else if (ordersRes?.status === 401) {
          localStorage.removeItem('userToken');
          localStorage.removeItem('adminToken');
          localStorage.removeItem('currentUser');
          setCurrentUser(null);
          setPlacedOrders([]);
        }
      } catch {
        // Preserve the last successful view while the next poll retries.
      }
    };

    const interval = setInterval(pollBackend, 2000);
    pollBackend();
    return () => clearInterval(interval);
  }, [currentUser, frontendInteractionsDisabled, orderUnavailable]);

  const availableBrands = [...new Set(MOCK_PRODUCTS.map((product) => product.brand))].sort();
  const suggestions = searchQuery.trim()
    ? MOCK_PRODUCTS.filter((product) => `${product.name} ${product.brand} ${product.category}`.toLowerCase().includes(searchQuery.toLowerCase())).slice(0, 5)
    : [];

  const showToast = (msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const cartBlockMessage = () => {
    if (!servicesReady) return 'Checking service availability. Please try again shortly.';
    if (frontendUnavailable) return 'Frontend service is temporarily unavailable.';
    if (productUnavailable) return 'Product service is temporarily unavailable.';
    if (cartUnavailable) return 'Cart service is temporarily unavailable. Please try again shortly.';
    return '';
  };

  // Cart operations
  const addToCart = (product, quantity = 1) => {
    const blockedMessage = cartBlockMessage();
    if (blockedMessage) {
      showToast(blockedMessage);
      return false;
    }
    setCart(prev => {
      const existing = prev.find(item => item.id === product.id);
      if (existing) {
        return prev.map(item => item.id === product.id ? { ...item, qty: Math.min(item.qty + quantity, product.stock) } : item);
      }
      return [...prev, { ...product, qty: Math.min(quantity, product.stock) }];
    });
    showToast(`Added ${product.name} to Cart`);
    return true;
  };

  const updateCartQty = (productId, delta) => {
    if (!servicesReady || frontendUnavailable || cartUnavailable) {
      showToast(!servicesReady ? 'Checking service availability. Please try again shortly.' : frontendUnavailable ? 'Frontend service is temporarily unavailable.' : 'Cart service is temporarily unavailable. Please try again shortly.');
      return;
    }
    setCart(prev => prev.map(item => {
      if (item.id === productId) {
        const newQty = item.qty + delta;
        return newQty > 0 ? { ...item, qty: Math.min(newQty, item.stock) } : null;
      }
      return item;
    }).filter(Boolean));
  };

  const removeFromCart = (productId) => {
    if (!servicesReady || frontendUnavailable || cartUnavailable) {
      showToast(!servicesReady ? 'Checking service availability. Please try again shortly.' : frontendUnavailable ? 'Frontend service is temporarily unavailable.' : 'Cart service is temporarily unavailable. Please try again shortly.');
      return false;
    }
    setCart(prev => prev.filter(item => item.id !== productId));
    return true;
  };

  const saveForLater = (product) => {
    if (!servicesReady || frontendUnavailable || cartUnavailable) {
      showToast(!servicesReady ? 'Checking service availability. Please try again shortly.' : frontendUnavailable ? 'Frontend service is temporarily unavailable.' : 'Cart service is temporarily unavailable. Please try again shortly.');
      return;
    }
    setWishlist((prev) => prev.some((item) => item.id === product.id) ? prev : [...prev, product]);
    if (!removeFromCart(product.id)) return;
    showToast('Saved to your wishlist for later.');
  };

  // Wishlist operations
  const toggleWishlist = (product) => {
    if (!servicesReady || frontendUnavailable || productUnavailable) {
      showToast(!servicesReady ? 'Checking service availability. Please try again shortly.' : frontendUnavailable ? 'Frontend service is temporarily unavailable.' : 'Product service is temporarily unavailable.');
      return;
    }
    setWishlist(prev => {
      const exists = prev.some(item => item.id === product.id);
      if (exists) {
        showToast(`Removed from Wishlist`);
        return prev.filter(item => item.id !== product.id);
      } else {
        showToast(`Saved to Wishlist`);
        return [...prev, product];
      }
    });
  };

  // Pricing calculations
  const cartSubtotal = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
  const discountTotal = cart.reduce((sum, item) => sum + ((item.originalPrice - item.price) * item.qty), 0);
  const deliveryFee = selectedDelivery === 'express' ? 99 : cartSubtotal > 999 || cart.length === 0 ? 0 : 49;
  const finalTotal = cartSubtotal + deliveryFee;

  // Checkout submission
  const handlePlaceOrder = async () => {
    if (!currentUser) {
      showToast('Sign in to place an order. Your guest cart will be kept on this device.');
      navigate('/login', { state: { from: `${location.pathname}${location.search}` } });
      return;
    }
    if (!servicesReady) return showToast('Checking service availability. Please try again shortly.');
    if (frontendUnavailable) return showToast('Frontend service is temporarily unavailable.');
    if (cartUnavailable) return showToast('Cart service is temporarily unavailable. Please try again shortly.');
    if (orderUnavailable) return showToast('Order service is temporarily unavailable.');
    if (paymentUnavailable) return showToast('Payment service is temporarily unavailable. Please try again later.');
    if (checkoutUnavailable) return showToast('Checkout is temporarily unavailable while AutoSRE investigates a service issue.');
    if (cart.length === 0) return;

    try {
      const token = localStorage.getItem('userToken') || localStorage.getItem('adminToken');
      if (!token) {
        showToast('Your sign-in session expired. Please sign in again.');
        navigate('/login', { state: { authExpired: true } });
        return;
      }
      if (!orderIdempotencyKey.current) {
        const storageKey = `shopsphereOrderAttempt:${userScope}`;
        const generated = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
        orderIdempotencyKey.current = sessionStorage.getItem(storageKey) || generated;
        sessionStorage.setItem(storageKey, orderIdempotencyKey.current);
      }
      const res = await fetch(`${API_URL}/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-auth-token': token,
          'Idempotency-Key': orderIdempotencyKey.current
        },
        body: JSON.stringify({
          items: cart.map(i => ({ id: i.id, name: i.name, price: i.price, quantity: i.qty })),
          totalAmount: finalTotal,
          paymentMethod: selectedPayment.toUpperCase(),
          address: selectedAddress === 'home' ? 'Home (Bandra West, Mumbai)' : 'Office (BKC, Mumbai)',
          deliveryOption: selectedDelivery
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        if (res.status === 401) {
          localStorage.removeItem('userToken');
          localStorage.removeItem('adminToken');
          localStorage.removeItem('currentUser');
          setCurrentUser(null);
          navigate('/login', { state: { authExpired: true } });
          return;
        }
        if (res.status === 409) {
          sessionStorage.removeItem(`shopsphereOrderAttempt:${userScope}`);
          orderIdempotencyKey.current = null;
        }
        showToast(`Checkout Error: ${errData.detail || 'Service degraded'}`);
        return;
      }

      const data = await res.json();
      sessionStorage.removeItem(`shopsphereOrderAttempt:${userScope}`);
      orderIdempotencyKey.current = null;
      setActiveOrder(data.order);
      setCart([]);
      setCheckoutStep('confirmation');
      showToast("Order placed successfully! Order ID: " + data.order.order_id);
    } catch {
      showToast("Checkout failed: Payment/Order microservice unavailable");
    }
  };

  // Product filtering
  const filteredProducts = MOCK_PRODUCTS.filter(p => {
    const matchesCat = selectedCategory === 'all' || p.category === selectedCategory;
    const searchable = `${p.name} ${p.brand} ${p.category} ${p.description || ''}`.toLowerCase();
    const matchesSearch = searchable.includes(searchQuery.toLowerCase());
    const matchesBrand = selectedBrand === 'all' || p.brand === selectedBrand;
    const matchesPrice = !maxPrice || p.price <= Number(maxPrice);
    const matchesRating = minimumRating === 'all' || p.rating >= Number(minimumRating);
    const matchesDiscount = minimumDiscount === 'all' || p.discount >= Number(minimumDiscount);
    const matchesAvailability = availability === 'all' || (availability === 'in-stock' ? p.stock > 0 : p.stock <= 10);
    return matchesCat && matchesSearch && matchesBrand && matchesPrice && matchesRating && matchesDiscount && matchesAvailability;
  }).sort((a, b) => {
    if (sortBy === 'price-low') return a.price - b.price;
    if (sortBy === 'price-high') return b.price - a.price;
    if (sortBy === 'rating') return b.rating - a.rating;
    if (sortBy === 'discount') return b.discount - a.discount;
    if (sortBy === 'newest') return String(b.id).localeCompare(String(a.id));
    return b.reviewCount - a.reviewCount;
  });

  const navigateToProduct = (product) => {
    if (frontendUnavailable || productUnavailable) {
      showToast(frontendUnavailable ? 'Frontend service is temporarily unavailable.' : 'Product service is temporarily unavailable.');
      return;
    }
    const next = [product, ...recentlyViewed.filter((item) => item.id !== product.id)].slice(0, 8);
    setRecentlyViewed(next);
    localStorage.setItem(`shopsphereRecent:${userScope}`, JSON.stringify(next));
    setDetailQuantity(1);
    setSelectedImageIndex(0);
    navigate(`/product/${product.id}`);
  };
  const closeProductDetails = () => navigate('/products');
  const closeCart = () => {
    setIsCartOpen(false);
    setCheckoutStep('cart');
    if (location.pathname === '/cart' || location.pathname === '/checkout') navigate('/');
  };
  const closeOrders = () => {
    setIsOrdersOpen(false);
    if (location.pathname === '/orders') navigate('/');
  };
  if (location.pathname === '/profile' && !currentUser) return <Navigate to="/login" replace />;
  const signOut = async () => {
    const authToken = localStorage.getItem('userToken') || localStorage.getItem('adminToken');
    if (authToken) await fetch(`${API_URL}/auth/logout`, { method: 'POST', headers: { 'x-auth-token': authToken } }).catch(() => {});
    localStorage.removeItem('userToken');
    localStorage.removeItem('adminToken');
    localStorage.removeItem('currentUser');
    setCart([]);
    setWishlist([]);
    setRecentlyViewed([]);
    setPlacedOrders([]);
    setCurrentUser(null);
    showToast('You have been signed out.');
    navigate('/');
  };

  return (
    <div className="shopsphere-root">
      <ServiceAvailabilityNotice services={unavailableServiceIds} />
      <div className="shopsphere-interactions" inert={frontendInteractionsDisabled}>
      {/* Top Header */}
      <header className="shopsphere-header">
        <div className="header-top-nav">
          <div className="shopsphere-logo" onClick={() => { setSelectedCategory('all'); setSearchQuery(''); navigate('/'); }}>
            <div className="logo-icon">
              <ShoppingBag color="#34745b" size={22} />
            </div>
            <div>
              <span className="logo-text">ShopSphere</span>
              <span className="logo-tag">INDIA</span>
            </div>
          </div>

          {/* Search Bar */}
          <div className="shopsphere-search-bar">
            <Search size={18} color="#8B949E" />
            <input
              type="text"
              placeholder="Search for Mobiles, Laptops, Electronics, Fashion & more..."
              value={searchQuery}
              disabled={productUnavailable}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setTimeout(() => setSearchFocused(false), 120)}
            />
            {searchQuery && <X size={16} color="#8B949E" style={{ cursor: productUnavailable ? 'not-allowed' : 'pointer' }} onClick={() => { if (!productUnavailable) setSearchQuery(''); }} />}
            {searchFocused && suggestions.length > 0 && (
              <div className="search-suggestions" inert={productUnavailable}>
                {suggestions.map((product) => (
                  <button key={product.id} onMouseDown={(event) => event.preventDefault()} onClick={() => { setSearchFocused(false); navigateToProduct(product); }}>
                    <Search size={14} /><span>{product.name}</span><small>{product.brand}</small>
                  </button>
                ))}
                {searchQuery.toLowerCase().includes('iphone') && <button onMouseDown={(event) => event.preventDefault()} onClick={() => { setSearchQuery('iphone'); setSelectedCategory('accessories'); }}><Search size={14} /><span>iPhone accessories</span></button>}
              </div>
            )}
          </div>

          {/* Header Right Actions */}
          <div className="header-user-actions">
            {currentUser?.role === 'admin' && localStorage.getItem('adminToken') && <button className="header-action-btn" onClick={() => navigate('/dashboard')} title="Open AutoSRE admin console">
              <LayoutDashboard size={18} /><span>Admin Console</span>
            </button>}

            <button className="header-action-btn" onClick={() => setIsWishlistOpen(true)}>
              <Heart size={18} color={wishlist.length > 0 ? "#b34d45" : "#58635a"} />
              <span>Wishlist</span>
              {wishlist.length > 0 && <span className="wishlist-count-badge">{wishlist.length}</span>}
            </button>

            <button className="header-action-btn" onClick={() => { setIsCartOpen(true); setCheckoutStep('cart'); navigate('/cart'); }}>
              <ShoppingCart size={18} />
              <span>Cart</span>
              {cart.length > 0 && <span className="cart-count-badge">{cart.reduce((s, i) => s + i.qty, 0)}</span>}
            </button>

            <button className="header-action-btn" onClick={() => { setIsOrdersOpen(true); navigate('/orders'); }}>
              <Package size={18} />
              <span>My Orders</span>
            </button>

            <button className="header-action-btn" onClick={() => setIsNotificationsOpen(true)} title="Notifications">
              <Bell size={18} /><span>Alerts</span>
            </button>
            <button className="header-action-btn" onClick={() => currentUser ? (setIsProfileOpen(true), navigate('/profile')) : navigate('/login')}>
              {currentUser ? <User size={18} /> : <LogIn size={18} />}
              <span>{currentUser?.name || 'Login'}</span>
            </button>
          </div>
        </div>

        {/* Category Navigation Bar */}
        <nav className="category-nav-bar">
          {CATEGORIES.map(cat => (
            <button
              key={cat.id}
              className={`category-nav-item ${selectedCategory === cat.id ? 'active' : ''}`}
              disabled={productUnavailable}
              onClick={() => { setSelectedCategory(cat.id); navigate('/products'); }}
            >
              {cat.name}
            </button>
          ))}
        </nav>
      </header>

      {/* Main Body */}
      <main className="shopsphere-content">
        {/* Hero Promotional Banner */}
        {selectedCategory === 'all' && !searchQuery && (
          <section className="hero-banner animate-fade-in">
            <div className="banner-text">
              <h2>Mega Electronics & Festival Sale</h2>
              <p>Up to 50% OFF on Top Smartphone Brands, Laptops & Noise Cancelling Headphones</p>
              <button className="btn-banner-shop" onClick={() => { setSelectedCategory('electronics'); navigate('/products'); }}>
                Explore Deals <ArrowRight size={16} />
              </button>
            </div>
          </section>
        )}

        {selectedCategory === 'all' && !searchQuery && (
          <section className="marketplace-highlights">
            <div className="highlight-tile"><Tag size={18} /><span><strong>Today’s Deals</strong><small>Up to 57% off across the store</small></span></div>
            <div className="highlight-tile"><ShieldCheck size={18} /><span><strong>Bank Offers</strong><small>10% instant discount on HDFC cards</small></span></div>
            <div className="highlight-tile"><Truck size={18} /><span><strong>Fast delivery</strong><small>Free delivery on eligible orders</small></span></div>
            <div className="highlight-tile"><Sparkles size={18} /><span><strong>Popular brands</strong><small>Samsung · Apple · Sony · boAt</small></span></div>
          </section>
        )}

        {selectedCategory === 'all' && !searchQuery && (
          <section className="home-shelves" inert={productUnavailable}>
            <div><h3>Best Sellers · Trending Products</h3><div className="mini-product-strip">{[...MOCK_PRODUCTS].sort((a, b) => b.reviewCount - a.reviewCount).slice(0, 5).map((product) => <button key={product.id} onClick={() => navigateToProduct(product)}><img src={product.images[0]} alt="" /><span>{product.name}</span><strong>{formatINR(product.price)}</strong></button>)}</div></div>
            <div><h3>Recommended For You</h3><div className="mini-product-strip">{MOCK_PRODUCTS.slice(3, 8).map((product) => <button key={product.id} onClick={() => navigateToProduct(product)}><img src={product.images[0]} alt="" /><span>{product.name}</span><strong>{formatINR(product.price)}</strong></button>)}</div></div>
            {recentlyViewed.length > 0 && <div><h3>Recently Viewed</h3><div className="mini-product-strip">{recentlyViewed.slice(0, 5).map((product) => <button key={product.id} onClick={() => navigateToProduct(product)}><img src={product.images[0]} alt="" /><span>{product.name}</span><strong>{formatINR(product.price)}</strong></button>)}</div></div>}
          </section>
        )}

        {/* Product Listing Section */}
        <section className="product-listing-section" inert={productUnavailable}>
          <div className="section-header">
            <h3>
              {selectedCategory === 'all' ? "Today's Featured Products" : `Browsing: ${selectedCategory.toUpperCase()}`}
            </h3>
            <span style={{ fontSize: '0.85rem', color: '#8B949E' }}>
              Showing {filteredProducts.length} Items
            </span>
          </div>

          <div className="product-filters">
            <label><Filter size={14} /> Brand<select value={selectedBrand} onChange={(e) => setSelectedBrand(e.target.value)}><option value="all">All brands</option>{availableBrands.map((brand) => <option key={brand} value={brand}>{brand}</option>)}</select></label>
            <label>Up to <span className="filter-rupee">₹</span><input aria-label="Maximum price in rupees" inputMode="numeric" type="number" min="0" placeholder="Any price" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} /></label>
            <label>Rating<select value={minimumRating} onChange={(e) => setMinimumRating(e.target.value)}><option value="all">All ratings</option><option value="4">4★ and up</option><option value="4.5">4.5★ and up</option></select></label>
            <label>Discount<select value={minimumDiscount} onChange={(e) => setMinimumDiscount(e.target.value)}><option value="all">Any discount</option><option value="10">10% and up</option><option value="25">25% and up</option><option value="50">50% and up</option></select></label>
            <label>Availability<select value={availability} onChange={(e) => setAvailability(e.target.value)}><option value="all">All items</option><option value="in-stock">In stock</option><option value="low-stock">Low stock</option></select></label>
            <label>Sort<select value={sortBy} onChange={(e) => setSortBy(e.target.value)}><option value="popular">Popularity</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option><option value="rating">Rating</option><option value="newest">Newest</option><option value="discount">Discount</option></select></label>
          </div>

          <div className="product-grid">
            {filteredProducts.map(product => (
              <div key={product.id} className="product-card" onClick={() => navigateToProduct(product)}>
                <div className="product-img-box">
                  <img src={product.images[0]} alt={product.name} />
                  {product.discount > 0 && <span className="discount-badge">{product.discount}% OFF</span>}
                  <button
                    className="wishlist-btn-overlay"
                    onClick={(e) => { e.stopPropagation(); toggleWishlist(product); }}
                  >
                    <Heart size={16} color={wishlist.some(w => w.id === product.id) ? "#b34d45" : "#606b62"} fill={wishlist.some(w => w.id === product.id) ? "#b34d45" : "none"} />
                  </button>
                </div>

                <div className="product-info">
                  <span className="product-brand">{product.brand}</span>
                  <h4 className="product-title">{product.name}</h4>

                  <div className="product-rating">
                    <Star size={14} fill="#FFCC00" color="#FFCC00" />
                    <span>{product.rating}</span>
                    <span style={{ color: '#8B949E' }}>({product.reviewCount})</span>
                  </div>

                  <div className="product-price-row">
                    <span className="price-current">{formatINR(product.price)}</span>
                    {product.originalPrice > product.price && (
                      <span className="price-original">{formatINR(product.originalPrice)}</span>
                    )}
                  </div>

                  <span className="delivery-tag">
                    <Truck size={12} style={{ display: 'inline', marginRight: '4px' }} />
                    {product.deliveryEstimate}
                  </span>

                  <span className={product.stock <= 10 ? 'stock-status low-stock' : 'stock-status'}>{product.stock <= 10 ? `Only ${product.stock} left` : 'In stock'}</span>

                  <button
                    className="btn-add-cart"
                    disabled={frontendUnavailable || productUnavailable || cartUnavailable}
                    onClick={(e) => { e.stopPropagation(); addToCart(product); }}
                  >
                    <ShoppingCart size={14} /> Add to Cart
                  </button>
                  <button className="btn-buy-now" disabled={frontendUnavailable || productUnavailable || cartUnavailable} onClick={(e) => { e.stopPropagation(); if (addToCart(product)) navigate('/checkout'); }}>Buy Now</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Product Details Modal */}
      {selectedProduct && (
        <div className="modal-backdrop" onClick={closeProductDetails}>
          <div className="modal-content animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedProduct.name}</h3>
              <button className="modal-close-btn" onClick={closeProductDetails}><X size={18} /></button>
            </div>
            <div className="modal-body product-detail-layout">
              <div>
                <img src={selectedImage} alt={selectedProduct.name} style={{ width: '100%', borderRadius: '12px', height: '300px', objectFit: 'cover' }} />
                {selectedProduct.images.length > 1 && <div className="detail-image-strip">{selectedProduct.images.map((src, index) => <button key={src} aria-label={`Show product image ${index + 1}`} className={selectedImageIndex === index ? 'selected' : ''} disabled={productUnavailable} onClick={() => setSelectedImageIndex(index)}><img src={src} alt="" /></button>)}</div>}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                <span className="product-brand">{selectedProduct.brand}</span>
                <span className="product-rating"><Star size={14} fill="#FFCC00" color="#FFCC00" /> {selectedProduct.rating} ({selectedProduct.reviewCount.toLocaleString('en-IN')} reviews)</span>
                <p className="product-description">{selectedProduct.description}</p>

                <div className="product-price-row">
                  <span className="price-current" style={{ fontSize: '1.5rem' }}>{formatINR(selectedProduct.price)}</span>
                  <span className="price-original">{formatINR(selectedProduct.originalPrice)}</span>
                  <span className="discount-badge">{selectedProduct.discount}% OFF</span>
                </div>

                <div className="offer-note"><strong>Bank offer:</strong> 10% instant discount on HDFC cards. No-cost EMI available on select cards.</div>
                <div className="delivery-check"><MapPin size={16} /><span>Delivery PIN</span><input aria-label="Delivery PIN code" value={deliveryPincode} maxLength={6} disabled={productUnavailable} onChange={(event) => setDeliveryPincode(event.target.value.replace(/\D/g, ''))} /><strong>{selectedProduct.deliveryEstimate}</strong></div>
                <span className={selectedProduct.stock <= 10 ? 'stock-status low-stock' : 'stock-status'}>{selectedProduct.stock <= 10 ? `Only ${selectedProduct.stock} left` : `${selectedProduct.stock} available`}</span>
                <div className="detail-quantity"><span>Quantity</span><button disabled={productUnavailable || cartUnavailable} onClick={() => setDetailQuantity((quantity) => Math.max(1, quantity - 1))}>−</button><strong>{detailQuantity}</strong><button disabled={productUnavailable || cartUnavailable} onClick={() => setDetailQuantity((quantity) => Math.min(selectedProduct.stock, quantity + 1))}>+</button></div>

                <div className="product-specifications">
                  <strong>Specifications:</strong>
                  {Object.entries(selectedProduct.specs || {}).map(([k, v]) => (
                    <div key={k}>
                      <span>{k}:</span>
                      <strong>{v}</strong>
                    </div>
                  ))}
                </div>

                <button
                  className="btn-add-cart"
                  style={{ padding: '0.8rem', fontSize: '1rem', marginTop: 'auto' }}
                  disabled={frontendUnavailable || productUnavailable || cartUnavailable}
                  onClick={() => { if (addToCart(selectedProduct, detailQuantity)) closeProductDetails(); }}
                >
                  <ShoppingCart size={18} /> Add to Cart Now
                </button>
                <button className="btn-buy-now" disabled={frontendUnavailable || productUnavailable || cartUnavailable} onClick={() => { if (addToCart(selectedProduct, detailQuantity)) { closeProductDetails(); navigate('/checkout'); } }}>Buy Now</button>
                <button className="save-later-btn" disabled={frontendUnavailable || productUnavailable} onClick={() => toggleWishlist(selectedProduct)}><Heart size={15} /> Save to Wishlist</button>
              </div>
            </div>
            <div className="product-detail-extras">
              <section>
                <h4>Customer reviews</h4>
                <article><strong>★★★★★ · Verified purchase</strong><p>Great value and quick delivery. The product matched the listing.</p><small>ShopSphere customer · Mumbai</small></article>
                <article><strong>★★★★☆ · Verified purchase</strong><p>Good quality and easy to use. Packaging arrived in good condition.</p><small>ShopSphere customer · Pune</small></article>
              </section>
              <section>
                <h4>Similar products</h4>
                <div className="similar-product-list" inert={productUnavailable}>{MOCK_PRODUCTS.filter((product) => product.category === selectedProduct.category && product.id !== selectedProduct.id).slice(0, 3).map((product) => <button key={product.id} disabled={productUnavailable} onClick={() => navigateToProduct(product)}><img src={product.images[0]} alt="" /><span>{product.name}</span><strong>{formatINR(product.price)}</strong></button>)}</div>
              </section>
            </div>
          </div>
        </div>
      )}

      {/* Cart & Checkout Modal */}
      {cartDialogOpen && (
        <div className="modal-backdrop" onClick={closeCart}>
          <div className="modal-content animate-fade-in" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h3>Shopping Cart & Checkout</h3>
              <button className="modal-close-btn" onClick={closeCart}><X size={18} /></button>
            </div>

            <div className="modal-body">
              {activeCheckoutStep === 'cart' && (
                <>
                  {cart.length === 0 ? (
                    <div className="cart-empty">
                      Your Shopping Cart is empty.
                    </div>
                  ) : (
                    <div className="cart-lines">
                      {cart.map(item => (
                        <div key={item.id} className="cart-line">
                          <img className="cart-line-image" src={item.images[0]} alt={item.name} />
                          <div className="cart-line-product">
                            <div>{item.name}</div>
                            <div className="cart-item-price">{formatINR(item.price)}</div>
                          </div>
                          <div className="cart-qty-control">
                            <button className="modal-close-btn" disabled={frontendUnavailable || cartUnavailable} onClick={() => updateCartQty(item.id, -1)}>-</button>
                            <span>{item.qty}</span>
                            <button className="modal-close-btn" disabled={frontendUnavailable || cartUnavailable} onClick={() => updateCartQty(item.id, 1)}>+</button>
                          </div>
                          <button className="save-later-btn" disabled={frontendUnavailable || cartUnavailable} onClick={() => saveForLater(item)}><BookmarkCheck size={14} /> Save for later</button>
                          <button className="modal-close-btn" disabled={frontendUnavailable || cartUnavailable} onClick={() => removeFromCart(item.id)}><X size={16} /></button>
                        </div>
                      ))}

                      <div className="cart-summary">
                        <div><span>Subtotal:</span><span>{formatINR(cartSubtotal)}</span></div>
                        <div className="cart-savings"><span>You save:</span><span>−{formatINR(discountTotal)}</span></div>
                        <div><span>Delivery Fee:</span><span>{deliveryFee === 0 ? 'FREE' : formatINR(deliveryFee)}</span></div>
                        <div className="cart-total">
                          <span>Total Amount:</span>
                          <span>{formatINR(finalTotal)}</span>
                        </div>
                      </div>

                      <button className="btn-banner-shop checkout-continue" disabled={frontendUnavailable || cartUnavailable} onClick={() => { setCheckoutStep('address'); navigate('/checkout'); }}>
                        Proceed to Delivery Address <ArrowRight size={16} />
                      </button>
                    </div>
                  )}
                </>
              )}

              {activeCheckoutStep === 'address' && (
                <div className="checkout-step-content">
                  <h4>Select Delivery Address</h4>
                  <div
                    onClick={() => setSelectedAddress('home')}
                    className={`checkout-choice-card ${selectedAddress === 'home' ? 'selected' : ''}`}
                  >
                    <strong>Home Address</strong>
                    <p>Flat 402, Sea Crest Apartments, Bandra West, Mumbai 400050</p>
                  </div>
                  <div
                    onClick={() => setSelectedAddress('office')}
                    className={`checkout-choice-card ${selectedAddress === 'office' ? 'selected' : ''}`}
                  >
                    <strong>Office Address</strong>
                    <p>Suite 800, Tech Park, BKC, Mumbai 400051</p>
                  </div>
                  <button className="btn-banner-shop" onClick={() => setCheckoutStep('delivery')}>
                    Continue to Delivery Options <ArrowRight size={16} />
                  </button>
                </div>
              )}

              {activeCheckoutStep === 'delivery' && (
                <div className="delivery-options">
                  <h4>Choose a delivery option</h4>
                  <button className={selectedDelivery === 'standard' ? 'delivery-choice selected' : 'delivery-choice'} onClick={() => setSelectedDelivery('standard')}><Truck size={17} /><span><strong>Standard delivery</strong><small>Free · Delivery by Tomorrow</small></span></button>
                  <button className={selectedDelivery === 'express' ? 'delivery-choice selected' : 'delivery-choice'} onClick={() => setSelectedDelivery('express')}><Clock size={17} /><span><strong>Express delivery</strong><small>₹99 · Delivery today by 9 PM</small></span></button>
                  <button className="btn-banner-shop" onClick={() => setCheckoutStep('payment')}>Continue to Payment <ArrowRight size={16} /></button>
                </div>
              )}

              {activeCheckoutStep === 'payment' && (
                <div className="checkout-step-content">
                  <h4>Select Payment Method</h4>
                  <p className="orders-unavailable-note">This demonstration records orders only. UPI, card, and net banking payments are not charged or processed.</p>
                  {checkoutUnavailable && <div className="checkout-outage-note"><AlertCircle size={16} /> {orderUnavailable ? 'Order service is temporarily unavailable.' : paymentUnavailable ? 'Payment service is temporarily unavailable. Please try again later.' : 'Payment is temporarily unavailable while AutoSRE investigates a service issue.'}</div>}
                  {['upi', 'card', 'netbanking', 'cod'].map(m => (
                    <div
                      key={m}
                      inert={checkoutUnavailable}
                      onClick={() => setSelectedPayment(m)}
                      className={`checkout-choice-card payment-choice ${selectedPayment === m ? 'selected' : ''}`}
                    >
                      <strong>{m === 'upi' ? 'UPI (Google Pay / PhonePe)' : m === 'card' ? 'Credit / Debit Card' : m === 'netbanking' ? 'Net Banking' : 'Cash on Delivery (COD)'}</strong>
                    </div>
                  ))}
                  <button className="btn-banner-shop" onClick={handlePlaceOrder} disabled={checkoutUnavailable || cartUnavailable}>
                    Place Order ({formatINR(finalTotal)})
                  </button>
                  {!currentUser && <p className="orders-unavailable-note">Sign in to place an order and view your order history.</p>}
                </div>
              )}

              {activeCheckoutStep === 'confirmation' && activeOrder && (
                <div className="order-confirmation">
                  <CheckCircle size={42} />
                  <h3>Order Placed Successfully!</h3>
                  <div className="order-confirmation-id">
                    Order ID: {activeOrder.order_id}
                  </div>
                  <p>
                    {activeOrder.deliveryEstimate}
                  </p>
                  <button className="btn-add-cart" onClick={closeCart}>
                    Back to ShopSphere
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Orders History Drawer */}
      {ordersDialogOpen && (
        <div className="modal-backdrop" onClick={closeOrders}>
          <div className="modal-content animate-fade-in" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '650px' }}>
            <div className="modal-header">
              <h3>My Orders ({placedOrders.length})</h3>
              <button className="modal-close-btn" onClick={closeOrders}><X size={18} /></button>
            </div>
            <div className="modal-body">
              {frontendUnavailable || orderUnavailable ? (
                <div className="orders-unavailable-note" role="status">
                  {frontendUnavailable ? 'Frontend service is temporarily unavailable.' : 'Order service is temporarily unavailable.'}
                </div>
              ) : !currentUser ? (
                <div className="orders-unavailable-note" role="status">
                  <p>Sign in to view your personal order history.</p>
                  <button className="btn-banner-shop" onClick={() => navigate('/login', { state: { from: '/orders' } })}>Sign In</button>
                </div>
              ) : placedOrders.length === 0 ? (
                <div style={{ color: '#8B949E', textAlign: 'center', padding: '2rem' }}>No past orders found.</div>
              ) : (
                placedOrders.map(ord => (
                  <div key={ord.order_id} className="order-history-card">
                    <div className="order-history-heading">
                      <span>Order #{ord.order_id}</span>
                      <span>{formatINR(ord.totalAmount)}</span>
                    </div>
                    <div className="order-history-meta">Placed on: {ord.timestamp}</div>
                    <div className="order-history-items">{(ord.items || []).map((item) => `${item.name} × ${item.quantity}`).join(' · ')}</div>
                    <div className="order-history-meta">Payment: {ord.paymentStatus === 'cash_on_delivery' ? 'Cash on delivery' : 'Not processed (demo)'} · {ord.paymentMethod}</div>
                    <div className="order-history-status">{ord.status} · {ord.deliveryEstimate}</div>
                    <div className="order-tracking-line">{['PLACED', 'CONFIRMED', 'PACKED', 'SHIPPED', 'OUT FOR DELIVERY', 'DELIVERED'].map((stage, index) => <React.Fragment key={stage}><span className={['PLACED', 'CONFIRMED', 'PACKED', 'SHIPPED', 'OUT FOR DELIVERY', 'DELIVERED'].indexOf(ord.status) >= index ? 'tracking-stage active' : 'tracking-stage'}>{stage}</span>{index < 5 && <b>›</b>}</React.Fragment>)}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {isWishlistOpen && (
        <div className="modal-backdrop" onClick={() => setIsWishlistOpen(false)}>
          <div className="modal-content animate-fade-in" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header"><h3>My Wishlist ({wishlist.length})</h3><button className="modal-close-btn" onClick={() => setIsWishlistOpen(false)}><X size={18} /></button></div>
            <div className="modal-body">
              {wishlist.length === 0 ? <p>Your wishlist is ready for products you love.</p> : wishlist.map((product) => <div className="wishlist-row" key={product.id}><img src={product.images[0]} alt={product.name} /><div><strong>{product.name}</strong><span>{formatINR(product.price)}</span></div><button disabled={frontendUnavailable || productUnavailable || cartUnavailable} onClick={() => { if (addToCart(product)) setIsWishlistOpen(false); }}>Add to Cart</button><button className="modal-close-btn" disabled={frontendUnavailable || productUnavailable} onClick={() => toggleWishlist(product)}><X size={16} /></button></div>)}
            </div>
          </div>
        </div>
      )}

      {profileDialogOpen && (
        <div className="modal-backdrop" onClick={() => setIsProfileOpen(false)}>
          <div className="modal-content animate-fade-in" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header"><h3>My Account</h3><button className="modal-close-btn" onClick={() => setIsProfileOpen(false)}><X size={18} /></button></div>
            <div className="profile-layout">
              <nav className="profile-menu">{['Personal Information', 'My Orders', 'Wishlist', 'Saved Addresses', 'Payment Methods', 'Notifications', 'Coupons', 'Reviews', 'Recently Viewed', 'Help & Support'].map((section) => <button key={section} className={profileSection === section ? 'active' : ''} onClick={() => setProfileSection(section)}>{section}</button>)}<button onClick={signOut}>Logout</button></nav>
              <div className="profile-content">
                <h4>{profileSection}</h4>
                {profileSection === 'Personal Information' && <div><p><strong>{currentUser?.name || 'ShopSphere Customer'}</strong></p><p>{currentUser?.email || 'Sign in to save your profile details.'}</p><p>India · INR (₹)</p></div>}
                {profileSection === 'Saved Addresses' && <div><p>Home · Flat 402, Sea Crest Apartments, Bandra West, Mumbai 400050</p><p>Office · Suite 800, Tech Park, BKC, Mumbai 400051</p></div>}
                {profileSection === 'Payment Methods' && <div><p><Wallet size={16} /> UPI · Cards · Net Banking · Cash on Delivery</p><p>Payments are simulated for this demo.</p></div>}
                {profileSection === 'Coupons' && <div><p><Tag size={16} /> SAVE500 · ₹500 off on orders above ₹5,000</p><p>HDFC10 · 10% instant discount on HDFC cards</p></div>}
                {profileSection === 'Help & Support' && <p><Headphones size={16} /> Support is available from 9 AM to 9 PM IST. Contact support@shopsphere.in.</p>}
                {profileSection === 'Reviews' && <p>Your product reviews will appear here after delivery.</p>}
                {profileSection === 'Recently Viewed' && (recentlyViewed.length ? recentlyViewed.map((product) => <button key={product.id} className="profile-product-link" onClick={() => { setIsProfileOpen(false); navigateToProduct(product); }}>{product.name}</button>) : <p>Your recently viewed products will appear here.</p>)}
                {profileSection === 'My Orders' && <button onClick={() => { setIsProfileOpen(false); setIsOrdersOpen(true); navigate('/orders'); }}>View orders ({placedOrders.length})</button>}
                {profileSection === 'Wishlist' && <button onClick={() => { setIsProfileOpen(false); setIsWishlistOpen(true); }}>View wishlist ({wishlist.length})</button>}
                {profileSection === 'Notifications' && <button onClick={() => { setIsProfileOpen(false); setIsNotificationsOpen(true); }}>View notifications</button>}
              </div>
            </div>
          </div>
        </div>
      )}

      {isNotificationsOpen && (
        <div className="modal-backdrop" onClick={() => setIsNotificationsOpen(false)}>
          <div className="modal-content animate-fade-in" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header"><h3>Notifications</h3><button className="modal-close-btn" onClick={() => setIsNotificationsOpen(false)}><X size={18} /></button></div>
            <div className="modal-body notification-list">
              {placedOrders.slice(0, 3).map((order) => <p key={order.order_id}><CheckCircle size={16} /> {({ PLACED: 'Order placed', CONFIRMED: 'Order confirmed', PACKED: 'Order packed', SHIPPED: 'Order shipped', 'OUT FOR DELIVERY': 'Order is out for delivery', DELIVERED: 'Order delivered', CANCELLED: 'Order cancelled' })[order.status] || 'Order update'} · {order.order_id} · {order.paymentStatus === 'cash_on_delivery' ? 'Cash on delivery' : 'Payment not processed in demo'}</p>)}
              <p><Tag size={16} /> 10% instant discount on HDFC cards is available today.</p>
              <p><Sparkles size={16} /> Your weekly ShopSphere deals are ready.</p>
              <p><Bell size={16} /> Price drop alerts and back-in-stock updates are enabled for your wishlist.</p>
            </div>
          </div>
        </div>
      )}

      {/* Toast popup */}
      {toastMsg && (
        <div className="shopsphere-toast animate-fade-in">
          <Sparkles size={16} />
          <span>{toastMsg}</span>
        </div>
      )}
      </div>
    </div>
  );
};

export default ShopSphere;
