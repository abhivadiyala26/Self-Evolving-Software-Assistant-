// dashboard/src/data/products.js

export const CATEGORIES = [
  { id: 'all', name: 'All Categories', icon: 'Sparkles' },
  { id: 'mobiles', name: 'Mobiles', icon: 'Smartphone' },
  { id: 'laptops', name: 'Laptops', icon: 'Laptop' },
  { id: 'electronics', name: 'Electronics', icon: 'Tv' },
  { id: 'tvs', name: 'TVs', icon: 'Tv' },
  { id: 'headphones', name: 'Headphones', icon: 'Headphones' },
  { id: 'watches', name: 'Smart Watches', icon: 'Watch' },
  { id: 'fashion', name: 'Fashion', icon: 'Shirt' },
  { id: 'mens-clothing', name: "Men's Clothing", icon: 'Shirt' },
  { id: 'womens-clothing', name: "Women's Clothing", icon: 'Shirt' },
  { id: 'footwear', name: 'Footwear', icon: 'Footprints' },
  { id: 'home-appliances', name: 'Home Appliances', icon: 'Refrigerator' },
  { id: 'grocery', name: 'Grocery', icon: 'ShoppingBasket' },
  { id: 'beauty', name: 'Beauty', icon: 'Sparkles' },
  { id: 'books', name: 'Books', icon: 'BookOpen' },
  { id: 'gaming', name: 'Gaming', icon: 'Gamepad2' },
  { id: 'accessories', name: 'Accessories', icon: 'Package' },
];

export const MOCK_PRODUCTS = [
  // MOBILES
  {
    id: 'prod-mob-1',
    name: 'Galaxy Ultra 5G (12GB RAM, 256GB Storage)',
    category: 'mobiles',
    brand: 'Samsung',
    price: 109999,
    originalPrice: 129999,
    discount: 15,
    rating: 4.6,
    reviewCount: 3420,
    stock: 45,
    seller: 'RetailNet India',
    deliveryEstimate: 'Tomorrow by 11 AM',
    images: [
      'https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&q=80',
      'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&q=80'
    ],
    description: 'Dynamic AMOLED 2X 120Hz display, 200MP Camera with Nightography, Snapdragon 8 Gen 3 Processor, All-day 5000mAh Battery.',
    specs: {
      Display: '6.8 inch QHD+ Dynamic AMOLED',
      Processor: 'Snapdragon 8 Gen 3',
      Camera: '200MP + 50MP + 12MP + 10MP',
      Battery: '5000 mAh with 45W Fast Charge'
    }
  },
  {
    id: 'prod-mob-2',
    name: 'iPhone 15 Pro Max (256GB, Titanium)',
    category: 'mobiles',
    brand: 'Apple',
    price: 139900,
    originalPrice: 149900,
    discount: 7,
    rating: 4.8,
    reviewCount: 5120,
    stock: 18,
    seller: 'Appario Retail',
    deliveryEstimate: 'Tomorrow by 2 PM',
    images: [
      'https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&q=80',
      'https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=600&q=80'
    ],
    description: 'Forged in titanium, A17 Pro chip, Action Button, 48MP main camera with 5x Telephoto zoom.',
    specs: {
      Display: '6.7 inch Super Retina XDR OLED',
      Processor: 'A17 Pro Bionic',
      Camera: '48MP Main + 12MP Ultra Wide + 12MP Telephoto',
      Battery: 'Up to 29 hours video playback'
    }
  },
  {
    id: 'prod-mob-3',
    name: 'OnePlus 12 5G (16GB RAM, 512GB)',
    category: 'mobiles',
    brand: 'OnePlus',
    price: 64999,
    originalPrice: 69999,
    discount: 7,
    rating: 4.5,
    reviewCount: 1890,
    stock: 60,
    seller: 'OnePlus Official',
    deliveryEstimate: 'Delivery by 2 Days',
    images: [
      'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&q=80'
    ],
    description: 'Snapdragon 8 Gen 3, 4th Gen Hasselblad Camera for Mobile, 100W SUPERVOOC Charging.',
    specs: {
      Display: '6.82 inch 120Hz 2K ProXDR',
      Processor: 'Snapdragon 8 Gen 3',
      Camera: '50MP Sony LYT-808 + 64MP Periscope',
      Battery: '5400 mAh with 100W Wired'
    }
  },

  // LAPTOPS
  {
    id: 'prod-lap-1',
    name: 'MacBook Air M3 (16GB, 512GB SSD, Midnight)',
    category: 'laptops',
    brand: 'Apple',
    price: 124900,
    originalPrice: 134900,
    discount: 7,
    rating: 4.9,
    reviewCount: 980,
    stock: 25,
    seller: 'Apple India',
    deliveryEstimate: 'Tomorrow by 11 AM',
    images: [
      'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&q=80',
      'https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=600&q=80'
    ],
    description: 'Incredibly thin and fast MacBook Air powered by the M3 chip. Up to 18 hours of battery life.',
    specs: {
      Display: '13.6 inch Liquid Retina',
      Processor: 'Apple M3 8-core CPU',
      RAM: '16GB Unified Memory',
      Storage: '512GB SSD'
    }
  },
  {
    id: 'prod-lap-2',
    name: 'ROG Strix G16 Gaming Laptop (RTX 4070, i7-13650HX)',
    category: 'laptops',
    brand: 'ASUS',
    price: 159990,
    originalPrice: 189990,
    discount: 16,
    rating: 4.7,
    reviewCount: 430,
    stock: 12,
    seller: 'Clicktech Retail',
    deliveryEstimate: 'Delivery by 3 Days',
    images: [
      'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&q=80'
    ],
    description: 'Power through Windows 11 gaming with Intel Core i7-13650HX CPU and NVIDIA GeForce RTX 4070 Laptop GPU.',
    specs: {
      Display: '16 inch FHD+ 165Hz 100% sRGB',
      Processor: 'Intel Core i7-13650HX',
      Graphics: 'NVIDIA GeForce RTX 4070 8GB',
      RAM: '16GB DDR5 + 1TB PCIe 4.0 NVMe SSD'
    }
  },

  // HEADPHONES
  {
    id: 'prod-head-1',
    name: 'Sony WH-1000XM5 Wireless Noise Cancelling Headphones',
    category: 'headphones',
    brand: 'Sony',
    price: 26990,
    originalPrice: 34990,
    discount: 23,
    rating: 4.6,
    reviewCount: 4890,
    stock: 80,
    seller: 'Sony Center',
    deliveryEstimate: 'Tomorrow by 5 PM',
    images: [
      'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80',
      'https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=600&q=80'
    ],
    description: 'Industry leading noise canceling with 8 microphones and Auto NC Optimizer. Up to 30-hour battery life.',
    specs: {
      Type: 'Over-Ear Wireless',
      Battery: '30 Hours with Quick Charge',
      NoiseCancellation: 'Industry Leading Active Noise Cancellation',
      Bluetooth: 'v5.2 with LDAC codec'
    }
  },
  {
    id: 'prod-head-2',
    name: 'AirPods Pro 2nd Gen with MagSafe Case (USB-C)',
    category: 'headphones',
    brand: 'Apple',
    price: 22900,
    originalPrice: 24900,
    discount: 8,
    rating: 4.8,
    reviewCount: 6100,
    stock: 50,
    seller: 'Appario Retail',
    deliveryEstimate: 'Tomorrow by 11 AM',
    images: [
      'https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=600&q=80'
    ],
    description: 'Up to 2x more Active Noise Cancellation, Transparency mode, Adaptive Audio, Personalised Spatial Audio.',
    specs: {
      Type: 'True Wireless In-Ear',
      Chip: 'Apple H2 Headphone Chip',
      Battery: 'Up to 6 hours listening time',
      Case: 'MagSafe (USB-C) with speaker and lanyard loop'
    }
  },

  // WATCHES
  {
    id: 'prod-wat-1',
    name: 'Galaxy Watch 6 Classic 47mm Bluetooth',
    category: 'watches',
    brand: 'Samsung',
    price: 32999,
    originalPrice: 40999,
    discount: 19,
    rating: 4.4,
    reviewCount: 890,
    stock: 30,
    seller: 'RetailNet India',
    deliveryEstimate: 'Delivery in 2 Days',
    images: [
      'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80'
    ],
    description: 'Iconic rotating bezel, Advanced Sleep Coaching, ECG & Blood Pressure Monitoring, Sapphire Crystal Glass.',
    specs: {
      Display: '1.5 inch Super AMOLED',
      Material: 'Stainless Steel Case with Hybrid Leather Band',
      Sensors: 'BioActive Sensor, Temperature, ECG, Heart Rate',
      WaterResistance: '5ATM + IP68'
    }
  },

  // ELECTRONICS
  {
    id: 'prod-elec-1',
    name: 'Sony Bravia 55 inch 4K Ultra HD Smart LED Google TV',
    category: 'electronics',
    brand: 'Sony',
    price: 57990,
    originalPrice: 99900,
    discount: 42,
    rating: 4.7,
    reviewCount: 3100,
    stock: 15,
    seller: 'Sony Retail',
    deliveryEstimate: 'Tomorrow by 8 PM',
    images: [
      'https://images.unsplash.com/photo-1593784991095-a205069470b6?w=600&q=80'
    ],
    description: '4K Processor X1, Motionflow XR 200, Dolby Audio, Google TV with Voice Search, Apple AirPlay support.',
    specs: {
      Display: '55 inch 4K Ultra HD (3840 x 2160)',
      Audio: '20W Dolby Audio Speakers',
      SmartTV: 'Google TV with Chromecast Built-in',
      RefreshRate: '60 Hz'
    }
  },

  // FASHION
  {
    id: 'prod-fash-1',
    name: 'Men Slim Fit Denim Jacket',
    category: 'fashion',
    brand: 'Levi\'s',
    price: 2499,
    originalPrice: 4999,
    discount: 50,
    rating: 4.3,
    reviewCount: 1520,
    stock: 100,
    seller: 'Levi Store',
    deliveryEstimate: 'Delivery in 3 Days',
    images: [
      'https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=600&q=80'
    ],
    description: 'Classic Trucker Jacket cut from pure cotton denim. Timeless fit with side welt pockets.',
    specs: {
      Material: '100% Cotton Denim',
      Fit: 'Slim Fit',
      Care: 'Machine Wash Cold'
    }
  },

  // APPLIANCES
  {
    id: 'prod-app-1',
    name: 'Front Load Fully Automatic Washing Machine (8 kg)',
    category: 'home-appliances',
    brand: 'Bosch',
    price: 34990,
    originalPrice: 48990,
    discount: 28,
    rating: 4.6,
    reviewCount: 2150,
    stock: 20,
    seller: 'Bosch Home Appliances',
    deliveryEstimate: 'Delivery by 2 Days',
    images: [
      'https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?w=600&q=80'
    ],
    description: 'EcoSilence Drive motor, AntiVibration design, 1400 RPM spin speed, Hygiene Plus program.',
    specs: {
      Capacity: '8 Kg',
      SpinSpeed: '1400 RPM',
      EnergyRating: '5 Star 5-Star BEE',
      Motor: 'EcoSilence Drive Frictionless Motor'
    }
  },

  // GAMING
  {
    id: 'prod-game-1',
    name: 'PlayStation 5 Console (Slim Edition)',
    category: 'gaming',
    brand: 'Sony',
    price: 54990,
    originalPrice: 54990,
    discount: 0,
    rating: 4.9,
    reviewCount: 7890,
    stock: 35,
    seller: 'Sony Center',
    deliveryEstimate: 'Tomorrow by 12 PM',
    images: [
      'https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=600&q=80'
    ],
    description: 'Experience lightning fast loading with ultra-high speed SSD, deeper immersion with haptic feedback, 3D Audio.',
    specs: {
      Storage: '1TB Ultra High Speed SSD',
      Output: '4K 120Hz & 8K Support',
      Audio: 'Tempest 3D AudioTech',
      Controller: 'DualSense Wireless Controller included'
    }
  },
  { id: 'prod-mob-4', name: 'Redmi Note 14 Pro 5G (8GB, 256GB)', category: 'mobiles', brand: 'Redmi', price: 24999, originalPrice: 28999, discount: 14, rating: 4.4, reviewCount: 1840, stock: 38, seller: 'Mi Store India', deliveryEstimate: 'Free delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&q=80'], description: 'AMOLED 5G smartphone with a 200MP camera, fast charging and all-day battery.', specs: { Display: '6.67 inch AMOLED 120Hz', Storage: '256GB', Battery: '5110 mAh' } },
  { id: 'prod-mob-5', name: 'Apple iPhone 16 (128GB)', category: 'mobiles', brand: 'Apple', price: 69900, originalPrice: 79900, discount: 13, rating: 4.7, reviewCount: 2650, stock: 21, seller: 'Imagine Store', deliveryEstimate: 'Delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=600&q=80'], description: 'A16-powered iPhone with a bright Super Retina display and advanced dual camera system.', specs: { Display: '6.1 inch Super Retina XDR', Storage: '128GB', Camera: '48MP Fusion' } },
  { id: 'prod-lap-3', name: 'HP Pavilion 14 (Core i5, 16GB, 512GB SSD)', category: 'laptops', brand: 'HP', price: 62990, originalPrice: 74990, discount: 16, rating: 4.3, reviewCount: 970, stock: 16, seller: 'HP World', deliveryEstimate: 'Free delivery in 2 Days', images: ['https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&q=80'], description: 'Portable everyday laptop with a 13th Gen Intel Core processor and fast NVMe storage.', specs: { Display: '14 inch FHD IPS', Processor: 'Intel Core i5', Memory: '16GB RAM + 512GB SSD' } },
  { id: 'prod-lap-4', name: 'Dell Inspiron 15 (Core i5, 16GB, 512GB SSD)', category: 'laptops', brand: 'Dell', price: 58990, originalPrice: 69990, discount: 16, rating: 4.2, reviewCount: 1210, stock: 24, seller: 'Dell Exclusive Store', deliveryEstimate: 'Delivery in 2 Days', images: ['https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&q=80'], description: 'A dependable 15 inch laptop for study, work and everyday entertainment.', specs: { Display: '15.6 inch FHD', Processor: 'Intel Core i5', Memory: '16GB RAM + 512GB SSD' } },
  { id: 'prod-lap-5', name: 'Lenovo IdeaPad Slim 5 (Ryzen 7, 16GB)', category: 'laptops', brand: 'Lenovo', price: 67990, originalPrice: 79990, discount: 15, rating: 4.4, reviewCount: 740, stock: 19, seller: 'Lenovo India', deliveryEstimate: 'Free delivery by Friday', images: ['https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&q=80'], description: 'Thin-and-light performance laptop with a vivid display and rapid charging.', specs: { Display: '14 inch WUXGA OLED', Processor: 'AMD Ryzen 7', Memory: '16GB RAM + 1TB SSD' } },
  { id: 'prod-head-3', name: 'boAt Airdopes 141 Bluetooth Earbuds', category: 'headphones', brand: 'boAt', price: 1299, originalPrice: 2990, discount: 57, rating: 4.1, reviewCount: 12600, stock: 120, seller: 'Imagine Marketing', deliveryEstimate: 'Free delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?w=600&q=80'], description: 'Lightweight true wireless earbuds with touch controls and a compact charging case.', specs: { Playtime: 'Up to 42 hours', Bluetooth: 'v5.3', Charging: 'USB Type-C' } },
  { id: 'prod-watch-2', name: 'Noise ColorFit Pro 5 Smart Watch', category: 'watches', brand: 'Noise', price: 3999, originalPrice: 7999, discount: 50, rating: 4.2, reviewCount: 2380, stock: 43, seller: 'Noise Official', deliveryEstimate: 'Delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80'], description: 'AMOLED smartwatch with Bluetooth calling, health tracking and multiple sports modes.', specs: { Display: '1.85 inch AMOLED', Battery: 'Up to 7 days', Resistance: 'IP68' } },
  { id: 'prod-watch-3', name: 'Apple Watch SE GPS 40mm', category: 'watches', brand: 'Apple', price: 24900, originalPrice: 29900, discount: 17, rating: 4.6, reviewCount: 1360, stock: 17, seller: 'Apple Authorised Reseller', deliveryEstimate: 'Delivery in 2 Days', images: ['https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=600&q=80'], description: 'Essential health, fitness and safety features in a comfortable lightweight watch.', specs: { Size: '40mm GPS', Display: 'Retina LTPO OLED', WaterResistance: '50 metres' } },
  { id: 'prod-tv-2', name: 'Samsung Crystal 4K UHD Smart TV 55 inch', category: 'tvs', brand: 'Samsung', price: 46990, originalPrice: 69900, discount: 33, rating: 4.5, reviewCount: 2860, stock: 12, seller: 'Samsung Smart Plaza', deliveryEstimate: 'Free installation in 2 Days', images: ['https://images.unsplash.com/photo-1593784991095-a205069470b6?w=600&q=80'], description: '4K smart television with Crystal Processor 4K, HDR and built-in streaming apps.', specs: { Display: '55 inch 4K UHD', OS: 'Tizen Smart TV', Audio: '20W Dolby Digital Plus' } },
  { id: 'prod-home-2', name: 'Philips Digital Air Fryer HD9252/90', category: 'home-appliances', brand: 'Philips', price: 7999, originalPrice: 11995, discount: 33, rating: 4.4, reviewCount: 1990, stock: 26, seller: 'Philips Domestic Appliances', deliveryEstimate: 'Delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1585515320310-259814833e62?w=600&q=80'], description: 'Rapid Air technology for crisp results with little or no added oil.', specs: { Capacity: '4.1 litres', Power: '1400W', Presets: '7 cooking presets' } },
  { id: 'prod-shoe-1', name: 'Nike Revolution 7 Road Running Shoes', category: 'footwear', brand: 'Nike', price: 3695, originalPrice: 4995, discount: 26, rating: 4.3, reviewCount: 780, stock: 31, seller: 'Nike India', deliveryEstimate: 'Free delivery in 3 Days', images: ['https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80'], description: 'Cushioned everyday running shoes with a breathable mesh upper.', specs: { Type: 'Road running', Closure: 'Lace-up', Fit: 'Regular' } },
  { id: 'prod-shoe-2', name: 'Puma Smashic Casual Sneakers', category: 'footwear', brand: 'Puma', price: 2499, originalPrice: 3999, discount: 38, rating: 4.2, reviewCount: 530, stock: 48, seller: 'Puma Store', deliveryEstimate: 'Delivery in 3 Days', images: ['https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=600&q=80'], description: 'Classic court-inspired sneakers designed for daily comfort.', specs: { Upper: 'Synthetic leather', Sole: 'Rubber', Closure: 'Lace-up' } },
  { id: 'prod-men-1', name: 'Allen Solly Men Regular Fit Cotton Shirt', category: 'mens-clothing', brand: 'Allen Solly', price: 1499, originalPrice: 2499, discount: 40, rating: 4.1, reviewCount: 610, stock: 65, seller: 'Aditya Birla Fashion', deliveryEstimate: 'Delivery in 3 Days', images: ['https://images.unsplash.com/photo-1603252109303-2751441dd157?w=600&q=80'], description: 'Versatile cotton shirt suited to office wear and weekend outings.', specs: { Material: '100% Cotton', Fit: 'Regular', Sleeve: 'Full sleeve' } },
  { id: 'prod-women-1', name: 'Women Printed Cotton Straight Kurta', category: 'womens-clothing', brand: 'Aurelia', price: 1199, originalPrice: 1999, discount: 40, rating: 4.2, reviewCount: 420, stock: 54, seller: 'Aurelia Store', deliveryEstimate: 'Delivery in 3 Days', images: ['https://images.unsplash.com/photo-1583391733958-d4a0f3f2ef72?w=600&q=80'], description: 'Comfortable breathable cotton kurta with a subtle all-over print.', specs: { Fabric: 'Cotton', Length: 'Calf length', Care: 'Machine wash' } },
  { id: 'prod-acc-1', name: 'American Tourister Casual Backpack 28L', category: 'accessories', brand: 'American Tourister', price: 1899, originalPrice: 3299, discount: 42, rating: 4.3, reviewCount: 1120, stock: 70, seller: 'VIP Industries', deliveryEstimate: 'Free delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&q=80'], description: 'Durable everyday backpack with a padded laptop sleeve and organiser pockets.', specs: { Capacity: '28 litres', LaptopSleeve: 'Up to 15.6 inch', Warranty: '1 year' } },
  { id: 'prod-acc-2', name: 'Logitech K380 Multi-Device Bluetooth Keyboard', category: 'accessories', brand: 'Logitech', price: 2995, originalPrice: 3995, discount: 25, rating: 4.5, reviewCount: 840, stock: 39, seller: 'Logitech Store', deliveryEstimate: 'Delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&q=80'], description: 'Compact wireless keyboard that pairs with computers, tablets and phones.', specs: { Connectivity: 'Bluetooth', Battery: '2 AAA batteries', Devices: 'Up to 3 paired devices' } },
  { id: 'prod-acc-3', name: 'Redragon M612 Predator Gaming Mouse', category: 'accessories', brand: 'Redragon', price: 1599, originalPrice: 2499, discount: 36, rating: 4.4, reviewCount: 670, stock: 42, seller: 'Redragon India', deliveryEstimate: 'Delivery in 2 Days', images: ['https://images.unsplash.com/photo-1527814050087-3793815479db?w=600&q=80'], description: 'Wired gaming mouse with adjustable DPI, programmable buttons and RGB lighting.', specs: { DPI: 'Up to 8000', Buttons: '11 programmable', Connection: 'USB wired' } },
  { id: 'prod-acc-4', name: 'JBL Go 3 Portable Bluetooth Speaker', category: 'accessories', brand: 'JBL', price: 2999, originalPrice: 4499, discount: 33, rating: 4.5, reviewCount: 1810, stock: 33, seller: 'JBL by Harman', deliveryEstimate: 'Free delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&q=80'], description: 'Pocket-sized speaker with punchy sound and an IP67 waterproof design.', specs: { Battery: 'Up to 5 hours', Bluetooth: 'v5.1', Resistance: 'IP67' } },
  { id: 'prod-acc-5', name: 'Mi Power Bank 4i 20000mAh', category: 'accessories', brand: 'Xiaomi', price: 2199, originalPrice: 2999, discount: 27, rating: 4.3, reviewCount: 2250, stock: 90, seller: 'Mi Store India', deliveryEstimate: 'Delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=600&q=80'], description: 'High-capacity power bank with 33W fast charging and triple output ports.', specs: { Capacity: '20000mAh', Output: 'Up to 33W', Ports: '2 USB-A + USB-C' } },
  { id: 'prod-electronics-2', name: 'LG UltraGear 27 inch QHD Gaming Monitor', category: 'electronics', brand: 'LG', price: 22999, originalPrice: 31999, discount: 28, rating: 4.5, reviewCount: 760, stock: 14, seller: 'LG Electronics', deliveryEstimate: 'Delivery in 2 Days', images: ['https://images.unsplash.com/photo-1527443154391-507e9dc6c5cc?w=600&q=80'], description: 'Fast IPS gaming monitor with a sharp QHD panel and adaptive sync.', specs: { Resolution: '2560 x 1440', RefreshRate: '165Hz', Response: '1ms' } },
  { id: 'prod-electronics-3', name: 'Samsung Galaxy Tab S9 FE Wi-Fi 128GB', category: 'electronics', brand: 'Samsung', price: 32999, originalPrice: 39999, discount: 18, rating: 4.4, reviewCount: 510, stock: 18, seller: 'Samsung Store', deliveryEstimate: 'Delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&q=80'], description: 'Versatile tablet with an immersive display, S Pen support and long battery life.', specs: { Display: '10.9 inch LCD', Storage: '128GB', Resistance: 'IP68' } },
  { id: 'prod-electronics-4', name: 'Canon EOS R50 Mirrorless Camera with 18-45mm Lens', category: 'electronics', brand: 'Canon', price: 69990, originalPrice: 75995, discount: 8, rating: 4.6, reviewCount: 280, stock: 8, seller: 'Canon Image Square', deliveryEstimate: 'Delivery in 3 Days', images: ['https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&q=80'], description: 'Compact mirrorless camera with 4K video and reliable subject tracking.', specs: { Sensor: '24.2MP APS-C CMOS', Video: '4K UHD', Mount: 'RF-S' } },
  { id: 'prod-electronics-5', name: 'HP Smart Tank 589 All-in-One Printer', category: 'electronics', brand: 'HP', price: 13999, originalPrice: 16999, discount: 18, rating: 4.2, reviewCount: 330, stock: 11, seller: 'HP India', deliveryEstimate: 'Delivery in 2 Days', images: ['https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&q=80'], description: 'Wireless all-in-one printer for home printing, scanning and copying.', specs: { Functions: 'Print, scan, copy', Connectivity: 'Wi-Fi + USB', InBox: 'Ink for thousands of pages' } },
  { id: 'prod-health-1', name: 'Mi Smart Band 8 Active Fitness Tracker', category: 'watches', brand: 'Xiaomi', price: 1499, originalPrice: 2499, discount: 40, rating: 4.1, reviewCount: 980, stock: 57, seller: 'Mi Store India', deliveryEstimate: 'Free delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1557935728-e6d1eaabe558?w=600&q=80'], description: 'Lightweight fitness band with activity, sleep and heart-rate tracking.', specs: { Display: '1.47 inch TFT', Battery: 'Up to 14 days', Modes: '50+ sports modes' } },
  { id: 'prod-book-1', name: 'The Design of Everyday Things (Revised Edition)', category: 'books', brand: 'Basic Books', price: 599, originalPrice: 799, discount: 25, rating: 4.6, reviewCount: 840, stock: 35, seller: 'Crossword India', deliveryEstimate: 'Delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=600&q=80'], description: 'A practical, engaging guide to design that works for people.', specs: { Format: 'Paperback', Language: 'English', Pages: '368' } },
  { id: 'prod-beauty-1', name: 'Minimalist 10% Vitamin C Face Serum 30ml', category: 'beauty', brand: 'Minimalist', price: 599, originalPrice: 699, discount: 14, rating: 4.2, reviewCount: 1520, stock: 44, seller: 'Minimalist Official', deliveryEstimate: 'Delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1601049541289-9b1b7bbbfe19?w=600&q=80'], description: 'Daily antioxidant serum formulated for a brighter, even-looking complexion.', specs: { Volume: '30ml', SkinType: 'All skin types', Usage: 'AM routine with sunscreen' } },
  { id: 'prod-grocery-1', name: 'Tata Sampann Everyday Pantry Essentials Pack', category: 'grocery', brand: 'Tata Sampann', price: 899, originalPrice: 1099, discount: 18, rating: 4.3, reviewCount: 390, stock: 28, seller: 'Tata Consumer Products', deliveryEstimate: 'Delivery by Tomorrow', images: ['https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&q=80'], description: 'A convenient pantry pack with everyday pulses, spices and staples.', specs: { PackSize: 'Assorted essentials', Storage: 'Store in a cool dry place', Origin: 'India' } }
];
