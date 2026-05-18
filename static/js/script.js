// ── getCookie helper ──────────────────────────────────────────────
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ── Toast Notifications ───────────────────────────────────────────
function showToast(message, type = 'success', duration = 3500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <span class="toast-msg">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => toast.classList.add('show'));

    // Auto-remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, duration);
}

// ── Form Validation ───────────────────────────────────────────────
function validateField(inputId, errorId, rules) {
    const input = document.getElementById(inputId);
    const error = document.getElementById(errorId);
    if (!input || !error) return true;

    const value = input.value.trim();
    let message = '';

    if (rules.required && !value) {
        message = rules.requiredMsg || 'This field is required.';
    } else if (rules.email && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            message = 'Please enter a valid email address.';
        }
    } else if (rules.minLength && value.length < rules.minLength) {
        message = `Must be at least ${rules.minLength} characters.`;
    } else if (rules.match) {
        const matchVal = document.getElementById(rules.match).value;
        if (value !== matchVal) {
            message = rules.matchMsg || 'Fields do not match.';
        }
    }

    if (message) {
        input.classList.add('input-error');
        input.classList.remove('input-success');
        error.textContent = message;
        error.classList.add('show');
        return false;
    } else {
        input.classList.remove('input-error');
        input.classList.add('input-success');
        error.classList.remove('show');
        return true;
    }
}

function clearError(inputId, errorId) {
    const input = document.getElementById(inputId);
    const error = document.getElementById(errorId);
    if (input) {
        input.classList.remove('input-error');
        input.classList.remove('input-success');
    }
    if (error) error.classList.remove('show');
}

function checkStrength(password) {
    const bar = document.getElementById('strengthBar');
    const label = document.getElementById('strengthLabel');
    if (!bar || !label) return;

    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    const levels = [
        { label: '', color: '#eee', width: '0%' },
        { label: 'Very Weak', color: '#e74c3c', width: '20%' },
        { label: 'Weak', color: '#e67e22', width: '40%' },
        { label: 'Fair', color: '#f1c40f', width: '60%' },
        { label: 'Strong', color: '#2ecc71', width: '80%' },
        { label: 'Very Strong', color: '#27ae60', width: '100%' },
    ];

    const level = levels[score] || levels[0];
    bar.style.width = level.width;
    bar.style.background = level.color;
    label.textContent = level.label;
    label.style.color = level.color;
}

function initPasswordToggles() {
    document.querySelectorAll('.password-toggle').forEach((button) => {
        const inputId = button.getAttribute('data-target');
        const input = inputId ? document.getElementById(inputId) : null;
        const icon = button.querySelector('i');
        if (!input) return;

        button.addEventListener('click', () => {
            const showPassword = input.type === 'password';
            input.type = showPassword ? 'text' : 'password';
            button.setAttribute('aria-label', showPassword ? 'Hide password' : 'Show password');
            button.setAttribute('title', showPassword ? 'Hide password' : 'Show password');
            if (icon) {
                icon.classList.toggle('fa-eye', !showPassword);
                icon.classList.toggle('fa-eye-slash', showPassword);
            }
        });
    });
}

document.addEventListener('DOMContentLoaded', initPasswordToggles);

function toggleMobileMenu() {
    const navLinks = document.getElementById('navLinks');
    const hamburger = document.getElementById('hamburgerBtn');
    if (navLinks) navLinks.classList.toggle('open');
    if (hamburger) hamburger.classList.toggle('active');
}

function navigateWithTransition(url) {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) {
        window.location.href = url;
        return;
    }

    document.body.classList.add('page-is-leaving');
    setTimeout(() => {
        window.location.href = url;
    }, 220);
}

// ── User dropdown toggle ──────────────────────────────────────────
function toggleDropdown(event) {
    event.stopPropagation();
    const menu = document.getElementById('userDropdown');
    if (menu) menu.classList.toggle('show');
}

// Close dropdown when clicking anywhere outside it
document.addEventListener('click', function(e) {
    const dropdown = document.querySelector('.user-dropdown');
    if (dropdown && !dropdown.contains(e.target)) {
        const menu = document.getElementById('userDropdown');
        if (menu) menu.classList.remove('show');
    }
});

// ── Logout ────────────────────────────────────────────────────────
async function logoutUser() {
    try {
        const response = await fetch('/logout-user/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
        });
        const result = await response.json();
        if (result.success) {
            localStorage.removeItem('loggedInUser');
            localStorage.removeItem('loggedInEmail');
            localStorage.removeItem('bikoCart');
            navigateWithTransition('/');
        }
    } catch (err) {
        // Force redirect even if fetch fails
        navigateWithTransition('/');
    }
}


// Product Database
const products = {
  'p1': { id: 'p1', name: 'Bilao (The Party Favorite)', price: 500, image: '/static/images/biko_bilao_1778184493482.png' },
  'p2': { id: 'p2', name: 'Biko Microwavable Container', price: 100, image: '/static/images/biko_container_1778184629253.png' }
};

// Cart logic
function updateCartCount() {
    const cart = JSON.parse(
        localStorage.getItem('bikoCart') || '[]'
    );
    const total = cart.reduce((sum, item) => sum + item.quantity, 0);
    const badge = document.getElementById('cartCount');
    if (badge) badge.textContent = total;
}

function animateProductToCart(image, trigger) {
    const cartIcon = document.querySelector('.cart-icon');
    const sourceImage = trigger
        ?.closest('.product-card')
        ?.querySelector('.product-img');

    if (!cartIcon || !trigger || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    const sourceRect = sourceImage
        ? sourceImage.getBoundingClientRect()
        : trigger.getBoundingClientRect();
    const cartRect = cartIcon.getBoundingClientRect();
    const flyer = document.createElement('img');

    flyer.src = image;
    flyer.alt = '';
    flyer.className = 'cart-flyer';
    flyer.style.left = `${sourceRect.left}px`;
    flyer.style.top = `${sourceRect.top}px`;
    flyer.style.width = `${sourceRect.width}px`;
    flyer.style.height = `${sourceRect.height}px`;

    document.body.appendChild(flyer);

    const startCenterX = sourceRect.left + sourceRect.width / 2;
    const startCenterY = sourceRect.top + sourceRect.height / 2;
    const endCenterX = cartRect.left + cartRect.width / 2;
    const endCenterY = cartRect.top + cartRect.height / 2;

    requestAnimationFrame(() => {
        flyer.style.transform = `
            translate(${endCenterX - startCenterX}px, ${endCenterY - startCenterY}px)
            scale(0.14)
        `;
        flyer.style.opacity = '0.25';
        flyer.style.borderRadius = '50%';
    });

    flyer.addEventListener('transitionend', () => {
        flyer.remove();
        cartIcon.classList.add('cart-icon-bump');
        setTimeout(() => cartIcon.classList.remove('cart-icon-bump'), 450);
    }, { once: true });
}

function addToCart(name, price, image, trigger) {
    const cart = JSON.parse(
        localStorage.getItem('bikoCart') || '[]'
    );
    const existing = cart.find(i => i.name === name);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ 
            name: name, 
            price: price, 
            image: image,
            quantity: 1 
        });
    }
    localStorage.setItem('bikoCart', JSON.stringify(cart));
    animateProductToCart(image, trigger);
    updateCartCount();
}

function renderCart() {
  const container = document.getElementById('cart-items-container');
  if (!container) return;

  container.innerHTML = '';
  let subtotal = 0;

  if (cart.length === 0) {
    container.innerHTML = '<p>Your cart is empty.</p>';
    document.getElementById('cart-subtotal').textContent = '₱0';
    document.getElementById('cart-total').textContent = '₱0';
    return;
  }

  cart.forEach((item, index) => {
    const product = products[item.id];
    subtotal += product.price * item.quantity;
    
    const div = document.createElement('div');
    div.className = 'cart-item';
    div.innerHTML = `
      <img src="${product.image}" class="cart-item-img" alt="${product.name}">
      <div class="cart-item-info">
        <h4>${product.name}</h4>
        <div class="qty-controls">
          <button class="qty-btn" onclick="updateQuantity(${index}, -1)">-</button>
          <span>${item.quantity}</span>
          <button class="qty-btn" onclick="updateQuantity(${index}, 1)">+</button>
        </div>
      </div>
      <div class="item-price">₱${product.price * item.quantity}</div>
    `;
    container.appendChild(div);
  });

  const shipping = 50; // default standard shipping
  document.getElementById('cart-subtotal').textContent = '₱' + subtotal;
  document.getElementById('cart-shipping').textContent = '₱' + shipping;
  document.getElementById('cart-total').textContent = '₱' + (subtotal + shipping);
}

function updateQuantity(index, change) {
  cart[index].quantity += change;
  if (cart[index].quantity <= 0) {
    cart.splice(index, 1);
  }
  localStorage.setItem('gagahBikoCart', JSON.stringify(cart));
  updateCartCount();
  renderCart();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  updateCartCount();
  renderCart();

  const checkoutForm = document.getElementById('checkout-form');
  if (checkoutForm) {
    checkoutForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      // Validate fields
      const v1 = validateField('email', 'emailErr', { required: true, email: true });
      const v2 = validateField('phone', 'phoneErr', { required: true });
      const v3 = validateField('full_name', 'nameErr', { required: true });
      const v4 = validateField('address', 'addressErr', { required: true });
      const v5 = validateField('city', 'cityErr', { required: true });
      const v6 = validateField('postal_code', 'postalErr', { required: true });

      if (!v1 || !v2 || !v3 || !v4 || !v5 || !v6) return;

      const email = document.getElementById('email').value;
      const phone = document.getElementById('phone').value;
      const fullName = document.getElementById('full_name').value;
      const address = document.getElementById('address').value;
      const apartment = document.getElementById('apartment').value;
      const city = document.getElementById('city').value;
      const postalCode = document.getElementById('postal_code').value;
      
      const shippingMethod = document.querySelector('input[name="shipping"]:checked').value;
      const paymentMethod = document.getElementById('payment_method').value;
      
      let subtotal = 0;
      const items = cart.map(item => {
        const p = products[item.id];
        subtotal += p.price * item.quantity;
        return {
          product_name: p.name,
          quantity: item.quantity,
          price: p.price
        };
      });
      
      const shippingFee = shippingMethod === 'standard' ? 50 : 150;
      const total = subtotal + shippingFee;
      
      const orderData = {
        full_name: fullName,
        email: email,
        phone: phone,
        address: address,
        apartment: apartment,
        city: city,
        postal_code: postalCode,
        shipping_method: shippingMethod,
        payment_method: paymentMethod,
        subtotal: subtotal,
        shipping_fee: shippingFee,
        total: total,
        items: items
      };
      
      try {
        const response = await fetch(paymentMethod === 'gcash' ? '/create-paymongo-checkout-session/' : '/place-order/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify(orderData)
        });
        
        const result = await response.json();
        if (result.success) {
          if (result.checkout_url) {
            window.location.href = result.checkout_url;
          } else {
            localStorage.removeItem('gagahBikoCart');
            cart = [];
            navigateWithTransition(`/order-success/?id=${result.order_id}`);
          }
        } else {
          showToast('Error placing order: ' + result.error, 'error');
        }
      } catch (err) {
        showToast('Network error placing order. Please try again.', 'error');
      }
    });
    
    // Add event listeners to shipping radio buttons to update totals
    document.querySelectorAll('input[name="shipping"]').forEach(radio => {
      radio.addEventListener('change', () => {
        let subtotal = 0;
        cart.forEach(item => {
          subtotal += products[item.id].price * item.quantity;
        });
        const shippingFee = radio.value === 'standard' ? 50 : 150;
        document.getElementById('cart-shipping').textContent = '₱' + shippingFee;
        document.getElementById('cart-total').textContent = '₱' + (subtotal + shippingFee);
      });
    });
  }

  // ── Page Transitions ────────────────────────────────────────────
  document.querySelectorAll('a[href]').forEach(link => {
      link.addEventListener('click', function(e) {
          if (
              e.defaultPrevented ||
              e.metaKey ||
              e.ctrlKey ||
              e.shiftKey ||
              e.altKey ||
              link.target === '_blank' ||
              link.hasAttribute('download')
          ) {
              return;
          }

          const href = link.getAttribute('href');
          if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) return;

          const destination = new URL(href, window.location.href);
          const isSameSite = destination.origin === window.location.origin;
          const isHashOnly = destination.pathname === window.location.pathname && destination.hash;
          if (!isSameSite || isHashOnly) return;

          e.preventDefault();
          navigateWithTransition(destination.href);
      });
  });
});

window.addEventListener('pageshow', () => {
    document.body.classList.remove('page-is-leaving');
});

function setPayment(method) {
  const paymentMethod = document.getElementById('payment_method');
  if (paymentMethod) {
    paymentMethod.value = method;
  }

  const gcashNote = document.getElementById('gcash-payment-note');
  const codNote = document.getElementById('cod-payment-note');
  if (gcashNote) {
    gcashNote.hidden = method !== 'gcash';
  }
  if (codNote) {
    codNote.hidden = method !== 'cod';
  }
  
  // Update button styles
  const buttons = ['gcash', 'cod'];
  buttons.forEach(btn => {
    const el = document.getElementById('btn-' + btn);
    if (!el) return;
    el.classList.toggle('active', btn === method);
    if (el.classList.contains('payment-tab')) return;
    if (btn === method) {
      el.className = 'btn btn-primary';
    } else {
      el.className = 'btn btn-outline';
    }
  });
}
