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

// Product Database
const products = {
  'p1': { id: 'p1', name: 'Bilao (The Party Favorite)', price: 500, image: 'assets/biko_bilao_1778184493482.png' },
  'p2': { id: 'p2', name: 'Biko Microwavable Container', price: 100, image: 'assets/biko_container_1778184629253.png' }
};

// Cart State
let cart = JSON.parse(localStorage.getItem('gagahBikoCart')) || [];

function updateCartCount() {
  const count = cart.reduce((sum, item) => sum + item.quantity, 0);
  document.querySelectorAll('.cart-badge').forEach(badge => {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'block' : 'none';
  });
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

function addToCart(productId, trigger) {
  const item = cart.find(i => i.id === productId);
  if (item) {
    item.quantity += 1;
  } else {
    cart.push({ id: productId, quantity: 1 });
  }
  localStorage.setItem('gagahBikoCart', JSON.stringify(cart));
  animateProductToCart(products[productId].image, trigger);
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

function installPageTransitions() {
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
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  updateCartCount();
  renderCart();
  installPageTransitions();

  const checkoutForm = document.getElementById('checkout-form');
  if (checkoutForm) {
    checkoutForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
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
          alert('Error placing order: ' + result.error);
        }
      } catch (err) {
        alert('Network error placing order.');
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
