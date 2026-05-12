// Alday Dental Clinic – Main JS

// ── Navbar scroll effect
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
});

// ── Mobile hamburger menu
const hamburger = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobileMenu');
if (hamburger) {
    hamburger.addEventListener('click', () => {
        mobileMenu.classList.toggle('open');
    });
}

// ── Scroll reveal (for elements added after initial load animations)
const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, { threshold: 0.12 });

document.querySelectorAll('.scroll-reveal').forEach(el => revealObserver.observe(el));

// ── Book form handler (if on booking page)
const bookForm = document.getElementById('bookForm');
if (bookForm) {
    bookForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = bookForm.querySelector('.btn-submit');
        btn.textContent = 'Submitting…';
        btn.disabled = true;
        const data = Object.fromEntries(new FormData(bookForm));
        try {
            const res = await fetch('/book', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (result.status === 'success') {
                showToast('Booking submitted! We will contact you shortly.', 'success');
                bookForm.reset();
            }
        } catch (err) {
            showToast('Something went wrong. Please try again.', 'error');
        } finally {
            btn.textContent = 'Book Appointment';
            btn.disabled = false;
        }
    });
}

// ── Contact form handler
const contactForm = document.getElementById('contactForm');
if (contactForm) {
    contactForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = contactForm.querySelector('.btn-submit');
        btn.textContent = 'Sending…';
        btn.disabled = true;
        const data = Object.fromEntries(new FormData(contactForm));
        try {
            const res = await fetch('/contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (result.status === 'success') {
                showToast('Message sent! We\'ll get back to you soon.', 'success');
                contactForm.reset();
            }
        } catch (err) {
            showToast('Something went wrong. Please try again.', 'error');
        } finally {
            btn.textContent = 'Send Message';
            btn.disabled = false;
        }
    });
}

// ── FAQ Accordion
document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
        const isOpen = btn.getAttribute('aria-expanded') === 'true';
        // Close all
        document.querySelectorAll('.faq-question').forEach(b => {
            b.setAttribute('aria-expanded', 'false');
            b.nextElementSibling.classList.remove('open');
        });
        // Open clicked (if it was closed)
        if (!isOpen) {
            btn.setAttribute('aria-expanded', 'true');
            btn.nextElementSibling.classList.add('open');
        }
    });
});

// ── Toast notification
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3500);
}

// ── Toast styles (injected)
const toastStyle = document.createElement('style');
toastStyle.textContent = `
.toast {
    position: fixed; bottom: 32px; right: 32px; z-index: 9999;
    background: #1a1208; color: #fff;
    padding: 14px 24px; border-radius: 12px;
    font-family: 'Montserrat', sans-serif; font-size: 0.82rem; font-weight: 500;
    border-left: 4px solid #c9a84c;
    box-shadow: 0 8px 40px rgba(0,0,0,0.2);
    opacity: 0; transform: translateY(16px);
    transition: opacity 0.35s, transform 0.35s;
    max-width: 340px;
}
.toast.show { opacity: 1; transform: translateY(0); }
.toast-error { border-left-color: #e74c3c; }
`;
document.head.appendChild(toastStyle);
